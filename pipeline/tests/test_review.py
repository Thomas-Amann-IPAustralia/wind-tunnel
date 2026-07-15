"""Tests for the REVIEW stage (TECH_SPEC §5.1 REVIEW, §5.5, §11, §12.3/§12.4).

LLM-free throughout (§15): a scripted transport plays the reviewer (Pro) and the
amending specialists (Flash), keyed by model id. The integrity-critical parts are
exercised here — a directive can only touch a section its specialist owns (§11.3),
the reviewer never asserts a rating (§12.4), and the residual ratings are a provable
code output of the reviewer's tiers.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agents.prompting import (
    RISK_SECTIONS,
    response_type_of,
    specialist_owned_sections,
)
from agents.reviewer import AgentError, ReviewerResult, run_reviewer
from agents.specialist import SpecialistDraft, run_specialist_amendment
from llm import LLMClient, ScriptedTransport, resolve_model
from rating import overall_rating, rating
from retrieval.db import write_kb
from retrieval.retrieve import KB
from run import FakeCommitter, run_pipeline
from stages.context import StageContext
from stages.full import (
    SPECIALISTS,
    _build_coverage,
    _compute_residual,
    render_review_markdown,
    review,
)
from statefile import RunState, Stage, StageStatus
from status import StatusModel

_NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
_VALID_TARGETS = {s: specialist_owned_sections(s) for s in SPECIALISTS}


# -- payload builders -----------------------------------------------------------


def _residual(**overrides) -> dict:
    """A residual object covering all eight §3 areas with valid tiers (all Low by
    default); override any area with a (consequence, likelihood) tuple."""
    out = {}
    for sid in RISK_SECTIONS:
        cons, like = overrides.get(sid, ("Insignificant", "Rare"))
        out[sid] = {"consequence": cons, "likelihood": like, "rationale": f"residual for {sid}"}
    return out


def _reviewer_payload(*, directives=None, unresolved=None, findings=None, residual=None) -> dict:
    return {
        "coherence_findings": findings if findings is not None else [],
        "amend_directives": directives if directives is not None else [],
        "unresolved": unresolved if unresolved is not None else [],
        "residual": residual if residual is not None else _residual(),
    }


def _directive(specialist="privacy", sections=("7.2",), **overrides) -> dict:
    d = {
        "target_specialist": f"full.specialist.{specialist}",
        "target_sections": list(sections),
        "conflicting_claims": [{"section": sections[0], "claim": "A", "ref": "(Src, p.1)"}],
        "ruling": f"amend {sections[0]} to align with the cited source",
        "rationale": "better supported",
    }
    d.update(overrides)
    return d


def _client(handler=None, responses=None) -> LLMClient:
    return LLMClient(transport=ScriptedTransport(handler=handler, responses=responses))


def _handler(payload: dict):
    return lambda **_: json.dumps(payload)


# -- run_reviewer: happy path + provenance --------------------------------------


def test_run_reviewer_returns_result():
    result = run_reviewer(
        _client(_handler(_reviewer_payload(directives=[_directive()]))),
        instrument_context="ctx",
        scope_context="scope",
        coverage_context="cov",
        draft_context="draft",
        threshold_md="threshold",
        outline_md="outline",
        valid_targets=_VALID_TARGETS,
    )
    assert isinstance(result, ReviewerResult)
    assert result.amend_directives[0]["target_specialist"] == "privacy"  # normalised from node id
    assert result.amend_directives[0]["target_sections"] == ["7.2"]
    assert set(result.residual) == set(RISK_SECTIONS)
    assert result.prompt_version == "v1"


def test_run_reviewer_accepts_bare_specialist_id():
    d = _directive(specialist="privacy")
    d["target_specialist"] = "privacy"  # bare form, not the node id
    result = _run(directives=[d])
    assert result.amend_directives[0]["target_specialist"] == "privacy"


def _run(**payload_kwargs) -> ReviewerResult:
    return run_reviewer(
        _client(_handler(_reviewer_payload(**payload_kwargs))),
        instrument_context="c",
        scope_context="s",
        coverage_context="cov",
        draft_context="d",
        threshold_md="t",
        outline_md="o",
        valid_targets=_VALID_TARGETS,
    )


# -- run_reviewer: directive write-scope (§11.3) --------------------------------


def test_rejects_directive_to_unknown_specialist():
    d = _directive()
    d["target_specialist"] = "full.specialist.not_real"
    with pytest.raises(AgentError, match="unknown specialist"):
        _run(directives=[d])


def test_rejects_directive_to_section_specialist_does_not_own():
    # 5.1 is owned by ethics, not privacy — a privacy directive on 5.1 is out of scope.
    with pytest.raises(AgentError, match="does not own"):
        _run(directives=[_directive(specialist="privacy", sections=("5.1",))])


def test_rejects_directive_without_ruling():
    d = _directive()
    d["ruling"] = "  "
    with pytest.raises(AgentError, match="ruling"):
        _run(directives=[d])


def test_rejects_directive_without_target_sections():
    d = _directive()
    d["target_sections"] = []
    with pytest.raises(AgentError, match="target_sections"):
        _run(directives=[d])


# -- run_reviewer: residual = tiers only, engine rates (§12.4) -------------------


def test_rejects_residual_with_asserted_rating():
    res = _residual()
    res["3.1"]["rating"] = "High"  # the reviewer must not assert a rating
    with pytest.raises(AgentError, match="rating"):
        _run(residual=res)


def test_rejects_residual_missing_area():
    res = _residual()
    del res["3.4"]
    with pytest.raises(AgentError, match="3.4"):
        _run(residual=res)


def test_rejects_residual_with_invalid_tier():
    res = _residual(**{"3.2": ("Catastrophic", "Rare")})  # not a valid consequence tier
    with pytest.raises(AgentError, match="consequence"):
        _run(residual=res)


# -- run_reviewer: unresolved shape ---------------------------------------------


def test_rejects_unresolved_missing_positions():
    bad = [{"topic": "x", "why_unresolved": "y"}]  # no position_a/b
    with pytest.raises(AgentError, match="position_a"):
        _run(unresolved=bad)


# -- _compute_residual: engine output, hand-worked ------------------------------


def test_compute_residual_matches_engine():
    inputs = _residual(**{"3.5": ("Major", "Possible")})
    out = _compute_residual(inputs)
    assert out["sections"]["3.5"]["rating"] == rating("Major", "Possible")
    assert out["sections"]["3.1"]["rating"] == rating("Insignificant", "Rare")
    expected_overall = overall_rating([out["sections"][s]["rating"] for s in RISK_SECTIONS])
    assert out["overall_residual"] == expected_overall
    # 3.5's Major/Possible drives the highest-wins overall above the all-Low baseline.
    assert out["overall_residual"] == rating("Major", "Possible")


# -- _build_coverage: deterministic checklist (§11.1) ---------------------------


def _draft_dict(specialist: str, *, gap_sections=()) -> dict:
    sections, gaps = {}, []
    for sid in specialist_owned_sections(specialist):
        if sid in gap_sections:
            gaps.append({"section": sid, "reason": f"insufficient basis for {sid}"})
        elif response_type_of(sid) == "yes_no_na":
            sections[sid] = f"Yes. {specialist} satisfied for {sid}."
        else:
            sections[sid] = f"Recorded for {sid}."
    return {
        "specialist": specialist,
        "sections": sections,
        "citations": {},
        "questions": {"why": "", "items": []},
        "gaps": gaps,
        "provenance": {"model": "flash", "prompt_version": "v1"},
    }


def test_build_coverage_classifies_sections():
    drafts = {s: _draft_dict(s) for s in SPECIALISTS}
    # legal gaps 12.2 — coverage must record it as gapped, not addressed.
    drafts["legal"] = _draft_dict("legal", gap_sections=("12.2",))
    coverage = _build_coverage(drafts)
    by_section = {i["section"]: i for i in coverage["items"]}
    assert by_section["7.1"]["state"] == "addressed"
    assert by_section["12.2"]["state"] == "gapped"
    assert by_section["12.3"]["state"] == "addressed"  # reviewer-produced residual
    assert by_section["12.4"]["state"] == "addressed"
    assert by_section["12.5"]["state"] == "human_action"
    assert coverage["gaps"] == ["12.2"]
    assert coverage["counts"]["gapped"] == 1
    assert coverage["missing"] == []


# -- run_specialist_amendment: scoped merge (§11.3) -----------------------------


def _kb_root(tmp_path: Path) -> Path:
    kb_root = tmp_path / "kb"
    kb_root.mkdir()
    for specialist in SPECIALISTS:
        write_kb(kb_root / f"{specialist}.sqlite", [], _NOW)
        (kb_root / f"{specialist}.index.json").write_text(
            json.dumps({"specialist": specialist, "documents": []}), encoding="utf-8"
        )
    return kb_root


def test_amendment_merges_only_target_sections(tmp_path):
    prior = SpecialistDraft.from_dict(_draft_dict("privacy"))
    amend_payload = {
        "action": "draft",
        "sections": {"7.2": "Amended: the data-flow now matches §6.1."},
        "citations": {"7.2": [{"short_name": "OAIC PIA", "locator": "p.14"}]},
        "gaps": [],
    }
    kb_root = _kb_root(tmp_path)
    with KB(kb_root / "privacy.sqlite") as kb:
        new = run_specialist_amendment(
            _client(_handler(amend_payload)),
            "privacy",
            prior,
            ("7.2",),
            "directive text",
            "seed terms",
            "outline",
            "threshold",
            kb,
            "{}",
        )
    assert new.sections["7.2"].startswith("Amended:")
    assert new.sections["7.1"] == prior.sections["7.1"]  # untouched
    assert new.citations["7.2"][0]["short_name"] == "OAIC PIA"
    assert new.questions == []  # amendments raise no questions


def test_amendment_rejects_out_of_scope_output(tmp_path):
    prior = SpecialistDraft.from_dict(_draft_dict("privacy"))
    # Model tries to also change 7.1, which was not directed.
    amend_payload = {
        "action": "draft",
        "sections": {"7.2": "Amended.", "7.1": "No. sneaky change."},
        "citations": {},
        "gaps": [],
    }
    kb_root = _kb_root(tmp_path)
    with KB(kb_root / "privacy.sqlite") as kb:
        with pytest.raises(Exception, match="non-directed"):
            run_specialist_amendment(
                _client(_handler(amend_payload)),
                "privacy",
                prior,
                ("7.2",),
                "d",
                "s",
                "o",
                "t",
                kb,
                "{}",
            )


def test_amendment_rejects_non_owned_target(tmp_path):
    prior = SpecialistDraft.from_dict(_draft_dict("privacy"))
    kb_root = _kb_root(tmp_path)
    with KB(kb_root / "privacy.sqlite") as kb:
        with pytest.raises(Exception, match="non-owned"):
            run_specialist_amendment(
                _client(_handler({"action": "draft", "sections": {}, "gaps": []})),
                "privacy",
                prior,
                ("5.1",),  # ethics' section, not privacy's
                "d",
                "s",
                "o",
                "t",
                kb,
                "{}",
            )


# -- the stage handler ----------------------------------------------------------


def _seed_review_run_dir(tmp_path: Path, run_id: str) -> Path:
    run_dir = tmp_path / "runs" / run_id
    (run_dir / "brainstorm").mkdir(parents=True)
    (run_dir / "brainstorm" / "outline.md").write_text("# Outline\nA triage assistant.\n", "utf-8")
    (run_dir / "threshold").mkdir()
    (run_dir / "threshold" / "threshold_assessment.md").write_text(
        "# Threshold\nOverall inherent risk rating (highest-wins): Medium\n", "utf-8"
    )
    specialists_dir = run_dir / "full" / "specialists"
    specialists_dir.mkdir(parents=True)
    for specialist in SPECIALISTS:
        (specialists_dir / f"{specialist}.json").write_text(
            json.dumps(_draft_dict(specialist)), encoding="utf-8"
        )
    return run_dir


def _model_responses(pro_queue: list[dict], flash_queue: list[dict] | None = None) -> dict:
    responses = {resolve_model("reviewer"): [json.dumps(p) for p in pro_queue]}
    if flash_queue is not None:
        responses[resolve_model("specialist")] = [json.dumps(p) for p in flash_queue]
    return responses


def test_review_no_directives_writes_outputs(tmp_path):
    run_dir = _seed_review_run_dir(tmp_path, "WT-REV-CLEAN")
    run = RunState.new("WT-REV-CLEAN")
    run.advance_to(Stage.REVIEW)
    status = StatusModel.initial(run)
    ctx = StageContext(
        run_dir=run_dir,
        run=run,
        status=status,
        llm=_client(responses=_model_responses([_reviewer_payload()])),
    )
    review(ctx)

    assert (run_dir / "full" / "reviewer" / "cycle_1.json").is_file()
    assert (run_dir / "full" / "reviewer" / "coverage.json").is_file()
    residual = json.loads((run_dir / "full" / "reviewer" / "ratings_residual.json").read_text())
    assert residual["overall_residual"] == "Low"
    assert set(residual["sections"]) == set(RISK_SECTIONS)
    assert not (run_dir / "full" / "reviewer" / "unresolved.json").exists()
    assert (run_dir / "full" / "reviewer" / "review.md").is_file()
    assert status.nodes["full.reviewer"] == "complete"
    assert run.review_cycles == 1


def test_review_applies_amendment_then_settles(tmp_path):
    run_dir = _seed_review_run_dir(tmp_path, "WT-REV-AMEND")
    run = RunState.new("WT-REV-AMEND")
    run.advance_to(Stage.REVIEW)
    status = StatusModel.initial(run)
    amend = {"action": "draft", "sections": {"7.2": "Amended per the reviewer."}, "gaps": []}
    ctx = StageContext(
        run_dir=run_dir,
        run=run,
        status=status,
        kb_root=_kb_root(tmp_path),
        llm=_client(
            responses=_model_responses(
                [_reviewer_payload(directives=[_directive()]), _reviewer_payload()],
                [amend],
            )
        ),
    )
    review(ctx)

    # Two reviewer cycles ran; the privacy draft was amended between them.
    assert (run_dir / "full" / "reviewer" / "cycle_1.json").is_file()
    assert (run_dir / "full" / "reviewer" / "cycle_2.json").is_file()
    privacy = json.loads((run_dir / "full" / "specialists" / "privacy.json").read_text())
    assert privacy["sections"]["7.2"] == "Amended per the reviewer."
    assert run.review_cycles == 2
    assert not (run_dir / "full" / "reviewer" / "unresolved.json").exists()
    # A revision event was narrated for the amending specialist (§6.3).
    assert any(e.type == "revision" for e in status.log)


def test_review_records_unresolved_when_cap_reached(tmp_path):
    run_dir = _seed_review_run_dir(tmp_path, "WT-REV-CAP")
    run = RunState.new("WT-REV-CAP")
    run.advance_to(Stage.REVIEW)
    status = StatusModel.initial(run)
    amend = {"action": "draft", "sections": {"7.2": "Amended once."}, "gaps": []}
    ctx = StageContext(
        run_dir=run_dir,
        run=run,
        status=status,
        kb_root=_kb_root(tmp_path),
        # Both cycles still emit a directive → cap reached with a live conflict (§11.4).
        llm=_client(
            responses=_model_responses(
                [
                    _reviewer_payload(directives=[_directive()]),
                    _reviewer_payload(directives=[_directive()]),
                ],
                [amend],
            )
        ),
    )
    review(ctx)

    assert run.review_cycles == 2
    unresolved = json.loads((run_dir / "full" / "reviewer" / "unresolved.json").read_text())
    assert unresolved and "cap" in unresolved[0]["why_unresolved"].lower()


def test_review_resets_cycles_on_entry(tmp_path):
    # A prior failed attempt left review_cycles at the cap; REVIEW must reset it so the
    # fresh bounded loop runs rather than tripping the cap immediately (§5.3).
    run_dir = _seed_review_run_dir(tmp_path, "WT-REV-RESET")
    run = RunState.new("WT-REV-RESET")
    run.advance_to(Stage.REVIEW)
    run.review_cycles = 2  # simulate a committed prior attempt
    status = StatusModel.initial(run)
    ctx = StageContext(
        run_dir=run_dir,
        run=run,
        status=status,
        llm=_client(responses=_model_responses([_reviewer_payload()])),
    )
    review(ctx)  # must not raise the cap error
    assert (run_dir / "full" / "reviewer" / "ratings_residual.json").is_file()
    assert run.review_cycles == 1


def test_render_review_markdown_shows_residual_table():
    coverage = _build_coverage({s: _draft_dict(s) for s in SPECIALISTS})
    residual = _compute_residual(_residual(**{"3.5": ("Major", "Possible")}))
    result = ReviewerResult(
        coherence_findings=[{"summary": "A contradiction", "sections": ["7.2"], "detail": "d"}],
        amend_directives=[],
        unresolved=[],
        residual={},
    )
    md = render_review_markdown(coverage, result, residual, [])
    assert "## 12.3 Residual risk summary" in md
    assert "12.4 Overall residual risk rating" in md
    assert "A contradiction" in md


# -- the driver end-to-end ------------------------------------------------------


def test_pipeline_runs_review_then_assembles_to_complete(tmp_path):
    run_dir = _seed_review_run_dir(tmp_path, "WT-REV-E2E")
    run = RunState.new("WT-REV-E2E")
    run.advance_to(Stage.REVIEW)
    run.save(run_dir)
    StatusModel.initial(run).save(run_dir)

    result = run_pipeline(
        run_dir,
        llm=_client(responses=_model_responses([_reviewer_payload()])),
        committer=FakeCommitter(),
        kb_root=_kb_root(tmp_path),
    )

    # REVIEW ran, then ASSEMBLY built the report and the run finalised at COMPLETE.
    assert result.ok is True
    assert (run_dir / "full" / "reviewer" / "ratings_residual.json").is_file()
    assert (run_dir / "artefacts" / "assessment.html").is_file()
    run = RunState.load(run_dir)
    assert run.stage is Stage.COMPLETE
    assert run.stage_status is StageStatus.COMPLETE


def test_pipeline_runs_full_path_drafting_to_complete(tmp_path):
    """The whole full-assessment happy path in one dispatch: six specialists draft,
    the architect writes the appendix, the reviewer audits, and assembly builds the
    report — all composing through the driver to a COMPLETE run."""
    run_dir = _seed_review_run_dir(tmp_path, "WT-FULL-CHAIN")
    # Remove the seeded specialist drafts so FULL_DRAFTING must produce them.
    for specialist in SPECIALISTS:
        (run_dir / "full" / "specialists" / f"{specialist}.json").unlink()
    run = RunState.new("WT-FULL-CHAIN")
    run.advance_to(Stage.FULL_DRAFTING)
    run.save(run_dir)
    StatusModel.initial(run).save(run_dir)

    specialist_drafts = [
        {**_draft_dict(s), "action": "draft", "questions": {"why": "", "items": []}}
        for s in SPECIALISTS
    ]
    architect_payload = {
        "overview": "Deliver the system in sequenced phases.",
        "steps": [
            {
                "title": "Encrypt personal data",
                "detail": "AES-256 at rest, TLS in transit.",
                "traces_to": [
                    {"specialist": "privacy", "section": "7.1", "mitigation": "encryption"}
                ],
            }
        ],
    }
    responses = {
        resolve_model("specialist"): [json.dumps(d) for d in specialist_drafts],
        # Architect and reviewer both resolve to the Pro id — FIFO in call order.
        resolve_model("reviewer"): [json.dumps(architect_payload), json.dumps(_reviewer_payload())],
    }

    result = run_pipeline(
        run_dir,
        llm=_client(responses=responses),
        committer=FakeCommitter(),
        kb_root=_kb_root(tmp_path),
    )

    assert result.ok is True
    assert all((run_dir / "full" / "specialists" / f"{s}.json").is_file() for s in SPECIALISTS)
    assert (run_dir / "full" / "architect.md").is_file()
    assert (run_dir / "full" / "reviewer" / "ratings_residual.json").is_file()
    assert (run_dir / "artefacts" / "assessment.ipynb").is_file()
    run = RunState.load(run_dir)
    assert run.stage is Stage.COMPLETE
    assert run.stage_status is StageStatus.COMPLETE
