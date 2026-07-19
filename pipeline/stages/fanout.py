"""The bounded agent fan-out (TECH_SPEC §5.4), shared by the stages that run
several agents concurrently within one job: THRESHOLD_DRAFTING (two generalists)
and FULL_DRAFTING / FULL_REVISING / the amendment paths (specialists).

The threading discipline is structural and identical everywhere:

  * **Workers compute and narrate only** — each opens its own KB connection if it
    needs one, charges the shared (lock-guarded) call budget, and narrates on the
    shared thread-safe :class:`status.StatusModel`. A worker never writes a file
    and never commits.
  * **The coordinating thread owns every write and every commit** (§14
    single-writer). Each task's ``finish`` runs there as its worker completes, so
    a finished draft is written and pulse-committed without waiting for the
    slowest agent — the per-agent §5.3 resume granularity survives the fan-out.
  * While workers run, ``status.pulse`` is swapped for a :class:`DeferredPulse`:
    worker narration only *requests* a publish; the coordinator drains the
    request between waits and publishes through the driver's real pulse.

The width comes from ``config/budgets.yml`` ``specialist_concurrency`` (§13) —
named for the binding case, the six specialists; the generalist pair (2) sits
under it either way. One knob, one owner (CLAUDE.md §6)."""

from __future__ import annotations

import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor
from concurrent.futures import wait as futures_wait
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Generic, TypeVar

from stages.context import StageContext

T = TypeVar("T")

# How often the coordinating thread wakes to publish worker narration while the
# fan-out is in flight. Publishing itself stays throttled by the driver's pulse
# (run.py PULSE_MIN_INTERVAL_S); this only bounds how stale an *urgent* node
# transition can get before it reaches the repo.
_PUBLISH_INTERVAL_S = 2.0


@lru_cache(maxsize=1)
def fanout_width() -> int:
    """How many agents run at once (§5.4), from config/budgets.yml
    ``specialist_concurrency`` — a §13 rate knob, owned there, not hardcoded
    (CLAUDE.md §6 "one owner per fact"). Bounded below the six-specialist fan so
    the burst of tool-loop calls respects the Gemini rate budget; raise it in
    the config as quota allows."""
    import yaml

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "config" / "budgets.yml"
        if candidate.is_file():
            with candidate.open(encoding="utf-8") as fh:
                budgets = yaml.safe_load(fh) or {}
            return max(1, int(budgets.get("specialist_concurrency", 3)))
    raise FileNotFoundError(f"Could not locate config/budgets.yml above {here}.")


class DeferredPulse:
    """Stands in for ``status.pulse`` while fan-out workers run (§5.4).

    Narration from a worker thread asks to publish; publishing means
    ``status.save`` plus a git commit, and the working copy is single-writer
    (§14) — a commit from a worker would race the coordinator's commits and
    could stage a file another part of the stage is mid-writing. So worker
    pulses are only *recorded* here; the coordinating thread drains the request
    between waits and publishes through the driver's real pulse, keeping every
    commit on one thread. Lock ordering is acyclic: this lock is only ever held
    for the flag flip — the coordinator drains (this lock), releases, and only
    then publishes (which takes the status lock inside ``save``)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._dirty = False
        self._urgent = False

    def __call__(self, urgent: bool) -> None:
        with self._lock:
            self._dirty = True
            self._urgent = self._urgent or urgent

    def drain(self) -> bool | None:
        """The pending request's urgency, or None if nothing was asked. Clears it."""
        with self._lock:
            if not self._dirty:
                return None
            urgent = self._urgent
            self._dirty = self._urgent = False
            return urgent


@dataclass
class AgentTask(Generic[T]):
    """One agent's unit of concurrent work (§5.4).

    ``work`` runs on a worker thread: narration (the thread-safe status model)
    plus LLM/KB compute only — **never a file write or a commit**. ``finish``
    runs on the coordinating thread once ``work`` returns: it writes the agent's
    files and completes its node, so every disk write the committer can stage,
    and every commit, stays single-threaded (§14)."""

    name: str
    work: Callable[[], T]
    finish: Callable[[T], None]


def run_agent_tasks(ctx: StageContext, tasks: list[AgentTask]) -> None:
    """Fan ``tasks`` out over a bounded thread pool (§5.4 — at most
    ``fanout_width()`` in flight; any KB a worker opens is its own, and the
    write scope of each result is disjoint by construction, §9.3/§6.2).

    While workers run, ``ctx.status.pulse`` is swapped for a :class:`DeferredPulse`
    and the coordinator publishes on their behalf between waits, so narration
    still reaches the repo on the §6.3 cadence but only ever from this thread.
    Each task's ``finish`` runs here as its worker completes — a finished draft
    is written and pulse-committed without waiting for the slowest agent,
    preserving the per-agent resume granularity (§5.3).

    On a worker failure: not-yet-started tasks are cancelled (their agents stay
    ``pending`` and re-run on resume), already-running ones are allowed to end
    and their results are still finished (their files are on disk, so the
    failure commit preserves them and the §5.3 idempotent skip honours them),
    and the first error then propagates to the driver's calm-failure path
    (§5.6)."""
    if not tasks:
        return
    deferred = DeferredPulse()
    original_pulse = ctx.status.pulse
    ctx.status.pulse = deferred

    def publish() -> None:
        urgent = deferred.drain()
        if urgent is not None and original_pulse is not None:
            original_pulse(urgent)

    first_error: BaseException | None = None
    try:
        with ThreadPoolExecutor(
            max_workers=min(fanout_width(), len(tasks)),
            thread_name_prefix="fanout",
        ) as pool:
            pending = {pool.submit(task.work): task for task in tasks}
            while pending:
                done, _ = futures_wait(
                    pending, timeout=_PUBLISH_INTERVAL_S, return_when=FIRST_COMPLETED
                )
                for future in done:
                    task = pending.pop(future)
                    try:
                        result = future.result()
                    except BaseException as exc:  # BaseException: includes CancelledError
                        if first_error is None:
                            first_error = exc
                            for other in pending:
                                other.cancel()  # only not-yet-started tasks cancel
                        continue
                    try:
                        task.finish(result)
                    except BaseException:
                        # A coordinator-side failure (write/serialise): stop admitting
                        # queued work before propagating, as with a worker failure.
                        for other in pending:
                            other.cancel()
                        raise
                publish()
        # The pool has exited: every worker has ended, so restoring the pulse
        # below cannot race a late worker narration into a worker-side commit.
    finally:
        ctx.status.pulse = original_pulse
    publish()
    if first_error is not None:
        raise first_error
