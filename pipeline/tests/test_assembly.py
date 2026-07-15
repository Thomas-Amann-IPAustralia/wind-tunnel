"""Tests for the ASSEMBLY stage (TECH_SPEC §5.1 ASSEMBLY, §12; design §8).

LLM-free throughout (§15) — ASSEMBLY makes no model calls; it is pure assembly of the
committed run artefacts. Covers reference resolution, the notebook cell plan (no code
cells — the notebook is a document), the self-contained HTML render, the stage handler,
and the driver finalising the run at COMPLETE.
"""

from __future__ import annotations

import json
from pathlib import Path

import nbformat

from assembly import build_document_index, build_notebook, render_html, resolve_references
from assembly.notebook import STANDING_DISCLAIMER
from llm import LLMClient, ScriptedTransport
from run import FakeCommitter, run_pipeline
from stages.assembly import ASSEMBLY_NODE, SPECIALISTS, assembly, gather_inputs
from stages.context import StageContext
from statefile import RunState, Stage, StageStatus
from status import StatusModel

_RISK = ("3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.8")


# -- references -----------------------------------------------------------------


def test_build_document_index_first_seen_wins():
    manifests = [
        {"documents": [{"short_name": "ISM", "title": "Info Security Manual"}]},
        {"documents": [{"short_name": "ISM", "title": "A DIFFERENT DOC"}]},
    ]
    index = build_document_index(manifests)
    assert index["ISM"]["title"] == "Info Security Manual"


def test_resolve_references_dedupes_and_resolves():
    citations = {
        "privacy": {"7.1": [{"short_name": "OAIC PIA", "locator": "p.14"}]},
        "legal": {
            "9.1": [
                {"short_name": "OAIC PIA", "locator": "p.20"},  # same doc, different locator
                {"short_name": "Privacy Act 1988", "locator": "s 6"},
            ]
        },
    }
    index = build_document_index(
        [
            {
                "documents": [
                    {"short_name": "OAIC PIA", "title": "OAIC PIA Guide", "publisher": "OAIC"},
                    {"short_name": "Privacy Act 1988", "title": "Privacy Act 1988"},
                ]
            }
        ]
    )
    refs = resolve_references(citations, index)
    by_name = {r.short_name: r for r in refs}
    assert set(by_name) == {"OAIC PIA", "Privacy Act 1988"}
    assert by_name["OAIC PIA"].locators == ["p.14", "p.20"]  # gathered, deduped, ordered
    assert set(by_name["OAIC PIA"].specialists) == {"privacy", "legal"}
    assert by_name["OAIC PIA"].resolved is True


def test_resolve_references_marks_unresolved():
    citations = {"privacy": {"7.1": [{"short_name": "Ghost Doc", "locator": "p.1"}]}}
    refs = resolve_references(citations, {})
    assert refs[0].resolved is False
    assert refs[0].title == "Ghost Doc"


# -- notebook -------------------------------------------------------------------


def _report_data(**overrides) -> dict:
    data = {
        "run_id": "WT-DEMO-01",
        "title": "AI triage assistant",
        "created_at": "2026-07-15T00:00:00Z",
        "generated_at": "2026-07-15T14:00:00Z",
        "attested": True,
        "sensitivity_ceiling": "OFFICIAL",
        "threshold_md": "## 1. Basic information\n\nA triage assistant.\n",
        "full_sections": [
            {
                "section_id": "7.1",
                "title": "Privacy compliance",
                "friendly": "Privacy specialist",
                "body": "Yes. Handled per APP 6.",
                "citations": [{"short_name": "OAIC PIA", "locator": "p.14"}],
            },
            {
                "section_id": "7.2",
                "title": "Security",
                "friendly": "Privacy specialist",
                "gap": "insufficient basis to assess encryption",
            },
        ],
        "residual": {
            "sections": {
                sid: {"consequence": "Minor", "likelihood": "Unlikely", "rating": "Low"}
                for sid in _RISK
            },
            "overall_residual": "Low",
        },
        "high_risk_governance_review_required": False,
        "architect_md": "# Appendix — Implementation Plan\n\nDeliver in phases.\n",
        "gaps": [
            {"section": "7.2", "reason": "insufficient basis", "friendly": "Privacy specialist"}
        ],
        "unresolved": [
            {
                "topic": "De-identification sufficiency",
                "position_a": {
                    "specialist": "privacy",
                    "claim": "Sufficient",
                    "support": ["(OAIC PIA, p.22)"],
                },
                "position_b": {"specialist": "legal", "claim": "Insufficient", "support": []},
                "why_unresolved": "needs human policy judgement",
            }
        ],
        "references": [
            {
                "short_name": "OAIC PIA",
                "title": "OAIC PIA Guide",
                "publisher": "OAIC",
                "version": "2023",
                "source_url": "https://oaic.gov.au",
                "locators": ["p.14"],
                "specialists": ["privacy"],
                "resolved": True,
            }
        ],
        "provenance": {
            "roles": {"reviewer": {"model": "gemini-3.1-pro-preview", "prompt_version": "v1"}},
            "corpus_manifests": [
                {"specialist": "privacy", "generated_at": "2026-07-01", "document_count": 5}
            ],
        },
        "poc_html": None,
    }
    data.update(overrides)
    return data


def test_notebook_has_no_code_cells():
    nb = build_notebook(_report_data())
    assert nb.cells, "expected report cells"
    assert all(c.cell_type != "code" for c in nb.cells), (
        "the notebook must be non-executable (§12.1)"
    )


def test_notebook_round_trips_as_valid_nbformat():
    nb = build_notebook(_report_data())
    reloaded = nbformat.reads(nbformat.writes(nb, version=4), as_version=4)
    nbformat.validate(reloaded)


def test_notebook_contains_the_cell_plan():
    text = "\n".join(c.source for c in build_notebook(_report_data()).cells)
    assert "Threshold assessment — sections 1–4" in text
    assert "Full assessment — sections 5–12" in text
    assert "7.1 · Privacy compliance" in text
    assert "Residual risk — 12.3 and 12.4" in text
    assert "Appendix — Implementation Plan" in text
    assert "Recommended next steps" in text
    assert "Points of unresolved disagreement" in text
    assert "Appendix — Provenance" in text
    assert "# References" in text


def test_notebook_omits_unresolved_when_none():
    text = "\n".join(c.source for c in build_notebook(_report_data(unresolved=[])).cells)
    assert "Points of unresolved disagreement" not in text


def test_notebook_gap_section_renders_as_gap_not_body():
    text = "\n".join(c.source for c in build_notebook(_report_data()).cells)
    assert "insufficient basis to assess encryption" in text
    assert 'class="gap-note"' in text


# -- HTML render ----------------------------------------------------------------


def test_render_html_is_self_contained_report():
    html = render_html(build_notebook(_report_data()), title="AI triage assistant")
    assert html.startswith("<!doctype html>")
    assert "<style>" in html and "IBM Plex" in html  # stylesheet inlined, no external fetch
    assert "http-equiv" not in html.lower()
    assert '<div class="title-block">' in html
    assert '<table class="risk-table"' in html  # embedded HTML rendered, not escaped
    assert "&lt;table" not in html
    assert 'class="chip chip-low"' in html
    assert STANDING_DISCLAIMER in html


# -- stage handler --------------------------------------------------------------


def _draft(specialist: str) -> dict:
    from agents.prompting import response_type_of, specialist_owned_sections

    sections, gaps = {}, []
    for sid in specialist_owned_sections(specialist):
        if response_type_of(sid) == "yes_no_na":
            sections[sid] = f"Yes. {specialist} satisfied for {sid}."
        else:
            sections[sid] = f"Recorded for {sid}."
    return {
        "specialist": specialist,
        "sections": sections,
        "citations": {list(sections)[0]: [{"short_name": "ISM", "locator": "p.10"}]},
        "questions": {"why": "", "items": []},
        "gaps": gaps,
        "provenance": {"model": "gemini-3.5-flash", "prompt_version": "v1"},
    }


def _seed_assembly_run_dir(tmp_path: Path, run_id: str) -> Path:
    run_dir = tmp_path / "runs" / run_id
    (run_dir / "brainstorm").mkdir(parents=True)
    (run_dir / "brainstorm" / "outline.md").write_text(
        "# AI triage assistant for enquiries\nAn assistant.\n", "utf-8"
    )
    (run_dir / "threshold").mkdir()
    (run_dir / "threshold" / "threshold_assessment.md").write_text(
        "# Threshold — WT\n## 1. Basic information\n\nA triage assistant.\n", "utf-8"
    )
    (run_dir / "threshold" / "generalist_a.json").write_text(
        json.dumps({"provenance": {"model": "gemini-3.5-flash", "prompt_version": "v1"}}), "utf-8"
    )
    (run_dir / "threshold" / "reconciled.json").write_text(
        json.dumps({"provenance": {"model": "gemini-3.1-pro-preview", "prompt_version": "v1"}}),
        "utf-8",
    )
    specialists_dir = run_dir / "full" / "specialists"
    specialists_dir.mkdir(parents=True)
    for specialist in SPECIALISTS:
        (specialists_dir / f"{specialist}.json").write_text(json.dumps(_draft(specialist)), "utf-8")
    (run_dir / "full" / "architect.md").write_text(
        "# Appendix — Implementation Plan\n\nDeliver in phases.\n", "utf-8"
    )
    (run_dir / "full" / "architect.json").write_text(
        json.dumps({"provenance": {"model": "gemini-3.1-pro-preview", "prompt_version": "v1"}}),
        "utf-8",
    )
    reviewer_dir = run_dir / "full" / "reviewer"
    reviewer_dir.mkdir()
    (reviewer_dir / "ratings_residual.json").write_text(
        json.dumps(
            {
                "sections": {
                    sid: {"consequence": "Minor", "likelihood": "Unlikely", "rating": "Low"}
                    for sid in _RISK
                },
                "overall_residual": "Low",
            }
        ),
        "utf-8",
    )
    (reviewer_dir / "cycle_1.json").write_text(
        json.dumps({"provenance": {"model": "gemini-3.1-pro-preview", "prompt_version": "v1"}}),
        "utf-8",
    )
    return run_dir


def _noop_llm() -> LLMClient:
    return LLMClient(transport=ScriptedTransport(handler=lambda **_: "{}"))


def test_assembly_stage_writes_artefacts(tmp_path):
    run_dir = _seed_assembly_run_dir(tmp_path, "WT-ASM-1")
    run = RunState.new("WT-ASM-1")
    run.advance_to(Stage.ASSEMBLY)
    status = StatusModel.initial(run)
    ctx = StageContext(
        run_dir=run_dir, run=run, status=status, llm=_noop_llm(), kb_root=tmp_path / "kb"
    )
    (tmp_path / "kb").mkdir()
    assembly(ctx)

    assert (run_dir / "artefacts" / "assessment.ipynb").is_file()
    html = (run_dir / "artefacts" / "assessment.html").read_text()
    assert html.startswith("<!doctype html>")
    assert "AI triage assistant for enquiries" in html  # title from the outline heading
    assert status.nodes[ASSEMBLY_NODE] == "complete"


def test_gather_inputs_orders_full_sections_and_gaps(tmp_path):
    run_dir = _seed_assembly_run_dir(tmp_path, "WT-ASM-2")
    run = RunState.new("WT-ASM-2")
    run.advance_to(Stage.ASSEMBLY)
    ctx = StageContext(
        run_dir=run_dir,
        run=run,
        status=StatusModel.initial(run),
        llm=_noop_llm(),
        kb_root=tmp_path / "kb",
    )
    (tmp_path / "kb").mkdir()
    data = gather_inputs(ctx)
    ids = [b["section_id"] for b in data["full_sections"]]
    assert ids == sorted(ids, key=lambda s: (int(s.split(".")[0]), int(s.split(".")[1])))
    # 12.3/12.4 (reviewer) and 12.5 (human action) are not in the drafted section list.
    assert "12.3" not in ids and "12.5" not in ids
    assert data["title"] == "AI triage assistant for enquiries"


# -- driver: ASSEMBLY finalises at COMPLETE -------------------------------------


def test_pipeline_assembles_then_completes(tmp_path):
    run_dir = _seed_assembly_run_dir(tmp_path, "WT-ASM-E2E")
    (tmp_path / "kb").mkdir()
    run = RunState.new("WT-ASM-E2E")
    run.advance_to(Stage.ASSEMBLY)
    run.save(run_dir)
    StatusModel.initial(run).save(run_dir)

    result = run_pipeline(
        run_dir, llm=_noop_llm(), committer=FakeCommitter(), kb_root=tmp_path / "kb"
    )

    assert result.ok is True
    assert (run_dir / "artefacts" / "assessment.ipynb").is_file()
    assert (run_dir / "artefacts" / "assessment.html").is_file()
    run = RunState.load(run_dir)
    assert run.stage is Stage.COMPLETE
    assert run.stage_status is StageStatus.COMPLETE
    status = StatusModel.load(run_dir, run)
    assert status.overall_state == "complete"
