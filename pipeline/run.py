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

The full-assessment stages (FULL_DRAFTING onward) are not built yet; the driver
routes the threshold path end-to-end and stops cleanly at ``THRESHOLD_REVIEW``.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from llm import GeminiTransport, LLMClient
from stages.context import StageContext
from stages.threshold import (
    NODE_A,
    NODE_RECONCILER,
    threshold_drafting,
    threshold_reconciling,
)
from statefile import RunState, Stage, StageStatus, utc_now_iso
from status import StatusModel

# Stage → its handler. Stages absent here are either boundary/pause/terminal states
# handled inline, or not yet implemented (full.*).
_HANDLERS: dict[Stage, Callable[[StageContext], None]] = {
    Stage.THRESHOLD_DRAFTING: threshold_drafting,
    Stage.THRESHOLD_RECONCILING: threshold_reconciling,
}

# Stage → the next stage on success.
_NEXT: dict[Stage, Stage] = {
    Stage.SUBMITTED: Stage.THRESHOLD_DRAFTING,
    Stage.THRESHOLD_DRAFTING: Stage.THRESHOLD_RECONCILING,
    Stage.THRESHOLD_RECONCILING: Stage.THRESHOLD_REVIEW,
}

# Stage → the checkpoint output files whose existence means the stage is done (§5.3).
_CHECKPOINT_OUTPUTS: dict[Stage, tuple[str, ...]] = {
    Stage.THRESHOLD_DRAFTING: ("threshold/generalist_a.json", "threshold/generalist_b.json"),
    Stage.THRESHOLD_RECONCILING: (
        "threshold/reconciled.json",
        "threshold/ratings.json",
        "threshold/routing.json",
        "threshold/divergence.json",
    ),
}

# Stage → a representative node for a failure with no single active node (§5.6).
_STAGE_FAIL_NODE: dict[Stage, str] = {
    Stage.THRESHOLD_DRAFTING: NODE_A,
    Stage.THRESHOLD_RECONCILING: NODE_RECONCILER,
}

# Human phrase per stage for the calm failure message (§5.6, design §7.2.4).
_STAGE_PHRASE: dict[Stage, str] = {
    Stage.THRESHOLD_DRAFTING: "drafting the threshold assessment",
    Stage.THRESHOLD_RECONCILING: "reconciling the threshold assessment",
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


@dataclass
class GitCommitter:
    """The Actions-side committer (§14): ``git add`` the run directory and commit with
    the built-in ``GITHUB_TOKEN`` identity. A no-op commit (nothing staged) returns
    the current HEAD rather than failing."""

    repo_root: Path

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
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return head.stdout.strip()


def run_pipeline(
    run_dir: str | Path,
    *,
    llm: LLMClient,
    committer: Committer,
    resume_from: str | None = None,
    now: Callable[[], str] = utc_now_iso,
) -> RunResult:
    """Drive one dispatch of the run at ``run_dir`` to its next pause/terminal/failure.

    ``resume_from`` (the dispatch input, §5.3/§5.7) is trusted as the dispatcher's
    statement of where to resume; idempotent skip then protects any stage whose
    outputs already exist."""
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
        commits += _drive(run_dir, run, status, llm, committer, now)
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
) -> int:
    commits = 0
    while True:
        stage = run.stage

        if run.stage_status is StageStatus.FAILED:
            return commits
        if stage in _TERMINAL_STAGES:
            return commits

        if stage in _PAUSE_STAGES:
            if run.stage_status is not StageStatus.AWAITING_USER:
                run.advance_to(stage, StageStatus.AWAITING_USER, now=now())
                status.set_overall("paused", now=now())
                commits += _persist_and_commit(
                    run, status, run_dir, committer, f"paused at {stage} (awaiting user)"
                )
            return commits

        if stage is Stage.SUBMITTED:
            run.advance_to(_NEXT[stage], now=now())
            continue

        handler = _HANDLERS.get(stage)
        if handler is None:
            raise StageNotImplemented(f"No handler for stage {stage} (full.* not built yet).")

        if _checkpoint_exists(run_dir, stage):
            run.advance_to(_NEXT[stage], now=now())
            continue

        status.heartbeat(agent="pipeline", now=now())
        handler(StageContext(run_dir=run_dir, run=run, status=status, llm=llm, now=now))

        # Commit the stage's outputs + status at THIS stage (checkpoint), then advance
        # in memory; the advance persists on the next commit. Idempotency keys off the
        # committed output files (§5.3), so a death before the next commit re-resolves
        # correctly by skipping this now-complete stage.
        sha = _commit(run_dir, committer, f"{stage} checkpoint")
        commits += 1
        run.set_checkpoint(stage, sha, now=now())
        run.advance_to(_NEXT[stage], now=now())


def _checkpoint_exists(run_dir: Path, stage: Stage) -> bool:
    outputs = _CHECKPOINT_OUTPUTS.get(stage, ())
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
