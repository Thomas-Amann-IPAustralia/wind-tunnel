"""Tests for the ARCHITECT stage (TECH_SPEC §5.1, §12.1; PROJECT_BRIEF §5.5).
LLM-free throughout (§15): a scripted transport plays the architect. The
traceability boundary — every step implements a section a specialist actually
drafted — is the integrity-critical part exercised here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.architect import AgentError, ArchitectPlan, run_architect
from agents.prompting import specialist_owned_sections
from llm import LLMClient, ScriptedTransport
from run import FakeCommitter, run_pipeline
from stages.context import StageContext
from stages.full import SPECIALISTS, architect, render_architect_markdown
from statefile import RunState, Stage, StageStatus
from status import StatusModel

# The valid trace targets for the tests: every specialist drafted all its owned
# sections (the no-questions happy path), so any owned (specialist, section) pair
# is a legal trace.
_VALID_TARGETS = {s: specialist_owned_sections(s) for s in SPECIALISTS}


def _client(handler) -> LLMClient:
    return LLMClient(transport=ScriptedTransport(handler=handler))


def _plan_payload(steps: list[dict] | None = None, **overrides) -> dict:
    payload = {
        "overview": "Build and deploy the system in three sequenced phases.",
        "steps": steps
        if steps is not None
        else [
            {
                "title": "Encrypt personal data at rest and in transit",
                "detail": "Use platform-managed AES-256 for storage and TLS 1.3 in transit.",
                "traces_to": [
                    {"specialist": "privacy", "section": "7.1", "mitigation": "encryption"}
                ],
            }
        ],
    }
    payload.update(overrides)
    return payload


def _handler(payload: dict):
    return lambda **_: json.dumps(payload)


# -- run_architect: the happy path + provenance ---------------------------------


def test_run_architect_returns_plan():
    plan = run_architect(
        _client(_handler(_plan_payload())), "outline", "threshold", "drafts", _VALID_TARGETS
    )
    assert isinstance(plan, ArchitectPlan)
    assert plan.overview.startswith("Build and deploy")
    assert len(plan.steps) == 1
    assert plan.steps[0]["traces_to"][0] == {
        "specialist": "privacy",
        "section": "7.1",
        "mitigation": "encryption",
    }
    assert plan.prompt_version == "v1"


def test_run_architect_accepts_multiple_traces_across_specialists():
    step = {
        "title": "Human oversight of automated decisions",
        "detail": "Route flagged cases to a reviewer.",
        "traces_to": [
            {"specialist": "ethics", "section": "8.4", "mitigation": "human oversight"},
            {
                "specialist": "legal",
                "section": "9.1",
                "mitigation": "administrative-law compliance",
            },
        ],
    }
    plan = run_architect(
        _client(_handler(_plan_payload(steps=[step]))), "o", "t", "d", _VALID_TARGETS
    )
    assert len(plan.steps[0]["traces_to"]) == 2


# -- validation: write scope (appendix only) + traceability (§5.5) --------------


def test_rejects_missing_overview():
    with pytest.raises(AgentError, match="overview"):
        run_architect(
            _client(_handler(_plan_payload(overview="  "))), "o", "t", "d", _VALID_TARGETS
        )


def test_rejects_empty_steps():
    with pytest.raises(AgentError, match="non-empty list"):
        run_architect(_client(_handler(_plan_payload(steps=[]))), "o", "t", "d", _VALID_TARGETS)


def test_rejects_step_without_detail():
    step = {
        "title": "A step",
        "detail": "",
        "traces_to": _VALID_TARGETS and [{"specialist": "privacy", "section": "7.1"}],
    }
    with pytest.raises(AgentError, match="'detail'"):
        run_architect(_client(_handler(_plan_payload(steps=[step]))), "o", "t", "d", _VALID_TARGETS)


def test_rejects_step_without_any_trace():
    step = {"title": "Floating step", "detail": "Something not in the assessment.", "traces_to": []}
    with pytest.raises(AgentError, match="non-empty 'traces_to'"):
        run_architect(_client(_handler(_plan_payload(steps=[step]))), "o", "t", "d", _VALID_TARGETS)


def test_rejects_trace_to_unknown_specialist():
    step = {
        "title": "Step",
        "detail": "Detail.",
        "traces_to": [{"specialist": "not_a_specialist", "section": "7.1"}],
    }
    with pytest.raises(AgentError, match="unknown specialist"):
        run_architect(_client(_handler(_plan_payload(steps=[step]))), "o", "t", "d", _VALID_TARGETS)


def test_rejects_trace_to_section_specialist_did_not_draft():
    # 5.1 is owned by ethics, not privacy — tracing privacy → 5.1 must fail.
    step = {
        "title": "Step",
        "detail": "Detail.",
        "traces_to": [{"specialist": "privacy", "section": "5.1"}],
    }
    with pytest.raises(AgentError, match="did not draft"):
        run_architect(_client(_handler(_plan_payload(steps=[step]))), "o", "t", "d", _VALID_TARGETS)


def test_rejects_trace_to_gapped_section():
    # privacy drafted only 7.2 here (7.1 was a gap) — a trace to 7.1 must fail
    # because a step can only implement a real drafted mitigation (§5.5).
    targets = dict(_VALID_TARGETS)
    targets["privacy"] = ("7.2",)
    step = {
        "title": "Step",
        "detail": "Detail.",
        "traces_to": [{"specialist": "privacy", "section": "7.1"}],
    }
    with pytest.raises(AgentError, match="did not draft"):
        run_architect(_client(_handler(_plan_payload(steps=[step]))), "o", "t", "d", targets)


# -- markdown rendering ---------------------------------------------------------


def test_render_architect_markdown_shows_traceability():
    plan = run_architect(_client(_handler(_plan_payload())), "o", "t", "d", _VALID_TARGETS)
    md = render_architect_markdown(plan)
    assert "# Appendix — Implementation Plan" in md
    assert "### 1. Encrypt personal data" in md
    # Traceability rendered with the specialist's friendly name and the mitigation.
    assert "*Answers: [Privacy" in md
    assert "§7.1" in md
    assert "encryption" in md


# -- the stage handler, direct call ---------------------------------------------


def _seed_architect_run_dir(tmp_path: Path) -> Path:
    run_dir = tmp_path / "runs" / "WT-TEST-ARCH"
    (run_dir / "brainstorm").mkdir(parents=True)
    (run_dir / "brainstorm" / "outline.md").write_text(
        "# Outline\nAn AI triage assistant for citizen enquiries.\n", encoding="utf-8"
    )
    (run_dir / "threshold").mkdir()
    (run_dir / "threshold" / "threshold_assessment.md").write_text(
        "# Threshold\nOverall inherent risk rating (highest-wins): Medium\n", encoding="utf-8"
    )
    specialists_dir = run_dir / "full" / "specialists"
    specialists_dir.mkdir(parents=True)
    for specialist in SPECIALISTS:
        owned = specialist_owned_sections(specialist)
        draft = {
            "specialist": specialist,
            "sections": {sid: f"Recorded for {sid}." for sid in owned},
            "citations": {owned[0]: [{"short_name": "ISM", "locator": "p.10"}]},
            "questions": {"why": "", "items": []},
            "gaps": [],
            "provenance": {"model": "flash", "prompt_version": "v1"},
        }
        (specialists_dir / f"{specialist}.json").write_text(json.dumps(draft), encoding="utf-8")
    return run_dir


def test_architect_stage_writes_appendix(tmp_path):
    run_dir = _seed_architect_run_dir(tmp_path)
    run = RunState.new("WT-TEST-ARCH")
    run.advance_to(Stage.ARCHITECT)
    status = StatusModel.initial(run)
    ctx = StageContext(
        run_dir=run_dir, run=run, status=status, llm=_client(_handler(_plan_payload()))
    )
    architect(ctx)

    plan_json = json.loads((run_dir / "full" / "architect.json").read_text())
    assert plan_json["steps"][0]["traces_to"][0]["section"] == "7.1"
    assert (run_dir / "full" / "architect.md").is_file()
    assert status.nodes["full.architect"] == "complete"
    # The drafting narration is the design-brief log line (§7.3 / design §9).
    drafting = [e for e in status.log if e.type == "drafting" and e.agent == "full.architect"]
    assert drafting and "implementation plan" in drafting[0].detail.lower()


def test_architect_stage_context_includes_all_specialists(tmp_path):
    """The architect must actually be shown every specialist's drafts + the
    traceable-sections list, or its traceability constraint is unenforceable."""
    run_dir = _seed_architect_run_dir(tmp_path)
    run = RunState.new("WT-TEST-ARCH2")
    run.advance_to(Stage.ARCHITECT)
    seen = {}

    def capture(*, model, system, user, response_json):
        seen["user"] = user
        return json.dumps(_plan_payload())

    ctx = StageContext(
        run_dir=run_dir, run=run, status=StatusModel.initial(run), llm=_client(capture)
    )
    architect(ctx)
    user = seen["user"]
    assert "Completed specialist assessment" in user
    assert "Traceable sections" in user
    for specialist in SPECIALISTS:
        assert specialist in user


# -- the driver end-to-end ------------------------------------------------------


def test_pipeline_runs_architect_then_stops_at_review(tmp_path):
    # Seed a run already at ARCHITECT with the specialist drafts in place.
    run_dir = _seed_architect_run_dir(tmp_path)
    run = RunState.new("WT-TEST-ARCH-E2E")
    run.advance_to(Stage.ARCHITECT)
    run.save(run_dir)
    StatusModel.initial(run).save(run_dir)

    result = run_pipeline(
        run_dir, llm=_client(_handler(_plan_payload())), committer=FakeCommitter()
    )

    # ARCHITECT ran and committed; REVIEW is not built, so the run stops there
    # as a calm, resumable failure — the documented boundary.
    assert result.ok is False
    assert (run_dir / "full" / "architect.md").is_file()
    run = RunState.load(run_dir)
    assert run.stage is Stage.REVIEW
    assert run.stage_status is StageStatus.FAILED
