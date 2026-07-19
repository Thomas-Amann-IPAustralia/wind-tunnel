"""End-to-end tests for the threshold governance slice (TECH_SPEC §5, §9, §10).

The whole path runs LLM-free through a scripted transport (§15): two generalists →
higher-wins resolution in code → the deterministic engine → routing → the
THRESHOLD_REVIEW pause. The section-3 inputs below are chosen so the ratings are
hand-workable from the real Table 2 — the spirit of Stage 2's exit test for the
engine wiring.
"""

from __future__ import annotations

import json

import pytest

from agents.prompting import RISK_SECTIONS
from agents.threshold import AgentError, run_generalist
from llm import CallBudget, LLMClient, LLMError, ScriptedTransport, resolve_model
from run import FakeCommitter, run_pipeline
from stages.threshold import compute_ratings, compute_routing, resolve_inputs
from statefile import RunState, Stage, StageStatus
from status import StatusModel

# Assessor A and B section-3 inputs (consequence, likelihood). 3.4 and 3.5 diverge.
_A = {
    "3.1": ("Insignificant", "Rare"),
    "3.2": ("Minor", "Unlikely"),
    "3.3": ("Insignificant", "Possible"),
    "3.4": ("Moderate", "Possible"),
    "3.5": ("Major", "Unlikely"),
    "3.6": ("Minor", "Possible"),
    "3.7": ("Insignificant", "Rare"),
    "3.8": ("Minor", "Rare"),
}
_B = {
    "3.1": ("Insignificant", "Rare"),
    "3.2": ("Insignificant", "Rare"),
    "3.3": ("Insignificant", "Rare"),
    "3.4": ("Major", "Possible"),  # diverges up from A's Moderate
    "3.5": ("Moderate", "Unlikely"),  # A's Major consequence wins
    "3.6": ("Minor", "Possible"),
    "3.7": ("Insignificant", "Rare"),
    "3.8": ("Minor", "Rare"),
}
# Hand-worked from risk_matrix.json for the resolved (higher-wins) inputs.
_EXPECTED_RATINGS = {
    "3.1": "Low",  # Insignificant/Rare
    "3.2": "Low",  # Minor/Unlikely
    "3.3": "Low",  # Insignificant/Possible
    "3.4": "High",  # Major/Possible
    "3.5": "Medium",  # Major/Unlikely
    "3.6": "Medium",  # Minor/Possible
    "3.7": "Low",  # Insignificant/Rare
    "3.8": "Low",  # Minor/Rare
}
_EXPECTED_OVERALL = "High"


def _generalist_json(risks: dict[str, tuple[str, str]]) -> str:
    return json.dumps(
        {
            "sections": {"1": "Basic info.", "2": "Purpose.", "4": "Recommendation."},
            "risks": {
                sid: {"consequence": c, "likelihood": lk, "rationale": f"rationale {sid}"}
                for sid, (c, lk) in risks.items()
            },
        }
    )


def _reconciler_json() -> str:
    return json.dumps(
        {
            "sections": {"1": "Reconciled 1.", "2": "Reconciled 2.", "4": "Reconciled 4."},
            "risk_rationale": {sid: f"reconciled rationale {sid}" for sid in RISK_SECTIONS},
            "divergence_notes": {"3.4": "A: Moderate, B: Major → Major.", "3.5": "consequence up."},
        }
    )


def _scripted_client() -> LLMClient:
    transport = ScriptedTransport(
        responses={
            resolve_model("threshold_generalist"): [_generalist_json(_A), _generalist_json(_B)],
            resolve_model("threshold_reconciler"): _reconciler_json(),
        }
    )
    return LLMClient(transport=transport)


def _make_run(run_dir, run_id="WT-TEST-01", stage=Stage.SUBMITTED) -> RunState:
    run = RunState.new(run_id)
    run.advance_to(stage)
    run.save(run_dir)
    StatusModel.initial(run).save(run_dir)
    (run_dir / "brainstorm").mkdir(parents=True, exist_ok=True)
    (run_dir / "brainstorm" / "outline.md").write_text(
        "# Outline\nAn AI triage assistant for citizen enquiries.\n", encoding="utf-8"
    )
    return run


# -- the deterministic core ----------------------------------------------------


def test_resolve_inputs_is_higher_wins():
    client = LLMClient(
        transport=ScriptedTransport(
            responses={
                resolve_model("threshold_generalist"): [_generalist_json(_A), _generalist_json(_B)]
            }
        )
    )
    da = run_generalist(client, "generalist_a", "o")
    db = run_generalist(client, "generalist_b", "o")
    resolved = resolve_inputs(da, db)
    assert resolved["3.4"] == {"consequence": "Major", "likelihood": "Possible"}
    assert resolved["3.5"] == {"consequence": "Major", "likelihood": "Unlikely"}
    assert resolved["3.1"] == {"consequence": "Insignificant", "likelihood": "Rare"}


def test_ratings_match_hand_worked():
    client = LLMClient(
        transport=ScriptedTransport(
            responses={
                resolve_model("threshold_generalist"): [_generalist_json(_A), _generalist_json(_B)]
            }
        )
    )
    da = run_generalist(client, "generalist_a", "o")
    db = run_generalist(client, "generalist_b", "o")
    ratings = compute_ratings(resolve_inputs(da, db))
    got = {sid: ratings["sections"][sid]["rating"] for sid in RISK_SECTIONS}
    assert got == _EXPECTED_RATINGS
    assert ratings["overall_inherent"] == _EXPECTED_OVERALL


def test_routing_from_overall_high():
    ratings = {
        "sections": {sid: {"rating": r} for sid, r in _EXPECTED_RATINGS.items()},
        "overall_inherent": _EXPECTED_OVERALL,
    }
    routing = compute_routing(ratings)
    assert routing["full_assessment"] == "required"
    assert routing["may_conclude"] is False
    assert routing["high_risk_governance_review_required"] is True
    assert routing["medium_or_high_sections"] == ["3.4", "3.5", "3.6"]


def test_routing_all_low_may_conclude():
    ratings = {
        "sections": {sid: {"rating": "Low"} for sid in RISK_SECTIONS},
        "overall_inherent": "Low",
    }
    routing = compute_routing(ratings)
    assert routing["full_assessment"] == "optional"
    assert routing["may_conclude"] is True
    assert routing["high_risk_governance_review_required"] is False
    assert routing["medium_or_high_sections"] == []


# -- agent output discipline (§9.4, §10) ---------------------------------------


def test_agent_rejects_asserted_rating():
    bad = json.dumps(
        {
            "sections": {"1": "a", "2": "b", "4": "c"},
            "risks": {
                sid: {
                    "consequence": "Minor",
                    "likelihood": "Rare",
                    "rationale": "x",
                    "rating": "Low",
                }
                for sid in RISK_SECTIONS
            },
        }
    )
    client = LLMClient(
        transport=ScriptedTransport(responses={resolve_model("threshold_generalist"): bad})
    )
    with pytest.raises(AgentError, match="asserts a rating"):
        run_generalist(client, "generalist_a", "o")


def test_agent_rejects_off_vocabulary_tier():
    bad = json.dumps(
        {
            "sections": {"1": "a", "2": "b", "4": "c"},
            "risks": {
                sid: {"consequence": "Catastrophic", "likelihood": "Rare", "rationale": "x"}
                for sid in RISK_SECTIONS
            },
        }
    )
    client = LLMClient(
        transport=ScriptedTransport(responses={resolve_model("threshold_generalist"): bad})
    )
    with pytest.raises(AgentError, match="not a valid tier"):
        run_generalist(client, "generalist_a", "o")


# -- the driver end-to-end -----------------------------------------------------


def test_pipeline_runs_threshold_to_review_pause(tmp_path):
    run_dir = tmp_path / "WT-TEST-01"
    run_dir.mkdir()
    _make_run(run_dir)

    result = run_pipeline(run_dir, llm=_scripted_client(), committer=FakeCommitter())

    assert result.ok
    assert result.final_stage is Stage.THRESHOLD_REVIEW
    assert result.stage_status is StageStatus.AWAITING_USER

    # run.json paused at review; status.json paused; rating engine complete.
    run = RunState.load(run_dir)
    assert run.stage is Stage.THRESHOLD_REVIEW
    assert run.stage_status is StageStatus.AWAITING_USER
    status = json.loads((run_dir / "status.json").read_text())
    assert status["overall_state"] == "paused"
    assert status["nodes"]["threshold.rating_engine"] == "complete"
    assert status["nodes"]["threshold.reconciler"] == "complete"

    # artefacts written with engine-computed ratings.
    ratings = json.loads((run_dir / "threshold" / "ratings.json").read_text())
    got = {sid: ratings["sections"][sid]["rating"] for sid in RISK_SECTIONS}
    assert got == _EXPECTED_RATINGS
    assert ratings["overall_inherent"] == _EXPECTED_OVERALL

    routing = json.loads((run_dir / "threshold" / "routing.json").read_text())
    assert routing["full_assessment"] == "required"

    divergence = json.loads((run_dir / "threshold" / "divergence.json").read_text())
    assert divergence["sections"]["3.4"]["diverged"] is True
    assert divergence["sections"]["3.1"]["diverged"] is False

    md = (run_dir / "threshold" / "threshold_assessment.md").read_text()
    assert "Overall inherent risk rating (highest-wins): High" in md
    assert "full assessment is **required**" in md.lower()


def test_pipeline_is_idempotent_on_resume(tmp_path):
    run_dir = tmp_path / "WT-TEST-02"
    run_dir.mkdir()
    _make_run(run_dir, run_id="WT-TEST-02")
    run_pipeline(run_dir, llm=_scripted_client(), committer=FakeCommitter())

    # Simulate a re-dispatch that rewinds the stage: the committed checkpoint output
    # files still exist, so re-running must NOT call the model again (§5.3).
    run = RunState.load(run_dir)
    run.advance_to(Stage.THRESHOLD_DRAFTING)
    run.save(run_dir)

    class _Boom:
        def generate(self, **_):
            raise AssertionError("model must not be called on an idempotent resume")

    result = run_pipeline(run_dir, llm=LLMClient(transport=_Boom()), committer=FakeCommitter())
    assert result.ok
    assert result.final_stage is Stage.THRESHOLD_REVIEW
    assert result.stage_status is StageStatus.AWAITING_USER


# -- threshold revision (§7, brief §7) -----------------------------------------


def _drive_to_review(run_dir, transport) -> None:
    _make_run(run_dir, run_id=run_dir.name)
    run_pipeline(run_dir, llm=LLMClient(transport=transport), committer=FakeCommitter())


def _stage_threshold_revision(run_dir, instructions: str) -> int:
    """Mimic ``POST /revise {threshold}``: consume a cap, stage the request, rewind to
    THRESHOLD_RECONCILING. Returns the revision number."""
    run = RunState.load(run_dir)
    n = run.record_revision("threshold")
    run.advance_to(Stage.THRESHOLD_RECONCILING)
    run.save(run_dir)
    req_dir = run_dir / "threshold" / "revisions" / f"rev_{n}"
    req_dir.mkdir(parents=True)
    (req_dir / "request.json").write_text(
        json.dumps({"instructions": instructions}), encoding="utf-8"
    )
    return n


def test_threshold_revision_reruns_reconciler_with_instructions(tmp_path):
    run_dir = tmp_path / "WT-TEST-RV"
    run_dir.mkdir()
    transport = ScriptedTransport(
        responses={
            resolve_model("threshold_generalist"): [_generalist_json(_A), _generalist_json(_B)],
            resolve_model("threshold_reconciler"): _reconciler_json(),
        }
    )
    _drive_to_review(run_dir, transport)

    n = _stage_threshold_revision(run_dir, "Emphasise the accessibility mitigations in section 4.")
    result = run_pipeline(
        run_dir,
        llm=LLMClient(transport=transport),
        committer=FakeCommitter(),
        resume_from="THRESHOLD_RECONCILING",
    )

    # Back at the review pause, one revision in.
    assert result.ok
    assert result.final_stage is Stage.THRESHOLD_REVIEW
    assert result.stage_status is StageStatus.AWAITING_USER
    assert n == 1

    # The reconciler was re-run and the user's instructions reached its prompt as untrusted
    # data — but the generalists were NOT re-called (drafting is checkpoint-skipped, §5.3).
    reconciler_model = resolve_model("threshold_reconciler")
    reconciler_prompts = [s["user"] for s in transport.seen if s["model"] == reconciler_model]
    assert len(reconciler_prompts) == 2  # once on the initial pass, once on the revision
    assert "accessibility mitigations" in reconciler_prompts[-1]

    # The per-revision checkpoint marker was written (idempotency key for the re-dispatch).
    marker = json.loads(
        (run_dir / "threshold" / "revisions" / "rev_1" / "reconciled.json").read_text()
    )
    assert marker["revision"] == 1

    # The ratings are UNCHANGED — the generalist drafts stand, so the resolved tiers and the
    # engine's ratings are identical; a revision steers narrative, never a rating (§10).
    ratings = json.loads((run_dir / "threshold" / "ratings.json").read_text())
    got = {sid: ratings["sections"][sid]["rating"] for sid in RISK_SECTIONS}
    assert got == _EXPECTED_RATINGS
    assert ratings["overall_inherent"] == _EXPECTED_OVERALL


def test_threshold_revision_is_idempotent_on_resume(tmp_path):
    run_dir = tmp_path / "WT-TEST-RW"
    run_dir.mkdir()
    transport = ScriptedTransport(
        responses={
            resolve_model("threshold_generalist"): [_generalist_json(_A), _generalist_json(_B)],
            resolve_model("threshold_reconciler"): _reconciler_json(),
        }
    )
    _drive_to_review(run_dir, transport)
    _stage_threshold_revision(run_dir, "Tighten section 2.")
    run_pipeline(
        run_dir,
        llm=LLMClient(transport=transport),
        committer=FakeCommitter(),
        resume_from="THRESHOLD_RECONCILING",
    )

    # A re-dispatch of the same revision must NOT re-run the reconciler: rev_1/reconciled.json
    # exists, so the per-revision checkpoint short-circuits it (§5.3).
    run = RunState.load(run_dir)
    run.advance_to(Stage.THRESHOLD_RECONCILING)
    run.save(run_dir)

    class _Boom:
        def generate(self, **_):
            raise AssertionError("model must not be called on an idempotent revision resume")

    result = run_pipeline(run_dir, llm=LLMClient(transport=_Boom()), committer=FakeCommitter())
    assert result.ok
    assert result.final_stage is Stage.THRESHOLD_REVIEW
    assert result.stage_status is StageStatus.AWAITING_USER


def test_pipeline_fails_calmly_on_bad_model_json(tmp_path):
    run_dir = tmp_path / "WT-TEST-03"
    run_dir.mkdir()
    _make_run(run_dir, run_id="WT-TEST-03")

    client = LLMClient(
        transport=ScriptedTransport(
            responses={resolve_model("threshold_generalist"): "not json at all"}
        )
    )
    result = run_pipeline(run_dir, llm=client, committer=FakeCommitter())

    assert result.ok is False
    run = RunState.load(run_dir)
    assert run.stage is Stage.THRESHOLD_DRAFTING  # stays at the failing stage (§5.6)
    assert run.stage_status is StageStatus.FAILED
    assert run.last_error and "run code" in run.last_error["message"].lower()
    status = json.loads((run_dir / "status.json").read_text())
    assert status["overall_state"] == "failed"
    assert status["failure"]["run_code"] == "WT-TEST-03"


# -- llm seam ------------------------------------------------------------------


def test_llm_parses_fenced_json():
    # A model that wraps its JSON in a ```json fence is still parsed loudly-or-cleanly.
    from llm import _strip_code_fence

    assert json.loads(_strip_code_fence('```json\n{"ok": true}\n```')) == {"ok": True}


def test_call_budget_trips():
    budget = CallBudget(max_calls=1)
    budget.charge()
    with pytest.raises(LLMError, match="budget exhausted"):
        budget.charge()


# -- failure recovery: the same-stage resume path (§5.6, §5.3) -----------------


def test_failed_run_resumes_from_its_failed_stage(tmp_path):
    """The zombie-run bug: a failed run's `stage` still points at the failing
    stage, so its retry dispatch is same-stage — that dispatch must clear the
    FAILED marker and actually re-run the stage (all three live failed runs
    needed exactly this). The retry also proves per-generalist idempotence: the
    committed draft of the assessor that succeeded is not re-drafted when only
    the other one failed. (The generalists draft concurrently, §5.4, so which of
    the two fails is scheduling-dependent — the handler counts under a lock and
    the assertions are assignment-agnostic.)"""
    run_dir = tmp_path / "WT-TEST-FR"
    run_dir.mkdir()
    _make_run(run_dir, run_id="WT-TEST-FR")

    import threading

    calls = {"n": 0}
    gate = threading.Lock()

    def failing_handler(*, model, system, user, response_json):
        with gate:
            calls["n"] += 1
            first = calls["n"] == 1
        if first:
            return _generalist_json(_A)
        raise LLMError("boom: simulated malformed-JSON exhaustion for one assessor")

    first = run_pipeline(
        run_dir,
        llm=LLMClient(transport=ScriptedTransport(handler=failing_handler)),
        committer=FakeCommitter(),
    )
    assert first.ok is False
    run = RunState.load(run_dir)
    assert run.stage is Stage.THRESHOLD_DRAFTING
    assert run.stage_status is StageStatus.FAILED
    assert "boom" in run.last_error["technical"]
    status_doc = json.loads((run_dir / "status.json").read_text())
    assert status_doc["overall_state"] == "failed"
    assert status_doc["failure"] is not None

    # The retry is a same-stage dispatch (the backend's /redispatch maps a failed
    # THRESHOLD_DRAFTING to itself). Only ONE draft is scripted — exactly the
    # missing assessor's; if the committed one were re-drafted the queue would
    # exhaust and the test would fail.
    resume_client = LLMClient(
        transport=ScriptedTransport(
            responses={
                resolve_model("threshold_generalist"): [_generalist_json(_B)],
                resolve_model("threshold_reconciler"): _reconciler_json(),
            }
        )
    )
    second = run_pipeline(
        run_dir,
        llm=resume_client,
        committer=FakeCommitter(),
        resume_from="THRESHOLD_DRAFTING",
    )
    assert second.ok
    assert second.final_stage is Stage.THRESHOLD_REVIEW
    assert second.stage_status is StageStatus.AWAITING_USER

    run = RunState.load(run_dir)
    assert run.stage_status is StageStatus.AWAITING_USER
    assert run.last_error is None
    status_doc = json.loads((run_dir / "status.json").read_text())
    assert status_doc["overall_state"] == "paused"
    assert status_doc["failure"] is None
    assert status_doc["nodes"]["threshold.generalist_a"] == "complete"
    assert status_doc["nodes"]["threshold.generalist_b"] == "complete"
    assert status_doc["nodes"]["threshold.rating_engine"] == "complete"


# -- mid-stage status pulses (§6.3 cadence) ------------------------------------


class _SnapshotCommitter:
    """Records, at every commit, the message and the node map committed in
    status.json — the observer a polling SPA effectively is."""

    def __init__(self):
        self.snapshots = []

    def commit(self, run_dir, message):
        from pathlib import Path

        status_path = Path(run_dir) / "status.json"
        nodes = None
        if status_path.is_file():
            nodes = json.loads(status_path.read_text())["nodes"]
        self.snapshots.append((message, nodes))
        return f"snap{len(self.snapshots):04d}"


def test_status_pulses_publish_mid_stage_progress(tmp_path):
    """Node transitions are committed as they happen, not only at stage
    checkpoints — otherwise the whole first stage reads as a hung,
    not-yet-started run (and invites a needless restart). The generalists draft
    concurrently (§5.4), so the guaranteed mid-stage observation is the drafted
    pair landing before the reconciler starts; with instant scripted calls the
    fleeting both-active state may fall between pulse drains (a real run's
    30s+ calls make it visible — the design §7.2 "two nodes pulsing")."""
    run_dir = tmp_path / "WT-TEST-PU"
    run_dir.mkdir()
    _make_run(run_dir, run_id="WT-TEST-PU")
    committer = _SnapshotCommitter()

    result = run_pipeline(run_dir, llm=_scripted_client(), committer=committer)
    assert result.ok

    pulses = [nodes for message, nodes in committer.snapshots if "status pulse" in message]
    assert pulses, "expected mid-stage status pulses"
    assert any(
        nodes["threshold.generalist_a"] == "complete"
        and nodes["threshold.generalist_b"] == "complete"
        and nodes["threshold.reconciler"] == "pending"
        for nodes in pulses
    ), "a poll must see the drafted pair before the reconciler starts"
    assert any(nodes["threshold.reconciler"] == "active" for nodes in pulses)


def test_threshold_drafting_fans_out_both_generalists(tmp_path):
    """The two assessors draft simultaneously (§5.4; design §7.2 "Generalist A and
    Generalist B go active at the same time"): a 2-party barrier inside the
    transport only releases when both are mid-call, so a serial implementation
    times it out rather than passing. The two are symmetric by construction —
    identical prompts — so which response lands in which slot is
    scheduling-dependent: both scripted drafts must land, one per slot, and the
    engine's ratings are identical either way (higher-wins is commutative)."""
    import threading

    run_dir = tmp_path / "WT-TEST-2GEN"
    run_dir.mkdir()
    _make_run(run_dir, run_id="WT-TEST-2GEN")

    barrier = threading.Barrier(2)
    queue = [_generalist_json(_A), _generalist_json(_B)]
    qlock = threading.Lock()

    def handler(*, model, system, user, response_json):
        if model == resolve_model("threshold_reconciler"):
            return _reconciler_json()
        barrier.wait(timeout=30)  # broken barrier (= serial execution) fails loudly
        with qlock:
            return queue.pop(0)

    result = run_pipeline(
        run_dir,
        llm=LLMClient(transport=ScriptedTransport(handler=handler)),
        committer=FakeCommitter(),
    )

    assert result.ok
    assert result.final_stage is Stage.THRESHOLD_REVIEW
    a = json.loads((run_dir / "threshold" / "generalist_a.json").read_text())
    b = json.loads((run_dir / "threshold" / "generalist_b.json").read_text())
    assert a["label"] == "generalist_a" and b["label"] == "generalist_b"
    expected_risk_maps = {
        json.dumps(
            {
                sid: {"consequence": c, "likelihood": lk, "rationale": f"rationale {sid}"}
                for sid, (c, lk) in risks.items()
            },
            sort_keys=True,
        )
        for risks in (_A, _B)
    }
    got_risk_maps = {json.dumps(d["risks"], sort_keys=True) for d in (a, b)}
    assert got_risk_maps == expected_risk_maps  # both drafts landed, one per assessor
    ratings = json.loads((run_dir / "threshold" / "ratings.json").read_text())
    got = {sid: ratings["sections"][sid]["rating"] for sid in RISK_SECTIONS}
    assert got == _EXPECTED_RATINGS  # assignment-independent
    assert ratings["overall_inherent"] == _EXPECTED_OVERALL
