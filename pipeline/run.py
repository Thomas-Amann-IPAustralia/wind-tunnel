"""pipeline/run.py — the governance state-machine driver (TECH_SPEC §5).

On every ``workflow_dispatch`` this reads ``run.json``, routes to the current
stage, runs its handler, commits the checkpoint, and advances — until a user pause,
a terminal state, or a failure (§5.3). Four invariants live here:

  * **Idempotent resume (§5.3).** Before running a stage, the driver checks whether
    that stage's checkpoint *output files* already exist — the spec's literal test —
    and if so advances past it. A job that dies mid-stage loses only that stage's
    uncommitted work.
  * **The start handshake (§5.7).** The first action is a ``heartbeat`` +
    ``overall_state=running``, committed, so the SPA learns the run actually started
    by watching ``status.json`` advance.
  * **Calm failure (§5.6).** Any unhandled error becomes ``run.json`` failed +
    ``last_error`` and ``status.json`` failed + failure payload, committed; the run
    code resumes from the last good checkpoint. Stack traces never reach the primary
    UI.
  * **The commit is the checkpoint.** Committing ``run.json`` + ``status.json`` +
    the stage artefacts is done through an injected :class:`Committer`, so the whole
    driver is testable with no git (a fake) and runs for real in Actions (git).

The driver routes the threshold path end-to-end to ``THRESHOLD_REVIEW``, and the
full path through ``FULL_DRAFTING`` to whichever comes next: the ``FULL_CHECKPOINT``
user pause if a specialist raised a question, or ``ARCHITECT`` otherwise. ``ARCHITECT``
writes the implementation-plan appendix, ``REVIEW`` runs the bounded reviewer loop
(coverage + coherence + residual, §11), and ``ASSEMBLY`` builds the notebook + HTML
report and finalises the run at ``COMPLETE``. The full governance path now runs
end-to-end. When a specialist raised a checkpoint question, the run pauses at
``FULL_CHECKPOINT``; a ``resume_from=FULL_REVISING`` dispatch (once the user submits
answers) resumes into ``FULL_REVISING``, which revises the questioning specialists'
sections before ``ARCHITECT``. After ``COMPLETE``, a ``resume_from=USER_REVISION``
dispatch (from ``POST /revise``) runs the ≤2 full-assessment revision path — reviewer
triage → targeted amendment → one verify pass → ``ASSEMBLY`` rebuilds and returns to
``COMPLETE`` (§5.8).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from llm import GeminiTransport, LLMClient
from stages.assembly import (
    ASSEMBLY_NODE,
    HTML_RELPATH,
    NOTEBOOK_RELPATH,
    assembly,
)
from stages.context import StageContext
from stages.full import (
    ARCHITECT_MD_RELPATH,
    ARCHITECT_NODE,
    QUESTIONS_RELPATH,
    RESIDUAL_RELPATH,
    REVIEWER_NODE,
    REVISED_RELPATH,
    SPECIALISTS,
    architect,
    full_drafting,
    full_revising,
    review,
    revision_verification_relpath,
    user_revision,
)
from stages.threshold import (
    NODE_A,
    NODE_RECONCILER,
    threshold_drafting,
    threshold_reconciling,
)
from statefile import RunState, Stage, StageStatus, utc_now_iso
from status import StatusModel

# Stage → its handler. Stages absent here are either boundary/pause/terminal states
# handled inline, or not yet implemented (USER_REVISION).
_HANDLERS: dict[Stage, Callable[[StageContext], None]] = {
    Stage.THRESHOLD_DRAFTING: threshold_drafting,
    Stage.THRESHOLD_RECONCILING: threshold_reconciling,
    Stage.FULL_DRAFTING: full_drafting,
    Stage.FULL_REVISING: full_revising,
    Stage.ARCHITECT: architect,
    Stage.REVIEW: review,
    Stage.ASSEMBLY: assembly,
    Stage.USER_REVISION: user_revision,
}

# Stage → the next stage on success. FULL_DRAFTING is conditional (see
# _resolve_next) — this is its default (questions were raised).
_NEXT: dict[Stage, Stage] = {
    Stage.SUBMITTED: Stage.THRESHOLD_DRAFTING,
    Stage.THRESHOLD_DRAFTING: Stage.THRESHOLD_RECONCILING,
    Stage.THRESHOLD_RECONCILING: Stage.THRESHOLD_REVIEW,
    Stage.FULL_DRAFTING: Stage.FULL_CHECKPOINT,
    Stage.FULL_REVISING: Stage.ARCHITECT,
    Stage.ARCHITECT: Stage.REVIEW,
    Stage.REVIEW: Stage.ASSEMBLY,
    Stage.ASSEMBLY: Stage.COMPLETE,
    Stage.USER_REVISION: Stage.ASSEMBLY,
}


def _resolve_next(stage: Stage, run_dir: Path) -> Stage:
    """The stage after ``stage`` completes. Only FULL_DRAFTING branches at
    runtime (§5.1): if no specialist raised a question, FULL_CHECKPOINT (and
    FULL_REVISING, which exists only to act on answers) are skipped entirely —
    the happy path goes straight to ARCHITECT (skipping the checkpoint pause)."""
    if stage is Stage.FULL_DRAFTING and not (run_dir / QUESTIONS_RELPATH).is_file():
        return Stage.ARCHITECT
    return _NEXT[stage]


# Stage → the checkpoint output files whose existence means the stage is done (§5.3).
# USER_REVISION is absent here on purpose: its checkpoint path carries the revision number
# (rev_<N>/verification.json), which is resolved from run.json at check time — see
# _checkpoint_outputs.
_CHECKPOINT_OUTPUTS: dict[Stage, tuple[str, ...]] = {
    Stage.THRESHOLD_DRAFTING: ("threshold/generalist_a.json", "threshold/generalist_b.json"),
    Stage.THRESHOLD_RECONCILING: (
        "threshold/reconciled.json",
        "threshold/ratings.json",
        "threshold/routing.json",
        "threshold/divergence.json",
    ),
    Stage.FULL_DRAFTING: tuple(f"full/specialists/{s}.json" for s in SPECIALISTS),
    Stage.FULL_REVISING: (REVISED_RELPATH,),
    Stage.ARCHITECT: (ARCHITECT_MD_RELPATH,),
    Stage.REVIEW: (RESIDUAL_RELPATH,),
    Stage.ASSEMBLY: (NOTEBOOK_RELPATH, HTML_RELPATH),
}


def _checkpoint_outputs(run: RunState, stage: Stage) -> tuple[str, ...]:
    """The checkpoint output files for ``stage`` (§5.3). Most are a fixed table entry;
    USER_REVISION's is per-revision (rev_<N>/verification.json), so it is resolved from
    ``run.json``'s ``revisions.full`` — the revision the dispatch is working on."""
    if stage is Stage.USER_REVISION:
        return (revision_verification_relpath(run.revisions.get("full", 0)),)
    return _CHECKPOINT_OUTPUTS.get(stage, ())


# Stage → a representative node for a failure with no single active node (§5.6).
_STAGE_FAIL_NODE: dict[Stage, str] = {
    Stage.THRESHOLD_DRAFTING: NODE_A,
    Stage.THRESHOLD_RECONCILING: NODE_RECONCILER,
    Stage.FULL_DRAFTING: f"full.specialist.{SPECIALISTS[0]}",
    Stage.FULL_REVISING: f"full.specialist.{SPECIALISTS[0]}",
    Stage.ARCHITECT: ARCHITECT_NODE,
    Stage.REVIEW: REVIEWER_NODE,
    Stage.ASSEMBLY: ASSEMBLY_NODE,
    Stage.USER_REVISION: REVIEWER_NODE,
}

# Human phrase per stage for the calm failure message (§5.6, design §7.2.4).
_STAGE_PHRASE: dict[Stage, str] = {
    Stage.THRESHOLD_DRAFTING: "drafting the threshold assessment",
    Stage.THRESHOLD_RECONCILING: "reconciling the threshold assessment",
    Stage.FULL_DRAFTING: "drafting the full assessment specialist sections",
    Stage.FULL_REVISING: "revising the full assessment in light of your answers",
    Stage.ARCHITECT: "writing the implementation-plan appendix",
    Stage.REVIEW: "reviewing the full assessment",
    Stage.ASSEMBLY: "assembling the notebook and report",
    Stage.USER_REVISION: "revising the full assessment",
}


def _setup_full_checkpoint(run_dir: Path, status: StatusModel) -> None:
    questions = json.loads((run_dir / QUESTIONS_RELPATH).read_text(encoding="utf-8"))
    status.wait_node("full.checkpoint")
    status.set_questions(questions)


# Stage → one-time setup run when a pause stage is first entered (§5.1, §6.4).
# THRESHOLD_REVIEW needs none — it pauses via overall_state alone (Decisions,
# STATUS.md). FULL_CHECKPOINT additionally sets its node waiting_user and
# attaches the batched questions payload written by FULL_DRAFTING.
_PAUSE_SETUP: dict[Stage, Callable[[Path, StatusModel], None]] = {
    Stage.FULL_CHECKPOINT: _setup_full_checkpoint,
}

_PAUSE_STAGES: frozenset[Stage] = frozenset({Stage.THRESHOLD_REVIEW, Stage.FULL_CHECKPOINT})
_TERMINAL_STAGES: frozenset[Stage] = frozenset({Stage.COMPLETE, Stage.CONCLUDED, Stage.FAILED})


class StageNotImplemented(RuntimeError):
    """A stage was routed to that this build does not yet handle (full.* stages)."""


@dataclass
class RunResult:
    """The outcome of one driver invocation (one Actions dispatch)."""

    ok: bool
    final_stage: Stage
    stage_status: StageStatus
    commits: int


class Committer(Protocol):
    """The commit seam (§14). ``commit`` durably records the current run directory
    and returns the resulting commit sha (or a marker). Serialised per run."""

    def commit(self, run_dir: Path, message: str) -> str: ...


@dataclass
class FakeCommitter:
    """A no-git committer for tests: persists nothing beyond what the driver already
    wrote to disk, and returns a monotonic fake sha so checkpoint provenance is
    exercised without a repo."""

    count: int = 0

    def commit(self, run_dir: Path, message: str) -> str:
        self.count += 1
        return f"fake{self.count:04d}"


class GitPushError(RuntimeError):
    """Raised when a checkpoint commit could not be pushed after retrying through
    the fetch→rebase→push cycle (TECH_SPEC §14). Left unpushed, a checkpoint only
    exists in the ephemeral Actions container and is not durable — this must be a
    loud failure, not a silent local-only commit."""


@dataclass
class GitCommitter:
    """The Actions-side committer (§14): ``git add`` the run directory, commit with
    the built-in ``GITHUB_TOKEN`` identity, and **push every commit immediately**.

    Every stage checkpoint must be durable the instant it is committed — the
    Actions runner's disk is destroyed at job end (§14 "Render disk is ephemeral"
    applies equally here), and a user pause or a mid-run crash both rely on the
    *pushed* history for resume (§5.2, §5.6). A local-only commit that is never
    pushed would be invisible to the next dispatch and to the backend's status
    proxy, silently breaking near-real-time polling. Push failures are retried
    with the fetch→rebase→push cycle (§14) to absorb another writer's commits to
    a different run's disjoint path.

    A no-op commit (nothing staged) returns the current HEAD rather than failing
    or pushing."""

    repo_root: Path
    remote: str = "origin"
    branch: str | None = None  # None => whatever is currently checked out
    push_retries: int = 4
    sleep: Callable[[float], None] = field(default=time.sleep)

    def commit(self, run_dir: Path, message: str) -> str:
        subprocess.run(["git", "add", "-A", str(run_dir)], cwd=self.repo_root, check=True)
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", message], cwd=self.repo_root, check=True)
            self._push_with_retry()
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return head.stdout.strip()

    def _push_with_retry(self) -> None:
        branch = self.branch or self._current_branch()
        delay = 1.0
        for attempt in range(1, self.push_retries + 1):
            result = subprocess.run(
                ["git", "push", self.remote, f"HEAD:{branch}"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return
            if attempt == self.push_retries:
                raise GitPushError(
                    f"git push to {self.remote}/{branch} failed after "
                    f"{self.push_retries} attempts: {result.stderr.strip()}"
                )
            # Non-fast-forward: another writer committed to a disjoint path (§14).
            # Rebase onto the latest remote tip and retry — our changes touch only
            # this run's own files, so the rebase applies cleanly. Best-effort: if
            # the remote is genuinely unreachable, fetch/rebase themselves fail
            # (not just the push), and the loop's final push attempt reports that.
            subprocess.run(
                ["git", "fetch", self.remote, branch], cwd=self.repo_root, capture_output=True
            )
            subprocess.run(
                ["git", "rebase", f"{self.remote}/{branch}"],
                cwd=self.repo_root,
                capture_output=True,
            )
            self.sleep(delay)
            delay *= 2

    def _current_branch(self) -> str:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()


def run_pipeline(
    run_dir: str | Path,
    *,
    llm: LLMClient,
    committer: Committer,
    resume_from: str | None = None,
    now: Callable[[], str] = utc_now_iso,
    kb_root: Path | None = None,
) -> RunResult:
    """Drive one dispatch of the run at ``run_dir`` to its next pause/terminal/failure.

    ``resume_from`` (the dispatch input, §5.3/§5.7) is trusted as the dispatcher's
    statement of where to resume; idempotent skip then protects any stage whose
    outputs already exist. ``kb_root`` overrides where FULL_DRAFTING looks for
    specialist KBs (§8) — tests inject a fixture directory; production leaves it
    None and the stage resolves the real repo ``kb/``."""
    run_dir = Path(run_dir)
    run = RunState.load(run_dir)
    status = StatusModel.load(run_dir, run)

    if resume_from:
        target = Stage(resume_from)
        if target is not run.stage:
            run.advance_to(target, now=now())

    # §5.7 handshake: the "tunnel is running" signal, committed first.
    status.set_running(now=now())
    status.heartbeat(now=now())
    commits = _persist_and_commit(run, status, run_dir, committer, "heartbeat (running)")

    try:
        commits += _drive(run_dir, run, status, llm, committer, now, kb_root)
    except Exception as exc:  # §5.6: any unhandled error → calm, resumable failure
        commits += _fail(run, status, run_dir, committer, exc, now)
        return RunResult(False, run.stage, run.stage_status, commits)

    return RunResult(True, run.stage, run.stage_status, commits)


def _drive(
    run_dir: Path,
    run: RunState,
    status: StatusModel,
    llm: LLMClient,
    committer: Committer,
    now: Callable[[], str],
    kb_root: Path | None = None,
) -> int:
    commits = 0
    while True:
        stage = run.stage

        if run.stage_status is StageStatus.FAILED:
            return commits
        if stage in _TERMINAL_STAGES:
            commits += _finalise_terminal(run, status, run_dir, committer, stage, now)
            return commits

        if stage in _PAUSE_STAGES:
            if run.stage_status is not StageStatus.AWAITING_USER:
                run.advance_to(stage, StageStatus.AWAITING_USER, now=now())
                status.set_overall("paused", now=now())
                setup = _PAUSE_SETUP.get(stage)
                if setup is not None:
                    setup(run_dir, status)
                commits += _persist_and_commit(
                    run, status, run_dir, committer, f"paused at {stage} (awaiting user)"
                )
            return commits

        if stage is Stage.SUBMITTED:
            run.advance_to(_NEXT[stage], now=now())
            continue

        handler = _HANDLERS.get(stage)
        if handler is None:
            raise StageNotImplemented(f"No handler for stage {stage}.")

        if _checkpoint_exists(run_dir, run, stage):
            run.advance_to(_resolve_next(stage, run_dir), now=now())
            continue

        status.heartbeat(agent="pipeline", now=now())
        handler(
            StageContext(run_dir=run_dir, run=run, status=status, llm=llm, now=now, kb_root=kb_root)
        )

        # Commit the stage's outputs + status at THIS stage (checkpoint), then advance
        # in memory; the advance persists on the next commit. Idempotency keys off the
        # committed output files (§5.3), so a death before the next commit re-resolves
        # correctly by skipping this now-complete stage.
        sha = _commit(run_dir, committer, f"{stage} checkpoint")
        commits += 1
        run.set_checkpoint(stage, sha, now=now())
        run.advance_to(_resolve_next(stage, run_dir), now=now())


def _finalise_terminal(
    run: RunState,
    status: StatusModel,
    run_dir: Path,
    committer: Committer,
    stage: Stage,
    now: Callable[[], str],
) -> int:
    """Mark a run terminal-complete when it first reaches COMPLETE/CONCLUDED (§5.1). The
    ASSEMBLY→COMPLETE transition lands here: set ``stage_status=complete`` and
    ``overall_state=complete`` and commit, so the SPA's poll sees the run finish. FAILED
    is handled by ``_fail`` and never reaches this; a re-entry after completion is a
    no-op (idempotent)."""
    if stage is Stage.FAILED or status.overall_state == "complete":
        return 0
    run.advance_to(stage, StageStatus.COMPLETE, now=now())
    status.set_complete(now=now())
    return _persist_and_commit(run, status, run_dir, committer, f"{stage} (complete)")


def _checkpoint_exists(run_dir: Path, run: RunState, stage: Stage) -> bool:
    outputs = _checkpoint_outputs(run, stage)
    return bool(outputs) and all((run_dir / rel).is_file() for rel in outputs)


def _fail(
    run: RunState,
    status: StatusModel,
    run_dir: Path,
    committer: Committer,
    exc: Exception,
    now: Callable[[], str],
) -> int:
    node = _failing_node(status, run.stage)
    phrase = _STAGE_PHRASE.get(run.stage, "running the assessment")
    message = (
        f"Something went wrong while {phrase}. Your run is safe — paste the run code "
        f"{run.run_id} to resume from the last checkpoint."
    )
    technical = f"{type(exc).__name__}: {exc}"
    run.fail(node, message, technical, now=now())
    status.fail_node(node, message, technical, run_code=run.run_id, now=now())
    return _persist_and_commit(run, status, run_dir, committer, f"failed at {run.stage}")


def _failing_node(status: StatusModel, stage: Stage) -> str:
    for node_id, state in status.nodes.items():
        if state == "active":
            return node_id
    return _STAGE_FAIL_NODE.get(stage, NODE_A)


def _persist_and_commit(
    run: RunState,
    status: StatusModel,
    run_dir: Path,
    committer: Committer,
    message: str,
) -> int:
    run.save(run_dir)
    status.save(run_dir)
    _commit(run_dir, committer, message)
    return 1


def _commit(run_dir: Path, committer: Committer, message: str) -> str:
    return committer.commit(run_dir, f"run {run_dir.name}: {message}")


def main(argv: list[str] | None = None) -> int:
    """Actions entrypoint: ``python -m run <run-id> [--resume-from STAGE]``."""
    import argparse

    parser = argparse.ArgumentParser(description="Windtunnel governance pipeline driver.")
    parser.add_argument("run_id", help="the run code, e.g. WT-ABCD-EF")
    parser.add_argument("--resume-from", default=None, help="dispatch resume_from input (§5.3)")
    parser.add_argument("--runs-root", default="runs", help="root holding runs/<run-id>/")
    args = parser.parse_args(argv)

    repo_root = _find_repo_root()
    run_dir = repo_root / args.runs_root / args.run_id
    llm = LLMClient(transport=GeminiTransport())
    committer = GitCommitter(repo_root=repo_root)
    result = run_pipeline(run_dir, llm=llm, committer=committer, resume_from=args.resume_from)
    print(
        f"run {args.run_id}: {result.final_stage} ({result.stage_status}), {result.commits} commits"
    )
    return 0 if result.ok else 1


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "instrument").is_dir() and (parent / "config").is_dir():
            return parent
    return Path.cwd()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
