"""status.json — the derived UI projection (TECH_SPEC §6).

``status.json`` is what the SPA polls to animate the pipeline and detect the two
user pauses. It is a *projection*, never the source of truth: it is always safe to
recompute from ``run.json`` plus the committed, append-only event log (§6), and the
pipeline never resumes from it (CLAUDE.md §3). Three constraints govern everything
here and are enforced structurally:

  1. **One poll fully determines visible state.** ``nodes`` is a whole-graph map on
     every write — every node id present every time — so a frontend that misses
     polls still renders correctly (§6.2).
  2. **The event log is append-only with stable, monotonic ids.** ``evt_000412``
     is never reused or reordered; the frontend keeps the highest id it has seen
     and animates only newer ones (§6.3).
  3. **No event may exist only in the graph.** Every node-state change to
     ``active``/``complete``/``failed`` is narrated by the matching
     ``stage_started``/``stage_complete``/``error`` log line in the same write —
     the log is the accessibility and honesty backbone (§6.3). This module makes
     that impossible to violate: those three node states can *only* be set through
     methods that append the coupled event.

The node topology (§6.2) is fixed and its ids are shared verbatim with the design
animation. Specialist nodes and their owned sections derive from
``instrument/sections.json`` — the one owner of the specialist↔section map — so
the graph never re-states that fact (CLAUDE.md §3, "one owner per fact").
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from statefile import RunState, Stage, StageStatus, utc_now_iso

SCHEMA_VERSION = 1
STATUS_JSON = "status.json"


class StatusError(ValueError):
    """Raised on an unknown node id, node state, event type, or overall state.
    A loud failure — a typo in a node id must not silently drop off the graph."""


# -- node states and the controlled event vocabulary (§6.2, §6.3) --------------

# Node state enum (§6.2). The design's visual "waiting-on-you" maps to waiting_user.
NODE_STATES: frozenset[str] = frozenset({"pending", "active", "waiting_user", "complete", "failed"})

# overall_state enum (§6.1).
OVERALL_STATES: frozenset[str] = frozenset({"running", "paused", "failed", "complete"})

# Controlled event `type` vocabulary (§6.3) — adopted verbatim from the design set.
EVENT_TYPES: frozenset[str] = frozenset(
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

# The three node-state changes that MUST carry a matching log line (§6.3), and the
# event type that narrates each. Enforced by construction below.
_COUPLED_EVENT: dict[str, str] = {
    "active": "stage_started",
    "complete": "stage_complete",
    "failed": "error",
}


# -- fixed node topology (§6.2), specialists derived from sections.json ---------


@dataclass(frozen=True)
class NodeSpec:
    node_id: str
    friendly: str
    model_role: str | None  # None ⇒ deterministic / pause (no LLM)
    owns: str  # human label of owned DTA sections (§6.2 "Owns" column)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "instrument" / "sections.json").is_file():
            return parent
    raise StatusError(
        f"Could not locate the repo root (with instrument/sections.json) above {here}."
    )


@lru_cache(maxsize=1)
def _sections() -> dict:
    with (_repo_root() / "instrument" / "sections.json").open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def _node_specs() -> tuple[NodeSpec, ...]:
    """Build the fixed §6.2 topology once. Threshold + non-specialist nodes are
    named here; the six specialist nodes derive their friendly name and owned
    sections from sections.json (the ownership contract)."""
    s = _sections()
    specialists: list[str] = s["specialists"]
    friendly: dict[str, str] = s["specialist_friendly"]
    ownership: dict[str, str] = s["full_assessment_ownership"]

    # Invert ownership → owned sections per specialist (drafting owners only).
    owned: dict[str, list[str]] = {spec: [] for spec in specialists}
    for section, owner in ownership.items():
        if owner in owned:
            owned[owner].append(section)
    for spec in owned:
        owned[spec].sort(key=_section_sort_key)

    nodes: list[NodeSpec] = [
        NodeSpec("threshold.generalist_a", "Assessor A", "threshold_generalist", "1–4 (draft)"),
        NodeSpec("threshold.generalist_b", "Assessor B", "threshold_generalist", "1–4 (draft)"),
        NodeSpec("threshold.reconciler", "Reconciler", "threshold_reconciler", "1–4 (final)"),
        NodeSpec("threshold.rating_engine", "Rating engine", None, "3.1–3.9 (computed)"),
    ]
    for spec in specialists:
        nodes.append(
            NodeSpec(
                node_id=f"full.specialist.{spec}",
                friendly=friendly[spec],
                model_role="specialist",
                owns=", ".join(owned[spec]),
            )
        )
    nodes += [
        NodeSpec("full.checkpoint", "Question checkpoint", None, "—"),
        NodeSpec(
            "full.architect",
            "Solution Architect (appendix)",
            "architect",
            "Implementation Plan appendix",
        ),
        NodeSpec(
            "full.reviewer",
            "Adjudicating reviewer",
            "reviewer",
            "coverage + coherence; residual 12.3/12.4",
        ),
        NodeSpec("full.assembly", "Assembly", None, "notebook + HTML"),
    ]
    return tuple(nodes)


def _section_sort_key(section: str) -> tuple[int, int]:
    major, _, minor = section.partition(".")
    return (int(major), int(minor) if minor else 0)


def node_specs() -> tuple[NodeSpec, ...]:
    """The fixed node topology in graph order (§6.2)."""
    return _node_specs()


def node_ids() -> tuple[str, ...]:
    """Every node id, in graph order — the complete key set of ``nodes``."""
    return tuple(n.node_id for n in _node_specs())


def friendly_name(node_id: str) -> str:
    """The design-facing name for a node id (§6.2). Raises on unknown id."""
    for n in _node_specs():
        if n.node_id == node_id:
            return n.friendly
    raise StatusError(f"Unknown node id: {node_id!r}.")


# Which node goes waiting_user at each user pause (§5.1, §6.2). THRESHOLD_REVIEW is
# absent: it pauses via overall_state (rating_engine → complete), not a node state.
_PAUSE_NODE_OF_STAGE: dict[Stage, str] = {Stage.FULL_CHECKPOINT: "full.checkpoint"}


# -- events (§6.3) --------------------------------------------------------------


@dataclass
class Event:
    """One append-only log entry (§6.3). ``id`` is stable, monotonic, zero-padded."""

    id: str
    ts: str
    agent: str  # a node_id (or its friendly name)
    type: str
    detail: str
    ref: dict | None = None

    def to_dict(self) -> dict:
        out = {
            "id": self.id,
            "ts": self.ts,
            "agent": self.agent,
            "type": self.type,
            "detail": self.detail,
        }
        if self.ref is not None:
            out["ref"] = self.ref
        return out


def _event_id(ordinal: int) -> str:
    return f"evt_{ordinal:06d}"


# -- the status model -----------------------------------------------------------


@dataclass
class StatusModel:
    """The status.json document (§6.1). Node/event coupling (§6.3) is enforced:
    ``active``/``complete``/``failed`` are only reachable via methods that append
    the matching event, so the graph can never silently diverge from the log."""

    run_id: str
    phase: str
    overall_state: str
    nodes: dict[str, str]
    log: list[Event] = field(default_factory=list)
    questions: dict | None = None
    failure: dict | None = None
    expected_ranges: dict | None = None
    updated_at: str = ""
    schema_version: int = SCHEMA_VERSION

    # -- construction -----------------------------------------------------------

    @classmethod
    def initial(
        cls,
        run: RunState,
        *,
        expected_ranges: dict | None = None,
        now: str | None = None,
    ) -> StatusModel:
        """A fresh projection for ``run``: every node pending, empty log, overall
        state derived from the run's stage/status."""
        ts = now or utc_now_iso()
        return cls(
            run_id=run.run_id,
            phase=str(run.phase),
            overall_state=_overall_from_run(run),
            nodes={nid: "pending" for nid in node_ids()},
            expected_ranges=expected_ranges
            if expected_ranges is not None
            else load_expected_ranges(),
            updated_at=ts,
        )

    # -- node/event coupling: active | complete | failed (§6.3) -----------------

    def start_node(
        self, node_id: str, detail: str | None = None, *, now: str | None = None
    ) -> Event:
        """Set ``node_id`` active and emit the coupled ``stage_started`` (§6.3)."""
        return self._set_and_narrate(node_id, "active", detail, now)

    def complete_node(
        self, node_id: str, detail: str | None = None, *, now: str | None = None
    ) -> Event:
        """Set ``node_id`` complete and emit the coupled ``stage_complete`` (§6.3)."""
        return self._set_and_narrate(node_id, "complete", detail, now)

    def fail_node(
        self,
        node_id: str,
        message: str,
        technical: str,
        *,
        run_code: str | None = None,
        now: str | None = None,
    ) -> Event:
        """Set ``node_id`` failed, emit the coupled ``error`` line, flip
        ``overall_state`` to failed, and populate the failure payload (§6.5).

        ``message`` is the plain, calm line shown in the log; ``technical`` sits in
        the failure payload behind "Show technical detail" (design §7.2.4)."""
        evt = self._set_and_narrate(node_id, "failed", message, now)
        self.overall_state = "failed"
        self.failure = {
            "stage": node_id,
            "message": message,
            "run_code": run_code or self.run_id,
            "technical": technical,
        }
        return evt

    def wait_node(self, node_id: str, *, now: str | None = None) -> None:
        """Set ``node_id`` waiting_user and flip ``overall_state`` to paused (§5.1).

        No coupled event: a pause is narrated by the ``question_raised`` lines the
        caller already emitted (checkpoint), so this is not a graph-only change."""
        self._require_node(node_id)
        self.nodes[node_id] = "waiting_user"
        self.overall_state = "paused"
        self._touch(now)

    # -- ephemeral / sub-activity / liveness events (no node-state change) -------

    def heartbeat(self, agent: str = "pipeline", *, now: str | None = None) -> Event:
        """Liveness (§6.3, §5.7). Emitted ≥ every ~20 s so the staleness counter
        always has a reference. Does not change any node state."""
        return self._append(agent, "heartbeat", "", None, now)

    def retrieval(
        self,
        node_id: str,
        detail: str,
        *,
        doc: str | None = None,
        locator: str | None = None,
        now: str | None = None,
    ) -> Event:
        """An agent read a chunk (§6.3): ephemeral label on the node."""
        self._require_node(node_id)
        ref = {"doc": doc, "locator": locator} if doc or locator else None
        return self._append(node_id, "retrieval", detail, ref, now)

    def drafting(
        self,
        node_id: str,
        detail: str,
        *,
        section: str | None = None,
        now: str | None = None,
    ) -> Event:
        """Node sub-activity, e.g. "drafting §7.3" (§6.3)."""
        self._require_node(node_id)
        ref = {"section": section} if section else None
        return self._append(node_id, "drafting", detail, ref, now)

    def question_raised(
        self,
        node_id: str,
        question_id: str,
        detail: str,
        *,
        now: str | None = None,
    ) -> Event:
        """A specialist raised a checkpoint question (§6.3); feeds the pause count."""
        self._require_node(node_id)
        specialist = node_id.rsplit(".", 1)[-1]
        ref = {"specialist": specialist, "question_id": question_id}
        return self._append(node_id, "question_raised", detail, ref, now)

    def revision(
        self,
        agent: str,
        detail: str,
        *,
        cycle: int | None = None,
        target: str | None = None,
        now: str | None = None,
    ) -> Event:
        """A reviewer-directed amend or a specialist revising after answers (§6.3)."""
        ref = {}
        if cycle is not None:
            ref["cycle"] = cycle
        if target is not None:
            ref["target"] = target
        return self._append(agent, "revision", detail, ref or None, now)

    def review_finding(self, agent: str, detail: str, *, now: str | None = None) -> Event:
        """A reviewer coverage/coherence note (§6.3): a log line, no node change."""
        return self._append(agent, "review_finding", detail, None, now)

    # -- overall state + pause/failure payloads ---------------------------------

    def set_overall(self, state: str, *, now: str | None = None) -> None:
        """Set ``overall_state`` (running | paused | failed | complete, §6.1)."""
        if state not in OVERALL_STATES:
            raise StatusError(
                f"Unknown overall_state: {state!r}. Expected one of {sorted(OVERALL_STATES)}."
            )
        self.overall_state = state
        self._touch(now)

    def set_running(self, *, now: str | None = None) -> None:
        """The "tunnel is running" signal — pair with the first heartbeat (§5.7)."""
        self.set_overall("running", now=now)

    def set_complete(self, *, now: str | None = None) -> None:
        """Terminal success (COMPLETE / CONCLUDED, §5.1)."""
        self.set_overall("complete", now=now)

    def set_questions(self, questions: dict, *, now: str | None = None) -> None:
        """Attach the batched-questions payload shown while paused (§6.4)."""
        self.questions = questions
        self._touch(now)

    def clear_questions(self, *, now: str | None = None) -> None:
        """Drop the questions payload once answers are submitted (§6.4)."""
        self.questions = None
        self._touch(now)

    # -- internals --------------------------------------------------------------

    def _set_and_narrate(
        self, node_id: str, state: str, detail: str | None, now: str | None
    ) -> Event:
        self._require_node(node_id)
        event_type = _COUPLED_EVENT[state]
        self.nodes[node_id] = state
        default_detail = {
            "active": f"{friendly_name(node_id)} started",
            "complete": f"{friendly_name(node_id)} complete",
            "failed": f"{friendly_name(node_id)} failed",
        }[state]
        return self._append(node_id, event_type, detail or default_detail, None, now)

    def _append(
        self, agent: str, event_type: str, detail: str, ref: dict | None, now: str | None
    ) -> Event:
        if event_type not in EVENT_TYPES:
            raise StatusError(
                f"Unknown event type: {event_type!r}. Expected one of {sorted(EVENT_TYPES)}."
            )
        ts = now or utc_now_iso()
        evt = Event(
            id=_event_id(self._next_ordinal()),
            ts=ts,
            agent=agent,
            type=event_type,
            detail=detail,
            ref=ref,
        )
        self.log.append(evt)
        self.updated_at = ts
        return evt

    def _next_ordinal(self) -> int:
        return len(self.log) + 1

    def _require_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            raise StatusError(f"Unknown node id: {node_id!r}. Expected one of {list(node_ids())}.")

    def _touch(self, now: str | None) -> None:
        self.updated_at = now or utc_now_iso()

    @property
    def log_cursor(self) -> int:
        """Highest event ordinal present, for frontend dedupe (§6.1). 0 if empty."""
        return len(self.log)

    # -- serialisation ----------------------------------------------------------

    def to_dict(self) -> dict:
        """The status.json document in the §6.1 shape."""
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "run_code": self.run_id,  # the run code *is* the id (§3)
            "phase": self.phase,
            "overall_state": self.overall_state,
            "updated_at": self.updated_at,
            "nodes": dict(self.nodes),
            "log": [e.to_dict() for e in self.log],
            "log_cursor": self.log_cursor,
            "questions": self.questions,
            "failure": self.failure,
            "expected_ranges": self.expected_ranges,
        }

    def save(self, run_dir: str | os.PathLike) -> Path:
        """Atomically write ``<run_dir>/status.json`` (temp + os.replace)."""
        run_path = Path(run_dir)
        run_path.mkdir(parents=True, exist_ok=True)
        target = run_path / STATUS_JSON
        tmp = target.with_name(target.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, target)
        return target


# -- recompute-from-log: the projection guarantee (§6) -------------------------


def rebuild(
    run: RunState,
    events: list[Event],
    *,
    expected_ranges: dict | None = None,
    now: str | None = None,
) -> StatusModel:
    """Reconstruct the whole projection from ``run.json`` + the committed event log.

    This is the concrete meaning of "status.json is always safe to recompute"
    (§6): node states follow deterministically from the append-only log
    (stage_started→active, stage_complete→complete, error→failed), the pause node
    follows from ``run.json`` (stage + awaiting_user), and ``overall_state`` follows
    from the run stage/status. A status file rebuilt this way must equal the one
    the pipeline wrote incrementally — asserted in tests."""
    model = StatusModel(
        run_id=run.run_id,
        phase=str(run.phase),
        overall_state=_overall_from_run(run),
        nodes={nid: "pending" for nid in node_ids()},
        expected_ranges=expected_ranges if expected_ranges is not None else load_expected_ranges(),
        updated_at=run.updated_at,
    )
    last_error_event: Event | None = None
    for evt in events:
        model.log.append(evt)
        if evt.type == "stage_started":
            model.nodes[evt.agent] = "active"
        elif evt.type == "stage_complete":
            model.nodes[evt.agent] = "complete"
        elif evt.type == "error":
            model.nodes[evt.agent] = "failed"
            last_error_event = evt
        if evt.ts:
            model.updated_at = evt.ts

    # Pause node (waiting_user) derives from run.json, not the log (§5.1, §6.2).
    if run.stage_status is StageStatus.AWAITING_USER:
        pause_node = _PAUSE_NODE_OF_STAGE.get(run.stage)
        if pause_node is not None:
            model.nodes[pause_node] = "waiting_user"

    if run.stage_status is StageStatus.FAILED and last_error_event is not None:
        err = run.last_error or {}
        model.failure = {
            "stage": err.get("stage", last_error_event.agent),
            "message": err.get("message", last_error_event.detail),
            "run_code": run.run_id,
            "technical": err.get("technical", ""),
        }
    if now is not None:
        model.updated_at = now
    return model


def _overall_from_run(run: RunState) -> str:
    """overall_state (§6.1) implied by run.json's stage + stage_status."""
    if run.stage_status is StageStatus.FAILED:
        return "failed"
    if run.stage in (Stage.COMPLETE, Stage.CONCLUDED):
        return "complete"
    if run.stage_status is StageStatus.AWAITING_USER:
        return "paused"
    return "running"


# -- expected_ranges from config/budgets.yml (§6.1, §13) -----------------------


@lru_cache(maxsize=1)
def load_expected_ranges() -> dict:
    """Per-phase ``[low, high]`` second ranges, aggregated from config/budgets.yml.

    threshold = threshold_drafting + threshold_reconciling; full = full_drafting +
    architect + reviewer (§13). Computed from the one owner (budgets.yml), not
    hardcoded, so tuning the budgets flows straight into the animation's timing
    hints (§6.1)."""
    import yaml  # local import: keeps status.py light for pure-projection callers

    with (_repo_root() / "config" / "budgets.yml").open(encoding="utf-8") as fh:
        budgets = yaml.safe_load(fh)
    stages = budgets.get("stages", {})

    def _sum(*names: str) -> list[int]:
        low = high = 0
        for name in names:
            rng = stages.get(name, {}).get("expected_range_seconds", [0, 0])
            low += rng[0]
            high += rng[1]
        return [low, high]

    return {
        "threshold": _sum("threshold_drafting", "threshold_reconciling"),
        "full": _sum("full_drafting", "architect", "reviewer"),
    }
