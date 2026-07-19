"""Tests for the FULL_REVISING stage (TECH_SPEC §5.1 FULL_REVISING, §5.8).

LLM-free (§15): a scripted Flash transport plays the revising specialists, and (for the
driver test) a scripted Pro transport plays the architect and reviewer. The checkpoint
path is exercised end-to-end — a specialist that raised a question revises its own
sections in light of the answers; a specialist that raised none is untouched; a skipped
question is surfaced to the specialist as an unavailable fact and can become a gap
(§5.1 "skipped questions → gaps").
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agents.prompting import (
    response_type_of,
    specialist_friendly_name,
    specialist_owned_sections,
)
from llm import LLMClient, ScriptedTransport, resolve_model
from retrieval.db import write_kb
from run import FakeCommitter, run_pipeline
from stages.context import StageContext
from stages.full import (
    SPECIALISTS,
    _render_answers_directive,
    _revision_seed_terms,
    _specialist_from_node,
    full_revising,
)
from statefile import RunState, Stage, StageStatus
from status import StatusModel

_NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# -- payload builders -----------------------------------------------------------


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


def _full_amendment(specialist: str, *, gap_sections=(), prefix="Revised") -> dict:
    """A `draft` action covering every owned section of ``specialist`` — the shape
    FULL_REVISING demands, since it targets the specialist's whole owned set."""
    sections, gaps = {}, []
    for sid in specialist_owned_sections(specialist):
        if sid in gap_sections:
            gaps.append({"section": sid, "reason": f"still unknown for {sid}"})
        elif response_type_of(sid) == "yes_no_na":
            sections[sid] = f"Yes. {prefix} {sid} with the supplied facts."
        else:
            sections[sid] = f"{prefix} {sid} with the supplied facts."
    return {"action": "draft", "sections": sections, "citations": {}, "gaps": gaps}


def _questions_payload(*specs: str) -> dict:
    """A batched checkpoint payload with one question per named specialist."""
    entries = [
        {
            "node_id": f"full.specialist.{s}",
            "friendly": s,
            "why": f"{s} needs a missing fact",
            "items": [
                {
                    "question_id": f"{s}-1",
                    "text": f"A fact {s} needs?",
                    "options": None,
                    "allow_free_text": True,
                }
            ],
        }
        for s in specs
    ]
    total = sum(len(e["items"]) for e in entries)
    return {
        "batch_id": "q-1",
        "specialists": entries,
        "counts": {"total": total, "answered": 0, "skipped": 0},
    }


def _client(responses) -> LLMClient:
    return LLMClient(transport=ScriptedTransport(responses=responses))


def _kb_root(tmp_path: Path) -> Path:
    kb_root = tmp_path / "kb"
    kb_root.mkdir()
    for specialist in SPECIALISTS:
        write_kb(kb_root / f"{specialist}.sqlite", [], _NOW)
        (kb_root / f"{specialist}.index.json").write_text(
            json.dumps({"specialist": specialist, "documents": []}), encoding="utf-8"
        )
    return kb_root


def _seed_run_dir(tmp_path: Path, run_id: str, *, questions: dict, answers: dict) -> Path:
    run_dir = tmp_path / "runs" / run_id
    (run_dir / "brainstorm").mkdir(parents=True)
    (run_dir / "brainstorm" / "outline.md").write_text("# Outline\nA triage assistant.\n", "utf-8")
    (run_dir / "threshold").mkdir()
    (run_dir / "threshold" / "threshold_assessment.md").write_text(
        "# Threshold\nOverall inherent risk rating (highest-wins): Medium\n", "utf-8"
    )
    full_dir = run_dir / "full"
    (full_dir / "specialists").mkdir(parents=True)
    for specialist in SPECIALISTS:
        (full_dir / "specialists" / f"{specialist}.json").write_text(
            json.dumps(_draft_dict(specialist)), encoding="utf-8"
        )
    (full_dir / "questions.json").write_text(json.dumps(questions), encoding="utf-8")
    (full_dir / "answers.json").write_text(json.dumps(answers), encoding="utf-8")
    return run_dir


# -- _specialist_from_node ------------------------------------------------------


def test_specialist_from_node_roundtrips_every_specialist():
    for s in SPECIALISTS:
        assert _specialist_from_node(f"full.specialist.{s}") == s


def test_specialist_from_node_rejects_bad_node():
    with pytest.raises(ValueError, match="Not a specialist node id"):
        _specialist_from_node("full.reviewer")
    with pytest.raises(ValueError, match="Unknown specialist"):
        _specialist_from_node("full.specialist.made_up")


# -- _render_answers_directive --------------------------------------------------


def test_render_directive_counts_answered_and_skipped():
    items = [
        {"question_id": "privacy-1", "text": "Where is PI stored?"},
        {"question_id": "privacy-2", "text": "Is a pilot planned?"},
        {"question_id": "privacy-3", "text": "Retention period?"},
    ]
    block, answered, skipped = _render_answers_directive(
        items,
        {"privacy-1": "In AWS Sydney", "privacy-3": ""},  # -3 blank ⇒ treated as skipped
        {"privacy-2"},  # -2 explicitly skipped
    )
    assert answered == 1
    assert skipped == 2
    assert "In AWS Sydney" in block
    assert block.count("chose not to answer") == 2


def test_revision_seed_terms_includes_questions_and_answers():
    items = [{"question_id": "privacy-1", "text": "Where is PI stored?"}]
    seed = _revision_seed_terms(items, {"privacy-1": "AWS Sydney"})
    assert "Where is PI stored?" in seed
    assert "AWS Sydney" in seed


# -- the stage handler ----------------------------------------------------------


def _run_handler(tmp_path, run_id, *, questions, answers, flash_queue):
    run_dir = _seed_run_dir(tmp_path, run_id, questions=questions, answers=answers)
    run = RunState.new(run_id)
    run.advance_to(Stage.FULL_REVISING)
    status = StatusModel.initial(run)
    ctx = StageContext(
        run_dir=run_dir,
        run=run,
        status=status,
        kb_root=_kb_root(tmp_path),
        llm=_client({resolve_model("specialist"): [json.dumps(p) for p in flash_queue]}),
    )
    full_revising(ctx)
    return run_dir, status


def test_revises_only_the_questioning_specialist(tmp_path):
    run_dir, status = _run_handler(
        tmp_path,
        "WT-REV-ONE",
        questions=_questions_payload("privacy"),
        answers={"answers": [{"question_id": "privacy-1", "value": "AWS Sydney"}], "skips": []},
        flash_queue=[_full_amendment("privacy")],
    )

    privacy = json.loads((run_dir / "full" / "specialists" / "privacy.json").read_text())
    assert privacy["sections"]["7.2"].startswith("Revised")  # re-drafted with the answer
    # An untouched specialist keeps its seeded draft verbatim.
    ethics = json.loads((run_dir / "full" / "specialists" / "ethics.json").read_text())
    assert ethics == _draft_dict("ethics")

    revised = json.loads((run_dir / "full" / "revised.json").read_text())
    assert revised["revised"] == ["privacy"]
    assert revised["counts"] == {"answered": 1, "skipped": 0}
    # The revising specialist's node was narrated with a revision event (§6.3).
    assert any(e.type == "revision" for e in status.log)
    assert status.nodes["full.specialist.privacy"] == "complete"


def test_skipped_question_can_become_a_gap(tmp_path):
    # The user skips privacy's question; the specialist cannot ground 7.2 and gaps it.
    run_dir, _ = _run_handler(
        tmp_path,
        "WT-REV-SKIP",
        questions=_questions_payload("privacy"),
        answers={"answers": [], "skips": ["privacy-1"]},
        flash_queue=[_full_amendment("privacy", gap_sections=("7.2",))],
    )
    privacy = json.loads((run_dir / "full" / "specialists" / "privacy.json").read_text())
    assert "7.2" not in privacy["sections"]
    assert any(g["section"] == "7.2" for g in privacy["gaps"])
    revised = json.loads((run_dir / "full" / "revised.json").read_text())
    assert revised["counts"] == {"answered": 0, "skipped": 1}


def test_revises_multiple_specialists(tmp_path):
    # Two questioners revise concurrently (§5.4), so the transport must route by
    # prompt content, not FIFO order — a queue would hand a specialist the other
    # one's amendment depending on scheduling.
    def handler(*, user, **_):
        for s in ("privacy", "it_security"):
            if f"sections owned by {specialist_friendly_name(s)}" in user:
                return json.dumps(_full_amendment(s))
        raise AssertionError(f"could not identify specialist from prompt: {user[:200]!r}")

    run_dir = _seed_run_dir(
        tmp_path,
        "WT-REV-MULTI",
        questions=_questions_payload("privacy", "it_security"),
        answers={
            "answers": [
                {"question_id": "privacy-1", "value": "AWS Sydney"},
                {"question_id": "it_security-1", "value": "ISM aligned"},
            ],
            "skips": [],
        },
    )
    run = RunState.new("WT-REV-MULTI")
    run.advance_to(Stage.FULL_REVISING)
    ctx = StageContext(
        run_dir=run_dir,
        run=run,
        status=StatusModel.initial(run),
        kb_root=_kb_root(tmp_path),
        llm=LLMClient(transport=ScriptedTransport(handler=handler)),
    )
    full_revising(ctx)

    revised = json.loads((run_dir / "full" / "revised.json").read_text())
    # Questions-payload order, deterministic regardless of completion order.
    assert revised["revised"] == ["privacy", "it_security"]
    assert revised["counts"] == {"answered": 2, "skipped": 0}
    for s in ("privacy", "it_security"):
        data = json.loads((run_dir / "full" / "specialists" / f"{s}.json").read_text())
        assert data["specialist"] == s  # each got its own amendment, not the other's
        assert all(v.startswith(("Revised", "Yes. Revised")) for v in data["sections"].values())


def test_amendment_directive_reaches_the_specialist(tmp_path):
    """The answer text lands in the specialist's amendment prompt — the answer is what the
    revision is grounded in, so it must actually reach the model (§5.1)."""
    seen: list[str] = []

    def handler(*, system, user, **_):
        seen.append(user)
        return json.dumps(_full_amendment("privacy"))

    run_dir = _seed_run_dir(
        tmp_path,
        "WT-REV-PROMPT",
        questions=_questions_payload("privacy"),
        answers={
            "answers": [{"question_id": "privacy-1", "value": "Stored in AWS Sydney"}],
            "skips": [],
        },
    )
    run = RunState.new("WT-REV-PROMPT")
    run.advance_to(Stage.FULL_REVISING)
    ctx = StageContext(
        run_dir=run_dir,
        run=run,
        status=StatusModel.initial(run),
        kb_root=_kb_root(tmp_path),
        llm=LLMClient(transport=ScriptedTransport(handler=handler)),
    )
    full_revising(ctx)

    assert any("Stored in AWS Sydney" in u for u in seen)
    assert any("now answered" in u for u in seen)  # the checkpoint-answer framing, not reviewer


# -- the driver end-to-end ------------------------------------------------------


def test_pipeline_resumes_checkpoint_through_revising_to_complete(tmp_path):
    """A dispatch with resume_from=FULL_REVISING (what POST /answers sends) resumes a
    paused checkpoint: the questioning specialist revises, then the architect, reviewer and
    assembly compose through the driver to a COMPLETE run (§5.1)."""
    run_dir = _seed_run_dir(
        tmp_path,
        "WT-REV-E2E",
        questions=_questions_payload("privacy"),
        answers={"answers": [{"question_id": "privacy-1", "value": "AWS Sydney"}], "skips": []},
    )
    run = RunState.new("WT-REV-E2E")
    run.advance_to(Stage.FULL_CHECKPOINT, StageStatus.AWAITING_USER)
    run.save(run_dir)
    StatusModel.initial(run).save(run_dir)

    architect_payload = {
        "overview": "Deliver in sequenced phases.",
        "steps": [
            {
                "title": "Encrypt personal data",
                "detail": "AES-256 at rest.",
                "traces_to": [
                    {"specialist": "privacy", "section": "7.1", "mitigation": "encryption"}
                ],
            }
        ],
    }
    reviewer_payload = {
        "coherence_findings": [],
        "amend_directives": [],
        "unresolved": [],
        "residual": {
            sid: {"consequence": "Insignificant", "likelihood": "Rare", "rationale": "r"}
            for sid in ("3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.8")
        },
    }
    responses = {
        resolve_model("specialist"): [json.dumps(_full_amendment("privacy"))],
        resolve_model("reviewer"): [json.dumps(architect_payload), json.dumps(reviewer_payload)],
    }

    result = run_pipeline(
        run_dir,
        llm=_client(responses),
        committer=FakeCommitter(),
        resume_from="FULL_REVISING",
        kb_root=_kb_root(tmp_path),
    )

    assert result.ok is True
    assert (run_dir / "full" / "revised.json").is_file()
    assert (run_dir / "full" / "architect.md").is_file()
    assert (run_dir / "artefacts" / "assessment.html").is_file()
    run = RunState.load(run_dir)
    assert run.stage is Stage.COMPLETE
    assert run.stage_status is StageStatus.COMPLETE


def test_full_revising_is_idempotent_on_resume(tmp_path):
    """If full/revised.json already exists, the stage is skipped on resume (§5.3) — no flash
    call is made, so an empty response queue is proof the handler did not re-run."""
    run_dir = _seed_run_dir(
        tmp_path,
        "WT-REV-IDEM",
        questions=_questions_payload("privacy"),
        answers={"answers": [{"question_id": "privacy-1", "value": "AWS Sydney"}], "skips": []},
    )
    (run_dir / "full" / "revised.json").write_text(
        json.dumps({"revised": ["privacy"], "counts": {"answered": 1, "skipped": 0}}), "utf-8"
    )
    run = RunState.new("WT-REV-IDEM")
    run.advance_to(Stage.FULL_REVISING)
    run.save(run_dir)
    StatusModel.initial(run).save(run_dir)

    architect_payload = {
        "overview": "o",
        "steps": [
            {
                "title": "t",
                "detail": "d",
                "traces_to": [{"specialist": "privacy", "section": "7.1", "mitigation": "m"}],
            }
        ],
    }
    reviewer_payload = {
        "coherence_findings": [],
        "amend_directives": [],
        "unresolved": [],
        "residual": {
            sid: {"consequence": "Insignificant", "likelihood": "Rare", "rationale": "r"}
            for sid in ("3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.8")
        },
    }
    responses = {
        resolve_model("specialist"): [],  # no amendment expected — FULL_REVISING is skipped
        resolve_model("reviewer"): [json.dumps(architect_payload), json.dumps(reviewer_payload)],
    }
    result = run_pipeline(
        run_dir,
        llm=_client(responses),
        committer=FakeCommitter(),
        kb_root=_kb_root(tmp_path),
    )
    assert result.ok is True
    run = RunState.load(run_dir)
    assert run.stage is Stage.COMPLETE
