"""Tests for the full-assessment drafting stage (TECH_SPEC §5.1 FULL_DRAFTING,
§8.1, §9.3). LLM-free throughout (§15): a scripted transport plays every
specialist, and fixture KBs (schema-only, via retrieval.db.write_kb) exercise
the real fetch/search path without needing corpus content.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agents.prompting import (
    owned_subquestions,
    response_type_of,
    specialist_friendly_name,
    specialist_owned_sections,
)
from agents.specialist import AgentError, run_specialist
from llm import LLMClient, ScriptedTransport, resolve_model
from retrieval.db import write_kb
from retrieval.retrieve import KB
from run import FakeCommitter, _make_pulse, run_pipeline
from stages.context import StageContext
from stages.full import SPECIALISTS, _specialist_concurrency, full_drafting
from statefile import RunState, Stage, StageStatus
from status import StatusModel

_NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_specialists_tuple_matches_sections_json(sections):
    assert list(SPECIALISTS) == sections["specialists"]


# -- fixture KB root -------------------------------------------------------------


def _build_kb_root(tmp_path: Path) -> Path:
    """An empty-but-real KB (schema only, zero documents) + a trivial index per
    specialist — enough for the seed `kb.search()` call to run for real and
    return nothing, without needing corpus content."""
    kb_root = tmp_path / "kb"
    kb_root.mkdir()
    for specialist in SPECIALISTS:
        write_kb(kb_root / f"{specialist}.sqlite", [], _NOW)
        index = {"specialist": specialist, "generated_at": _NOW, "documents": []}
        (kb_root / f"{specialist}.index.json").write_text(json.dumps(index), encoding="utf-8")
    return kb_root


def _draft_sections(specialist_id: str) -> dict[str, str]:
    out = {}
    for sid in specialist_owned_sections(specialist_id):
        if response_type_of(sid) == "yes_no_na":
            out[sid] = f"Yes. {specialist_id} is satisfied for {sid} based on the outline."
        else:
            out[sid] = f"Recorded for {sid}: the project's document management system."
    return out


def _draft_response(specialist_id: str, *, questions: dict | None = None) -> str:
    return json.dumps(
        {
            "action": "draft",
            "sections": _draft_sections(specialist_id),
            "citations": {},
            "questions": questions or {"why": "", "items": []},
            "gaps": [],
        }
    )


def _handler_all_draft_immediately(questions_by_specialist: dict[str, dict] | None = None):
    questions_by_specialist = questions_by_specialist or {}

    def handler(*, model, system, user, response_json):
        for specialist in SPECIALISTS:
            if f"sections owned by {specialist_friendly_name(specialist)}" in user:
                return _draft_response(
                    specialist, questions=questions_by_specialist.get(specialist)
                )
        raise AssertionError(f"could not identify specialist from prompt: {user[:200]!r}")

    return handler


def _architect_response() -> str:
    """A minimal valid Implementation Plan tracing one step to a section privacy
    drafts (7.1) — enough to carry the driver past ARCHITECT."""
    return json.dumps(
        {
            "overview": "Build and deploy the system in three sequenced phases.",
            "steps": [
                {
                    "title": "Encrypt personal data at rest and in transit",
                    "detail": "Use platform-managed AES-256 for storage and TLS 1.3 in transit.",
                    "traces_to": [
                        {"specialist": "privacy", "section": "7.1", "mitigation": "encryption"}
                    ],
                }
            ],
        }
    )


def _handler_full_then_architect(questions_by_specialist: dict[str, dict] | None = None):
    """Serves the six specialist drafts and, once they are final, the architect —
    so a no-questions run drives FULL_DRAFTING → ARCHITECT in one dispatch."""
    specialist_handler = _handler_all_draft_immediately(questions_by_specialist)

    def handler(*, model, system, user, response_json):
        if "Completed specialist assessment" in user:
            return _architect_response()
        return specialist_handler(
            model=model, system=system, user=user, response_json=response_json
        )

    return handler


# -- run_specialist: the retrieval tool loop + validation ------------------------


def _client(handler) -> LLMClient:
    return LLMClient(transport=ScriptedTransport(handler=handler))


def _open_empty_kb(tmp_path: Path, name: str = "spec") -> KB:
    path = tmp_path / f"{name}.sqlite"
    write_kb(path, [], _NOW)
    return KB(path)


def test_run_specialist_drafts_immediately(tmp_path):
    kb = _open_empty_kb(tmp_path)
    client = _client(_handler_all_draft_immediately())
    draft = run_specialist(client, "privacy", "outline text", "threshold text", kb, "{}")
    assert set(draft.sections) == set(specialist_owned_sections("privacy"))
    assert draft.questions == []
    assert draft.gaps == []
    kb.close()


def test_run_specialist_tool_loop_then_draft(tmp_path):
    kb = _open_empty_kb(tmp_path)
    calls = {"n": 0}

    def handler(*, model, system, user, response_json):
        calls["n"] += 1
        if calls["n"] == 1:
            return json.dumps({"action": "search", "query": "fairness", "k": 5})
        return _draft_response("ethics")

    client = _client(handler)
    draft = run_specialist(client, "ethics", "outline", "threshold", kb, "{}")
    assert calls["n"] == 2
    assert set(draft.sections) == set(specialist_owned_sections("ethics"))
    kb.close()


def test_run_specialist_narrates_retrieval_events(tmp_path):
    kb = _open_empty_kb(tmp_path)

    # One search round (returns nothing, since the KB is empty) then a draft —
    # the point is that an empty result set doesn't crash the narration path.
    def one_round_then_draft(*, model, system, user, response_json):
        if "This turn (round 1" in user:
            return json.dumps({"action": "search", "query": "x", "k": 5})
        return _draft_response("legal")

    client = _client(one_round_then_draft)
    run = RunState.new("WT-TEST-99")
    status = StatusModel.initial(run)
    draft = run_specialist(
        client,
        "legal",
        "outline",
        "threshold",
        kb,
        "{}",
        status=status,
        node_id="full.specialist.legal",
        max_rounds=4,
    )
    assert set(draft.sections) == set(specialist_owned_sections("legal"))
    kb.close()


def test_run_specialist_forces_draft_after_max_rounds(tmp_path):
    kb = _open_empty_kb(tmp_path)

    def always_search(*, model, system, user, response_json):
        if "Final round" in user:
            return _draft_response("data_governance")
        return json.dumps({"action": "search", "query": "x", "k": 3})

    client = _client(always_search)
    draft = run_specialist(client, "data_governance", "o", "t", kb, "{}", max_rounds=2)
    assert set(draft.sections) == set(specialist_owned_sections("data_governance"))
    kb.close()


def test_run_specialist_raises_if_forced_round_still_no_draft(tmp_path):
    kb = _open_empty_kb(tmp_path)
    client = _client(lambda **_: json.dumps({"action": "search", "query": "x"}))
    with pytest.raises(AgentError, match="forced final round"):
        run_specialist(client, "it_security", "o", "t", kb, "{}", max_rounds=1)
    kb.close()


# -- validation: structural write-scope + gap/section discipline (§9.3) ---------


def _bad_draft(specialist_id: str, **overrides) -> str:
    payload = {
        "action": "draft",
        "sections": _draft_sections(specialist_id),
        "citations": {},
        "questions": {"why": "", "items": []},
        "gaps": [],
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_rejects_out_of_scope_section(tmp_path):
    kb = _open_empty_kb(tmp_path)
    sections = _draft_sections("privacy")
    sections["5.1"] = "Yes. out of scope."  # owned by ethics, not privacy
    client = _client(lambda **_: _bad_draft("privacy", sections=sections))
    with pytest.raises(AgentError, match="out-of-scope"):
        run_specialist(client, "privacy", "o", "t", kb, "{}")
    kb.close()


def test_rejects_section_neither_drafted_nor_gapped(tmp_path):
    kb = _open_empty_kb(tmp_path)
    sections = _draft_sections("privacy")
    del sections["7.2"]
    client = _client(lambda **_: _bad_draft("privacy", sections=sections))
    with pytest.raises(AgentError, match="neither drafted nor flagged"):
        run_specialist(client, "privacy", "o", "t", kb, "{}")
    kb.close()


def test_rejects_section_both_drafted_and_gapped(tmp_path):
    kb = _open_empty_kb(tmp_path)
    client = _client(
        lambda **_: _bad_draft("privacy", gaps=[{"section": "7.2", "reason": "unknown"}])
    )
    with pytest.raises(AgentError, match="both drafted and flagged"):
        run_specialist(client, "privacy", "o", "t", kb, "{}")
    kb.close()


def test_rejects_yes_no_na_without_prefix(tmp_path):
    kb = _open_empty_kb(tmp_path)
    sections = _draft_sections("privacy")
    sections["7.1"] = "The APPs are complied with, we think."
    client = _client(lambda **_: _bad_draft("privacy", sections=sections))
    with pytest.raises(AgentError, match="yes/no/N-A"):
        run_specialist(client, "privacy", "o", "t", kb, "{}")
    kb.close()


def test_rejects_too_many_questions(tmp_path):
    kb = _open_empty_kb(tmp_path)
    items = [{"question_id": f"privacy-{i}", "text": f"q{i}"} for i in range(1, 5)]
    client = _client(
        lambda **_: _bad_draft("privacy", questions={"why": "need facts", "items": items})
    )
    with pytest.raises(AgentError, match="exceeds the cap"):
        run_specialist(client, "privacy", "o", "t", kb, "{}")
    kb.close()


def test_rejects_gap_for_out_of_scope_section(tmp_path):
    kb = _open_empty_kb(tmp_path)
    client = _client(
        lambda **_: _bad_draft("privacy", gaps=[{"section": "5.1", "reason": "not mine"}])
    )
    with pytest.raises(AgentError, match="out-of-scope"):
        run_specialist(client, "privacy", "o", "t", kb, "{}")
    kb.close()


# -- sub-question folding (§9.3): 12.2.1/12.2.2 → 12.2, losslessly --------------


def test_owned_subquestions_maps_only_sections_with_nested_questions():
    # 12.2 'Legal advice' and 8.4 are the only DTA sections carrying sub-questions.
    assert owned_subquestions(specialist_owned_sections("legal"))["12.2"] == ("12.2.1", "12.2.2")
    assert owned_subquestions(specialist_owned_sections("ethics"))["8.4"] == ("8.4.1", "8.4.2")
    # A specialist with no nested-question sections gets an empty map.
    assert owned_subquestions(specialist_owned_sections("it_security")) == {}


def test_folds_subquestion_keys_into_owned_parent(tmp_path):
    """The reported WT-H2A8-H3 failure: the legal specialist keyed its answer by
    12.2.1/12.2.2 — the instrument's real sub-questions of the owned section 12.2 —
    instead of 12.2. They fold into the single owned parent, losslessly, rather than
    failing the run as out-of-scope (§9.3)."""
    kb = _open_empty_kb(tmp_path)
    sections = _draft_sections("legal")
    del sections["12.2"]
    sections["12.2.1"] = "Yes, we identified the need for legal advice during scoping."
    sections["12.2.2"] = "Stored in the departmental records management system."
    client = _client(lambda **_: _bad_draft("legal", sections=sections))
    draft = run_specialist(client, "legal", "o", "t", kb, "{}")
    assert "12.2" in draft.sections
    assert "12.2.1" not in draft.sections and "12.2.2" not in draft.sections
    # Concatenated in instrument order → the folded parent still opens with the Yes
    # of 12.2.1 (12.2 is yes_no_na), and 12.2.2's content is preserved.
    assert draft.sections["12.2"].startswith("Yes, we identified")
    assert "records management system" in draft.sections["12.2"]
    kb.close()


def test_folds_subquestion_citations_onto_parent(tmp_path):
    kb = _open_empty_kb(tmp_path)
    sections = _draft_sections("legal")
    del sections["12.2"]
    sections["12.2.1"] = "Yes, legal advice was sought early."
    sections["12.2.2"] = "Held in the case management system."
    citations = {"12.2.1": [{"short_name": "Legal-Memo", "locator": "p.3"}]}
    client = _client(lambda **_: _bad_draft("legal", sections=sections, citations=citations))
    draft = run_specialist(client, "legal", "o", "t", kb, "{}")
    assert "12.2.1" not in draft.citations
    assert draft.citations["12.2"] == [{"short_name": "Legal-Memo", "locator": "p.3"}]
    kb.close()


def test_fold_still_rejects_a_true_out_of_scope_key(tmp_path):
    """Folding is scoped to instrument sub-questions of *owned* sections. A deeper id
    whose parent the specialist does not own is not folded — the structural write-scope
    guard still rejects it loudly (§9.3)."""
    kb = _open_empty_kb(tmp_path)
    sections = _draft_sections("legal")
    sections["7.1.1"] = "Yes. this belongs to privacy, not legal."
    client = _client(lambda **_: _bad_draft("legal", sections=sections))
    with pytest.raises(AgentError, match="out-of-scope"):
        run_specialist(client, "legal", "o", "t", kb, "{}")
    kb.close()


# -- the stage handler, direct call ----------------------------------------------


def _make_full_drafting_run_dir(tmp_path) -> Path:
    run_dir = tmp_path / "runs" / "WT-TEST-FULL"
    run_dir.mkdir(parents=True)
    (run_dir / "brainstorm").mkdir()
    (run_dir / "brainstorm" / "outline.md").write_text(
        "# Outline\nAn AI triage assistant for citizen enquiries.\n", encoding="utf-8"
    )
    (run_dir / "threshold").mkdir()
    (run_dir / "threshold" / "threshold_assessment.md").write_text(
        "# Threshold\nOverall inherent risk rating (highest-wins): Medium\n", encoding="utf-8"
    )
    return run_dir


def test_full_drafting_writes_every_specialist_no_questions(tmp_path):
    run_dir = _make_full_drafting_run_dir(tmp_path)
    kb_root = _build_kb_root(tmp_path)
    run = RunState.new("WT-TEST-FULL")
    run.advance_to(Stage.FULL_DRAFTING)
    status = StatusModel.initial(run)
    ctx = StageContext(
        run_dir=run_dir,
        run=run,
        status=status,
        llm=_client(_handler_all_draft_immediately()),
        kb_root=kb_root,
    )
    full_drafting(ctx)

    for specialist in SPECIALISTS:
        data = json.loads((run_dir / "full" / "specialists" / f"{specialist}.json").read_text())
        assert set(data["sections"]) == set(specialist_owned_sections(specialist))
        assert (run_dir / "full" / "specialists" / f"{specialist}.md").is_file()
        assert status.nodes[f"full.specialist.{specialist}"] == "complete"
    # The questions file is always written (it closes the stage's checkpoint,
    # run.py) — empty specialists ⇒ no pause.
    payload = json.loads((run_dir / "full" / "questions.json").read_text())
    assert payload["specialists"] == []


def test_full_drafting_writes_questions_when_raised(tmp_path):
    run_dir = _make_full_drafting_run_dir(tmp_path)
    kb_root = _build_kb_root(tmp_path)
    run = RunState.new("WT-TEST-FULL2")
    run.advance_to(Stage.FULL_DRAFTING)
    status = StatusModel.initial(run)
    q = {
        "why": "Asking so the privacy risk rests on fact, not assumption.",
        "items": [{"question_id": "privacy-1", "text": "Where is personal data stored?"}],
    }
    ctx = StageContext(
        run_dir=run_dir,
        run=run,
        status=status,
        llm=_client(_handler_all_draft_immediately({"privacy": q})),
        kb_root=kb_root,
    )
    full_drafting(ctx)

    payload = json.loads((run_dir / "full" / "questions.json").read_text())
    assert payload["counts"] == {"total": 1, "answered": 0, "skipped": 0}
    assert payload["specialists"][0]["node_id"] == "full.specialist.privacy"
    assert payload["specialists"][0]["items"][0]["question_id"] == "privacy-1"
    events = [e.type for e in status.log if e.type == "question_raised"]
    assert events == ["question_raised"]


# -- the driver end-to-end --------------------------------------------------------


def _seed_full_drafting_run(run_dir: Path, run_id: str) -> None:
    run = RunState.new(run_id)
    run.advance_to(Stage.FULL_DRAFTING)
    run.save(run_dir)
    StatusModel.initial(run).save(run_dir)
    (run_dir / "brainstorm").mkdir(parents=True, exist_ok=True)
    (run_dir / "brainstorm" / "outline.md").write_text("# Outline\nAn AI triage tool.\n")
    (run_dir / "threshold").mkdir(exist_ok=True)
    (run_dir / "threshold" / "threshold_assessment.md").write_text(
        "# Threshold\nOverall inherent risk rating (highest-wins): Medium\n"
    )


def test_pipeline_pauses_at_full_checkpoint_when_questions_raised(tmp_path):
    run_dir = tmp_path / "WT-TEST-CP"
    run_dir.mkdir()
    _seed_full_drafting_run(run_dir, "WT-TEST-CP")
    kb_root = _build_kb_root(tmp_path)
    q = {
        "why": "need the fact",
        "items": [{"question_id": "ethics-1", "text": "Any pilot planned?"}],
    }

    result = run_pipeline(
        run_dir,
        llm=_client(_handler_all_draft_immediately({"ethics": q})),
        committer=FakeCommitter(),
        kb_root=kb_root,
    )

    assert result.ok
    assert result.final_stage is Stage.FULL_CHECKPOINT
    assert result.stage_status is StageStatus.AWAITING_USER
    status = json.loads((run_dir / "status.json").read_text())
    assert status["overall_state"] == "paused"
    assert status["nodes"]["full.checkpoint"] == "waiting_user"
    assert status["questions"]["specialists"][0]["node_id"] == "full.specialist.ethics"


def test_pipeline_skips_checkpoint_when_no_questions(tmp_path):
    run_dir = tmp_path / "WT-TEST-NOQ"
    run_dir.mkdir()
    _seed_full_drafting_run(run_dir, "WT-TEST-NOQ")
    kb_root = _build_kb_root(tmp_path)

    result = run_pipeline(
        run_dir,
        llm=_client(_handler_full_then_architect()),
        committer=FakeCommitter(),
        kb_root=kb_root,
    )

    # The driver skipped FULL_CHECKPOINT/FULL_REVISING (no questions — the
    # always-written questions file has an empty specialists list) and ran
    # ARCHITECT straight through; REVIEW is not built yet, so the calm, resumable
    # failure there is the documented stopping point. The architect appendix
    # having been written proves the skip landed at ARCHITECT, not a needless pause.
    assert result.ok is False
    questions = json.loads((run_dir / "full" / "questions.json").read_text())
    assert questions["specialists"] == []
    assert (run_dir / "full" / "architect.md").is_file()
    run = RunState.load(run_dir)
    assert run.stage is Stage.REVIEW
    assert run.stage_status is StageStatus.FAILED


def test_pipeline_is_idempotent_on_full_drafting_resume(tmp_path):
    run_dir = tmp_path / "WT-TEST-IDEM"
    run_dir.mkdir()
    _seed_full_drafting_run(run_dir, "WT-TEST-IDEM")
    kb_root = _build_kb_root(tmp_path)

    run_pipeline(
        run_dir,
        llm=_client(_handler_full_then_architect()),
        committer=FakeCommitter(),
        kb_root=kb_root,
    )
    run = RunState.load(run_dir)
    assert run.stage is Stage.REVIEW  # advanced past FULL_DRAFTING and ARCHITECT already

    run.advance_to(Stage.FULL_DRAFTING)
    run.save(run_dir)

    class _Boom:
        def generate(self, **_):
            raise AssertionError("model must not be called on an idempotent resume")

    result = run_pipeline(
        run_dir,
        llm=LLMClient(transport=_Boom()),
        committer=FakeCommitter(),
        kb_root=kb_root,
    )
    # Still fails at REVIEW (not built), but crucially without re-calling the model:
    # both FULL_DRAFTING and ARCHITECT checkpoints already exist and are skipped.
    assert result.ok is False
    run = RunState.load(run_dir)
    assert run.stage is Stage.REVIEW


def test_pipeline_fails_calmly_when_a_specialist_errors(tmp_path):
    run_dir = tmp_path / "WT-TEST-ERR"
    run_dir.mkdir()
    _seed_full_drafting_run(run_dir, "WT-TEST-ERR")
    kb_root = _build_kb_root(tmp_path)

    def handler(*, model, system, user, response_json):
        for specialist in SPECIALISTS:
            if f"sections owned by {specialist_friendly_name(specialist)}" in user:
                return "not json at all" if specialist == "legal" else _draft_response(specialist)
        raise AssertionError(f"could not identify specialist from prompt: {user[:200]!r}")

    result = run_pipeline(run_dir, llm=_client(handler), committer=FakeCommitter(), kb_root=kb_root)

    assert result.ok is False
    run = RunState.load(run_dir)
    # legal is the only worker that raised, so its node is the only one left
    # "active" when the driver scans (§5.6) — the failure is attributed to it.
    assert run.stage is Stage.FULL_DRAFTING
    assert run.stage_status is StageStatus.FAILED
    status = json.loads((run_dir / "status.json").read_text())
    assert status["failure"]["stage"] == "full.specialist.legal"
    assert status["nodes"]["full.specialist.legal"] == "failed"
    assert not (run_dir / "full" / "specialists" / "legal.json").exists()
    # Under the §5.4 fan-out the other five run concurrently with legal: each is
    # either complete (it finished — kept, with its draft on disk for the §5.3
    # idempotent resume) or pending (cancelled before it started). Never a
    # half-state, and the stage checkpoint (questions.json) is never written.
    for other in set(SPECIALISTS) - {"legal"}:
        state = status["nodes"][f"full.specialist.{other}"]
        assert state in ("complete", "pending")
        assert (run_dir / "full" / "specialists" / f"{other}.json").exists() == (
            state == "complete"
        )
    assert not (run_dir / "full" / "questions.json").exists()


def test_llm_role_resolves_to_flash_for_specialist():
    # Sanity check that the "specialist" role is registered (config/models.yml)
    # and every specialist call routes through it, not a per-specialist role.
    assert resolve_model("specialist")


# -- the §5.4 fan-out: bounded concurrency, single-writer commits -----------------


def test_specialist_concurrency_comes_from_budgets_yml():
    # The fan-out width is a §13 rate knob owned by config/budgets.yml — the
    # committed value is 3 (raise toward 6 as Gemini quota allows). The barrier
    # test below is calibrated to this value; change them together.
    assert _specialist_concurrency() == 3


def test_full_drafting_fans_out_concurrently_within_bound(tmp_path):
    """Proves the fan-out is real and bounded (§5.4): a 3-party barrier inside the
    transport only releases when three specialists are simultaneously mid-call, so
    a serial implementation times the barrier out rather than passing; a counter
    proves in-flight never exceeds the configured bound. The §6.3 log contract
    must survive the concurrency: event ids unique and monotonic."""
    run_dir = _make_full_drafting_run_dir(tmp_path)
    kb_root = _build_kb_root(tmp_path)
    run = RunState.new("WT-TEST-CONC")
    run.advance_to(Stage.FULL_DRAFTING)
    status = StatusModel.initial(run)

    # Six specialists at one call each = two clean releases of a 3-party barrier.
    barrier = threading.Barrier(3)
    gate = threading.Lock()
    inflight = {"now": 0, "max": 0}
    inner = _handler_all_draft_immediately()

    def handler(*, model, system, user, response_json):
        with gate:
            inflight["now"] += 1
            inflight["max"] = max(inflight["max"], inflight["now"])
        try:
            barrier.wait(timeout=30)  # broken barrier (= serial execution) fails loudly
            return inner(model=model, system=system, user=user, response_json=response_json)
        finally:
            with gate:
                inflight["now"] -= 1

    ctx = StageContext(
        run_dir=run_dir, run=run, status=status, llm=_client(handler), kb_root=kb_root
    )
    full_drafting(ctx)

    assert inflight["max"] == 3  # the barrier forced 3 up; the pool bound stopped a 4th
    for specialist in SPECIALISTS:
        assert status.nodes[f"full.specialist.{specialist}"] == "complete"
        assert (run_dir / "full" / "specialists" / f"{specialist}.json").is_file()
    ids = [e.id for e in status.log]
    assert len(ids) == len(set(ids)), "concurrent narration minted a duplicate event id"
    assert ids == sorted(ids), "event ids must stay monotonic (§6.3)"


def test_full_drafting_commits_only_from_the_coordinating_thread(tmp_path):
    """The §14 single-writer property under the fan-out: workers narrate (start,
    drafting, retrieval) from their own threads, but every publish those narrations
    request must be made by the coordinating thread — a worker-side commit would
    race the git working copy."""
    run_dir = _make_full_drafting_run_dir(tmp_path)
    kb_root = _build_kb_root(tmp_path)
    run = RunState.new("WT-TEST-1WRT")
    run.advance_to(Stage.FULL_DRAFTING)
    status = StatusModel.initial(run)

    class ThreadRecordingCommitter(FakeCommitter):
        def __init__(self):
            super().__init__()
            self.threads: list[int] = []

        def commit(self, run_dir, message):
            self.threads.append(threading.get_ident())
            return super().commit(run_dir, message)

    committer = ThreadRecordingCommitter()
    # min_interval_s=0: every drained pulse publishes, maximising the chance a
    # worker-side commit path (if one existed) would be caught red-handed.
    status.pulse = _make_pulse(run_dir, status, committer, min_interval_s=0.0)
    ctx = StageContext(
        run_dir=run_dir,
        run=run,
        status=status,
        llm=_client(_handler_all_draft_immediately()),
        kb_root=kb_root,
    )
    full_drafting(ctx)

    assert committer.count > 0  # narration was published while the fan-out ran
    assert set(committer.threads) == {threading.get_ident()}


def test_full_drafting_resume_skips_committed_drafts_and_keeps_their_questions(tmp_path):
    """Per-specialist idempotence under the fan-out (§5.3): drafts already committed
    are not re-run — only the missing specialists are submitted to the pool — and a
    skipped specialist's committed questions still reach the batched payload."""
    run_dir = _make_full_drafting_run_dir(tmp_path)
    kb_root = _build_kb_root(tmp_path)
    run = RunState.new("WT-TEST-SKIP")
    run.advance_to(Stage.FULL_DRAFTING)
    status = StatusModel.initial(run)

    q = {
        "why": "the privacy risk should rest on fact",
        "items": [
            {
                "question_id": "privacy-1",
                "text": "Where is personal data stored?",
                "options": None,
                "allow_free_text": True,
            }
        ],
    }
    seeded = {"privacy": q, "legal": {"why": "", "items": []}}
    specialists_dir = run_dir / "full" / "specialists"
    specialists_dir.mkdir(parents=True)
    for specialist, questions in seeded.items():
        (specialists_dir / f"{specialist}.json").write_text(
            json.dumps(
                {
                    "specialist": specialist,
                    "sections": _draft_sections(specialist),
                    "citations": {},
                    "questions": questions,
                    "gaps": [],
                    "provenance": {"model": "prior", "prompt_version": "v1"},
                }
            ),
            encoding="utf-8",
        )

    calls = {"n": 0}
    gate = threading.Lock()
    inner = _handler_all_draft_immediately()

    def handler(*, model, system, user, response_json):
        for skipped in seeded:
            assert f"sections owned by {specialist_friendly_name(skipped)}" not in user, (
                f"{skipped} has a committed draft and must not be re-run (§5.3)"
            )
        with gate:
            calls["n"] += 1
        return inner(model=model, system=system, user=user, response_json=response_json)

    ctx = StageContext(
        run_dir=run_dir, run=run, status=status, llm=_client(handler), kb_root=kb_root
    )
    full_drafting(ctx)

    assert calls["n"] == len(SPECIALISTS) - len(seeded)  # one call per missing draft
    payload = json.loads((run_dir / "full" / "questions.json").read_text())
    assert [s["node_id"] for s in payload["specialists"]] == ["full.specialist.privacy"]
    assert payload["specialists"][0]["items"][0]["question_id"] == "privacy-1"
