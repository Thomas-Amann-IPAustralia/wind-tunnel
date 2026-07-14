"""Run-state core tests: run codes (§3), run.json (§4/§5), status.json (§6).

These exercise the LLM-free state machine and its projection — the resume model
the whole pipeline rests on. Kept in pipeline/tests/ (a mandated pytest target,
CLAUDE.md §4).
"""

from __future__ import annotations

import json

import pytest

import runcode
import status
from statefile import (
    REVISION_ARTEFACTS,
    Phase,
    RunState,
    Stage,
    StageStatus,
    StateError,
)
from status import Event, StatusError, StatusModel

# ------------------------------------------------------------------ run codes


def test_generate_matches_format_and_alphabet():
    for _ in range(200):
        code = runcode.generate()
        assert runcode.RUN_CODE_RE.match(code), code
        assert runcode.is_valid(code)
        assert code == code.upper()
        # WT- + 4 + - + 2 = 10 chars
        assert len(code) == 10
        body = code.removeprefix("WT-").replace("-", "")
        assert all(ch in runcode.ALPHABET for ch in body)


def test_alphabet_excludes_ambiguous_symbols():
    for ch in "ILOUV01":
        assert ch not in runcode.ALPHABET
    assert len(runcode.ALPHABET) == 29


def test_normalize_uppercases_and_trims():
    assert runcode.normalize("  wt-7k3d-q2 ") == "WT-7K3D-Q2"


def test_validate_roundtrips_and_rejects():
    assert runcode.validate(" wt-7k3d-q2 ") == "WT-7K3D-Q2"
    for bad in ["", "WT-7K3D", "WT-7K3D-Q2X", "XX-7K3D-Q2", "WT-7K3D-Q0", "WT-IL3D-Q2"]:
        with pytest.raises(runcode.RunCodeError):
            runcode.validate(bad)


def test_is_valid_is_strict_not_normalising():
    assert not runcode.is_valid("wt-7k3d-q2")  # lower-case fails strict check
    assert runcode.is_valid("WT-7K3D-Q2")


def test_generate_unique_uses_predicate_and_exhausts():
    taken = {runcode.generate() for _ in range(3)}
    code = runcode.generate_unique(lambda c: c in taken)
    assert code not in taken
    # Predicate that never frees anything → exhaustion is a loud error, never a dup.
    with pytest.raises(runcode.RunCodeError):
        runcode.generate_unique(lambda c: True, attempts=5)
    with pytest.raises(ValueError):
        runcode.generate_unique(lambda c: False, attempts=0)


# ------------------------------------------------------------------ run.json


def test_new_run_defaults():
    r = RunState.new("WT-7K3D-Q2", now="2026-07-11T00:00:00Z")
    assert r.stage is Stage.BRAINSTORM
    assert r.stage_status is StageStatus.IN_PROGRESS
    assert r.phase is Phase.THRESHOLD
    assert r.revisions == {a: 0 for a in REVISION_ARTEFACTS}
    assert r.review_cycles == 0
    assert r.attestation == {"sensitivity_ceiling": "OFFICIAL", "attested": False}
    assert r.last_error is None
    assert r.created_at == r.updated_at == "2026-07-11T00:00:00Z"


def test_run_json_roundtrip():
    r = RunState.new("WT-7K3D-Q2", now="2026-07-11T00:00:00Z")
    r.advance_to(Stage.FULL_DRAFTING, now="2026-07-11T01:00:00Z")
    r.record_revision("threshold", now="2026-07-11T01:01:00Z")
    r.set_checkpoint(Stage.THRESHOLD_RECONCILING, "9b02d4a", now="2026-07-11T01:02:00Z")
    again = RunState.from_dict(r.to_dict())
    assert again.to_dict() == r.to_dict()


def test_from_dict_rejects_unknown_enums_and_missing_fields():
    good = RunState.new("WT-7K3D-Q2").to_dict()
    for field_name, bad in [("stage", "NOPE"), ("stage_status", "nope"), ("phase", "nope")]:
        d = dict(good, **{field_name: bad})
        with pytest.raises(StateError):
            RunState.from_dict(d)
    incomplete = dict(good)
    del incomplete["run_id"]
    with pytest.raises(StateError):
        RunState.from_dict(incomplete)
    with pytest.raises(StateError):
        RunState.from_dict(dict(good, schema_version=99))


def test_save_load_is_atomic(tmp_path):
    r = RunState.new("WT-7K3D-Q2")
    r.save(tmp_path)
    assert (tmp_path / "run.json").is_file()
    assert not (tmp_path / "run.json.tmp").exists()
    loaded = RunState.load(tmp_path)
    assert loaded.to_dict() == r.to_dict()


def test_load_missing_and_malformed(tmp_path):
    with pytest.raises(StateError):
        RunState.load(tmp_path)
    (tmp_path / "run.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(StateError):
        RunState.load(tmp_path)


def test_phase_derives_from_stage():
    r = RunState.new("WT-7K3D-Q2")
    r.advance_to(Stage.FULL_DRAFTING)
    assert r.phase is Phase.FULL
    r.advance_to(Stage.CONCLUDED)
    assert r.phase is Phase.THRESHOLD
    r.advance_to(Stage.USER_REVISION)
    assert r.phase is Phase.FULL


def test_fail_preserves_stage_and_phase_for_resume():
    r = RunState.new("WT-7K3D-Q2")
    r.advance_to(Stage.FULL_DRAFTING)
    r.fail("full.specialist.privacy", "A step didn't complete.", "GeminiRateLimitError")
    # stage stays put so resume restarts it from its last checkpoint (§5.3/§5.6).
    assert r.stage is Stage.FULL_DRAFTING
    assert r.phase is Phase.FULL
    assert r.stage_status is StageStatus.FAILED
    assert r.last_error == {
        "stage": "full.specialist.privacy",
        "message": "A step didn't complete.",
        "technical": "GeminiRateLimitError",
    }


def test_advance_clears_prior_error():
    r = RunState.new("WT-7K3D-Q2")
    r.fail("full.reviewer", "boom", "tech")
    r.advance_to(Stage.ASSEMBLY)
    assert r.last_error is None
    assert r.stage_status is StageStatus.IN_PROGRESS


def test_checkpoints():
    r = RunState.new("WT-7K3D-Q2")
    assert not r.has_checkpoint(Stage.THRESHOLD_DRAFTING)
    r.set_checkpoint(Stage.THRESHOLD_DRAFTING, "3af9c1e")
    assert r.has_checkpoint(Stage.THRESHOLD_DRAFTING)
    assert r.to_dict()["checkpoints"]["THRESHOLD_DRAFTING"] == "3af9c1e"


def test_revision_cap_holds():
    r = RunState.new("WT-7K3D-Q2")
    assert r.can_revise("full")
    assert r.record_revision("full") == 1
    assert r.record_revision("full") == 2
    assert not r.can_revise("full")
    with pytest.raises(StateError):
        r.record_revision("full")
    with pytest.raises(StateError):
        r.record_revision("not_an_artefact")


def test_review_cycle_cap_holds():
    r = RunState.new("WT-7K3D-Q2")
    assert r.can_review_again()
    assert r.record_review_cycle() == 1
    assert r.record_review_cycle() == 2
    assert not r.can_review_again()
    with pytest.raises(StateError):
        r.record_review_cycle()


# ------------------------------------------------------------------ status.json

EXPECTED_NODE_IDS = (
    "threshold.generalist_a",
    "threshold.generalist_b",
    "threshold.reconciler",
    "threshold.rating_engine",
    "full.specialist.it_security",
    "full.specialist.privacy",
    "full.specialist.ethics",
    "full.specialist.legal",
    "full.specialist.data_governance",
    "full.specialist.solution_architect",
    "full.checkpoint",
    "full.architect",
    "full.reviewer",
    "full.assembly",
)


@pytest.fixture
def fresh() -> StatusModel:
    r = RunState.new("WT-7K3D-Q2", now="2026-07-11T00:00:00Z")
    return StatusModel.initial(r, now="2026-07-11T00:00:00Z")


def test_node_topology_matches_spec():
    assert status.node_ids() == EXPECTED_NODE_IDS


def test_specialist_nodes_derive_from_sections_json():
    # friendly names + owned sections come from instrument/sections.json (one owner).
    assert status.friendly_name("full.specialist.privacy") == "Privacy specialist"
    privacy = next(n for n in status.node_specs() if n.node_id == "full.specialist.privacy")
    assert privacy.owns == "7.1, 7.2"
    ethics = next(n for n in status.node_specs() if n.node_id == "full.specialist.ethics")
    assert ethics.owns == "5.1, 5.2, 8.1, 8.2, 8.4, 8.5, 10.1"
    with pytest.raises(StatusError):
        status.friendly_name("full.specialist.nope")


def test_initial_is_whole_graph_and_pending(fresh):
    assert set(fresh.nodes) == set(EXPECTED_NODE_IDS)
    assert all(state == "pending" for state in fresh.nodes.values())
    assert fresh.overall_state == "running"
    assert fresh.log == []
    assert fresh.log_cursor == 0
    assert fresh.questions is None and fresh.failure is None
    assert fresh.expected_ranges is not None


def test_vocabulary_sets_are_exactly_the_spec():
    assert status.NODE_STATES == frozenset(
        {"pending", "active", "waiting_user", "complete", "failed"}
    )
    assert status.OVERALL_STATES == frozenset({"running", "paused", "failed", "complete"})
    assert status.EVENT_TYPES == frozenset(
        {
            "stage_started",
            "retrieval",
            "drafting",
            "question_raised",
            "revision",
            "review_finding",
            "stage_complete",
            "heartbeat",
            "error",
        }
    )


def test_start_and_complete_couple_events(fresh):
    evt = fresh.start_node("threshold.generalist_a", now="2026-07-11T00:00:01Z")
    assert fresh.nodes["threshold.generalist_a"] == "active"
    assert evt.id == "evt_000001" and evt.type == "stage_started"
    assert fresh.log_cursor == 1
    evt2 = fresh.complete_node("threshold.generalist_a", now="2026-07-11T00:00:02Z")
    assert fresh.nodes["threshold.generalist_a"] == "complete"
    assert evt2.id == "evt_000002" and evt2.type == "stage_complete"
    assert fresh.updated_at == "2026-07-11T00:00:02Z"


def test_fail_node_sets_failure_payload(fresh):
    fresh.start_node("full.specialist.privacy")
    evt = fresh.fail_node(
        "full.specialist.privacy",
        "A step didn't complete. Your progress is saved.",
        "GeminiRateLimitError after 5 retries",
    )
    assert fresh.nodes["full.specialist.privacy"] == "failed"
    assert evt.type == "error"
    assert fresh.overall_state == "failed"
    assert fresh.failure == {
        "stage": "full.specialist.privacy",
        "message": "A step didn't complete. Your progress is saved.",
        "run_code": "WT-7K3D-Q2",
        "technical": "GeminiRateLimitError after 5 retries",
    }


def test_unknown_node_id_raises(fresh):
    with pytest.raises(StatusError):
        fresh.start_node("threshold.nope")
    with pytest.raises(StatusError):
        fresh.retrieval("nope", "reading")


def test_wait_node_pauses(fresh):
    fresh.wait_node("full.checkpoint")
    assert fresh.nodes["full.checkpoint"] == "waiting_user"
    assert fresh.overall_state == "paused"


def test_event_ordinals_are_monotonic_unique_and_padded(fresh):
    fresh.start_node("threshold.generalist_a")
    fresh.start_node("threshold.generalist_b")
    fresh.heartbeat()
    fresh.complete_node("threshold.generalist_a")
    ids = [e.id for e in fresh.log]
    assert ids == ["evt_000001", "evt_000002", "evt_000003", "evt_000004"]
    assert len(set(ids)) == len(ids)
    assert fresh.log_cursor == len(fresh.log)


def test_ephemeral_events_do_not_change_node_state(fresh):
    fresh.start_node("full.specialist.privacy")
    fresh.retrieval(
        "full.specialist.privacy", "reading OAIC PIA guidance", doc="OAIC PIA", locator="p.14"
    )
    fresh.drafting("full.specialist.privacy", "drafting §7.1", section="7.1")
    fresh.question_raised("full.specialist.privacy", "privacy-1", "has a question about storage")
    assert fresh.nodes["full.specialist.privacy"] == "active"
    types = [e.type for e in fresh.log]
    assert types == ["stage_started", "retrieval", "drafting", "question_raised"]
    ret = fresh.log[1]
    assert ret.ref == {"doc": "OAIC PIA", "locator": "p.14"}
    q = fresh.log[3]
    assert q.ref == {"specialist": "privacy", "question_id": "privacy-1"}


def test_heartbeat_updates_timestamp_without_node_change(fresh):
    before = dict(fresh.nodes)
    fresh.heartbeat(now="2026-07-11T00:05:00Z")
    assert fresh.nodes == before
    assert fresh.updated_at == "2026-07-11T00:05:00Z"
    assert fresh.log[-1].type == "heartbeat"


def test_coupling_invariant_every_settled_node_has_matching_last_event(fresh):
    # Drive a realistic threshold slice, then assert §6.3: every active/complete/
    # failed node is narrated by a matching latest event in the log.
    fresh.set_running()
    fresh.heartbeat()
    fresh.start_node("threshold.generalist_a")
    fresh.start_node("threshold.generalist_b")
    fresh.complete_node("threshold.generalist_a")
    fresh.complete_node("threshold.generalist_b")
    fresh.start_node("threshold.reconciler")
    fresh.complete_node("threshold.reconciler")
    fresh.complete_node("threshold.rating_engine")

    coupled = {"active": "stage_started", "complete": "stage_complete", "failed": "error"}
    for node_id, node_state in fresh.nodes.items():
        if node_state in coupled:
            matching = [
                e for e in fresh.log if e.agent == node_id and e.type == coupled[node_state]
            ]
            assert matching, f"{node_id} is {node_state} but has no {coupled[node_state]} event"


def test_to_dict_shape(fresh):
    fresh.start_node("threshold.generalist_a")
    d = fresh.to_dict()
    assert set(d) == {
        "schema_version",
        "run_id",
        "run_code",
        "phase",
        "overall_state",
        "updated_at",
        "nodes",
        "log",
        "log_cursor",
        "questions",
        "failure",
        "expected_ranges",
    }
    assert d["run_code"] == d["run_id"] == "WT-7K3D-Q2"
    assert set(d["nodes"]) == set(EXPECTED_NODE_IDS)  # whole-graph every poll
    assert d["log"][0]["id"] == "evt_000001"


def test_save_is_atomic_and_valid_json(tmp_path, fresh):
    fresh.start_node("threshold.generalist_a")
    fresh.save(tmp_path)
    assert (tmp_path / "status.json").is_file()
    assert not (tmp_path / "status.json.tmp").exists()
    reloaded = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))
    assert reloaded["nodes"]["threshold.generalist_a"] == "active"


def test_expected_ranges_from_budgets():
    ranges = status.load_expected_ranges()
    # threshold_drafting [30,120] + threshold_reconciling [20,90]
    assert ranges["threshold"] == [50, 210]
    # full_drafting [90,300] + architect [20,90] + reviewer [60,240]
    assert ranges["full"] == [170, 630]


# --------------------------------------------------- projection recompute (§6)


def test_rebuild_reproduces_running_graph():
    r = RunState.new("WT-7K3D-Q2", now="2026-07-11T00:00:00Z")
    r.advance_to(Stage.THRESHOLD_DRAFTING, now="2026-07-11T00:01:00Z")
    live = StatusModel.initial(r, now="2026-07-11T00:00:00Z")
    live.set_running()
    live.heartbeat()
    live.start_node("threshold.generalist_a")
    live.start_node("threshold.generalist_b")
    live.complete_node("threshold.generalist_a")
    live.complete_node("threshold.generalist_b")

    rebuilt = status.rebuild(r, live.log)
    assert rebuilt.nodes == live.nodes
    assert rebuilt.overall_state == live.overall_state == "running"
    assert rebuilt.log_cursor == live.log_cursor


def test_rebuild_reproduces_paused_checkpoint():
    r = RunState.new("WT-7K3D-Q2")
    r.advance_to(Stage.FULL_CHECKPOINT, StageStatus.AWAITING_USER)
    live = StatusModel.initial(r)
    for spec in (
        "it_security",
        "privacy",
        "ethics",
        "legal",
        "data_governance",
        "solution_architect",
    ):
        live.start_node(f"full.specialist.{spec}")
        live.complete_node(f"full.specialist.{spec}")
    live.question_raised("full.specialist.privacy", "privacy-1", "has a question")
    live.wait_node("full.checkpoint")

    rebuilt = status.rebuild(r, live.log)
    # waiting_user derives from run.json (stage + awaiting_user), not the log.
    assert rebuilt.nodes["full.checkpoint"] == "waiting_user"
    assert rebuilt.nodes == live.nodes
    assert rebuilt.overall_state == "paused"


def test_rebuild_reproduces_failure():
    r = RunState.new("WT-7K3D-Q2")
    r.advance_to(Stage.FULL_DRAFTING)
    r.fail("full.specialist.privacy", "A step didn't complete.", "RateLimit after 5 retries")
    live = StatusModel.initial(r)
    live.start_node("full.specialist.privacy")
    live.fail_node(
        "full.specialist.privacy", "A step didn't complete.", "RateLimit after 5 retries"
    )

    rebuilt = status.rebuild(r, live.log)
    assert rebuilt.nodes["full.specialist.privacy"] == "failed"
    assert rebuilt.overall_state == "failed"
    assert rebuilt.failure["stage"] == "full.specialist.privacy"
    assert rebuilt.failure["run_code"] == "WT-7K3D-Q2"
    assert rebuilt.failure["technical"] == "RateLimit after 5 retries"


def test_event_to_dict_omits_null_ref():
    e = Event(
        id="evt_000001", ts="2026-07-11T00:00:00Z", agent="pipeline", type="heartbeat", detail=""
    )
    assert "ref" not in e.to_dict()
    e2 = Event(
        id="evt_000002",
        ts="2026-07-11T00:00:00Z",
        agent="x",
        type="retrieval",
        detail="r",
        ref={"doc": "d", "locator": "p.1"},
    )
    assert e2.to_dict()["ref"] == {"doc": "d", "locator": "p.1"}
