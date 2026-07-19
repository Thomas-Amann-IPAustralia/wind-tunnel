"""run.json — the authoritative state machine (TECH_SPEC §4, §5).

``run.json`` is what the pipeline reads to resume; ``status.json`` (status.py) is
a *derived projection* for the UI and is never resumed from. Keeping them apart is
load-bearing (CLAUDE.md §3): everything a run needs to be resumed or audited lives
here, and the pipeline reconstructs state entirely from committed files, so a job
that dies mid-state loses only that state's uncommitted work (§5.3).

This module owns the run.json shape, its enums (the §5.1 states), the cap
invariants (revisions ≤2 per artefact, reviewer loop ≤2 — CLAUDE.md §3), and
atomic local read/write. It does no git/API I/O: committing the file is the
caller's job (backend github_io.py / pipeline statefile-commit, §14). Every
mutation is idempotent-friendly and validates loudly — an unknown stage or an
over-cap revision raises rather than corrupting the state machine.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

SCHEMA_VERSION = 1
RUN_JSON = "run.json"

# Per-artefact user-revision cap and reviewer internal-loop cap (brief §7,
# CLAUDE.md §3 "Caps hold"). Enforced loudly in record_revision/record_review_cycle.
REVISION_CAP = 2
REVIEW_CYCLE_CAP = 2

# The capped, user-revisable artefacts (PROJECT_BRIEF §7 / §7 /revise). One owner for
# the revision counts: run.json only — never the outline front-matter (§7.1).
#
# The outline is deliberately NOT here. The brief settles it: "The interview conversation
# itself is unbounded" (§4) and the two-cycle cap applies only to "the information-flow
# map, the PoC, the threshold assessment and the full impact assessment" (§7) — the
# outline is refined without limit through the interview (/brainstorm/message) and canvas
# edits (/edit-outline), so it has no revision counter and no /revise branch. (This aligns
# the encoding with the brief's intent, which governs — CLAUDE.md §2; TECH_SPEC §7 was
# corrected to match.) `from_dict` ignores any legacy `revisions.outline` key.
REVISION_ARTEFACTS: tuple[str, ...] = ("poc", "flow_map", "threshold", "full")


class StateError(ValueError):
    """Raised on an invalid state transition, an over-cap revision, or malformed
    run.json. A hard, loud failure — the state machine never corrupts silently."""


class Stage(StrEnum):
    """Pipeline states (TECH_SPEC §5.1). The value is what run.json stores."""

    BRAINSTORM = "BRAINSTORM"
    SUBMITTED = "SUBMITTED"
    THRESHOLD_DRAFTING = "THRESHOLD_DRAFTING"
    THRESHOLD_RECONCILING = "THRESHOLD_RECONCILING"
    THRESHOLD_REVIEW = "THRESHOLD_REVIEW"
    FULL_DRAFTING = "FULL_DRAFTING"
    FULL_CHECKPOINT = "FULL_CHECKPOINT"
    FULL_REVISING = "FULL_REVISING"
    ARCHITECT = "ARCHITECT"
    REVIEW = "REVIEW"
    ASSEMBLY = "ASSEMBLY"
    COMPLETE = "COMPLETE"
    USER_REVISION = "USER_REVISION"
    CONCLUDED = "CONCLUDED"
    FAILED = "FAILED"


class StageStatus(StrEnum):
    """Status of the current stage (TECH_SPEC §4)."""

    IN_PROGRESS = "in_progress"
    AWAITING_USER = "awaiting_user"
    COMPLETE = "complete"
    FAILED = "failed"


class Phase(StrEnum):
    """UI framing phase (TECH_SPEC §4). Derived from stage; see _PHASE_OF_STAGE."""

    THRESHOLD = "threshold"
    FULL = "full"


# Which phase each stage belongs to (§4 "drives UI framing"). FAILED is absent on
# purpose: a failed run keeps the phase it failed in, so resume framing is honest.
_PHASE_OF_STAGE: dict[Stage, Phase] = {
    Stage.BRAINSTORM: Phase.THRESHOLD,
    Stage.SUBMITTED: Phase.THRESHOLD,
    Stage.THRESHOLD_DRAFTING: Phase.THRESHOLD,
    Stage.THRESHOLD_RECONCILING: Phase.THRESHOLD,
    Stage.THRESHOLD_REVIEW: Phase.THRESHOLD,
    Stage.CONCLUDED: Phase.THRESHOLD,
    Stage.FULL_DRAFTING: Phase.FULL,
    Stage.FULL_CHECKPOINT: Phase.FULL,
    Stage.FULL_REVISING: Phase.FULL,
    Stage.ARCHITECT: Phase.FULL,
    Stage.REVIEW: Phase.FULL,
    Stage.ASSEMBLY: Phase.FULL,
    Stage.COMPLETE: Phase.FULL,
    Stage.USER_REVISION: Phase.FULL,
}


def utc_now_iso() -> str:
    """UTC timestamp, seconds precision, ``Z`` suffix — the run.json time format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class RunState:
    """The run.json document (TECH_SPEC §4). ``phase`` is derived from ``stage``
    (except in failure, which preserves it); the rest is set explicitly."""

    run_id: str
    created_at: str
    updated_at: str
    stage: Stage = Stage.BRAINSTORM
    stage_status: StageStatus = StageStatus.IN_PROGRESS
    phase: Phase = Phase.THRESHOLD
    checkpoints: dict[str, str] = field(default_factory=dict)
    revisions: dict[str, int] = field(default_factory=lambda: {a: 0 for a in REVISION_ARTEFACTS})
    review_cycles: int = 0
    attestation: dict = field(default_factory=lambda: {"attested": False})
    last_error: dict | None = None
    schema_version: int = SCHEMA_VERSION

    # -- construction -----------------------------------------------------------

    @classmethod
    def new(
        cls,
        run_id: str,
        *,
        attested: bool = False,
        now: str | None = None,
    ) -> RunState:
        """A freshly created run: BRAINSTORM / in_progress / threshold, zeroed
        counters (TECH_SPEC §3, §5.1). Called by POST /api/runs (§7)."""
        ts = now or utc_now_iso()
        return cls(
            run_id=run_id,
            created_at=ts,
            updated_at=ts,
            attestation={"attested": attested},
        )

    # -- transitions ------------------------------------------------------------

    def touch(self, now: str | None = None) -> None:
        """Bump ``updated_at`` (the SPA's staleness reference, §5.7)."""
        self.updated_at = now or utc_now_iso()

    def advance_to(
        self,
        stage: Stage,
        stage_status: StageStatus = StageStatus.IN_PROGRESS,
        *,
        now: str | None = None,
    ) -> None:
        """Move to ``stage`` with ``stage_status``, updating the derived phase and
        clearing any prior error. FAILED preserves the phase it failed in."""
        self.stage = stage
        self.stage_status = stage_status
        if stage in _PHASE_OF_STAGE:
            self.phase = _PHASE_OF_STAGE[stage]
        if stage_status is not StageStatus.FAILED:
            self.last_error = None
        self.touch(now)

    def set_checkpoint(self, stage: Stage, commit_sha: str, *, now: str | None = None) -> None:
        """Record the commit SHA at which ``stage``'s outputs were durably written
        (§4). Resume treats a checkpointed stage's outputs as authoritative (§5.3)."""
        self.checkpoints[str(stage)] = commit_sha
        self.touch(now)

    def has_checkpoint(self, stage: Stage) -> bool:
        """Whether ``stage`` is already checkpoint-committed (idempotent resume, §5.3)."""
        return str(stage) in self.checkpoints

    def fail(
        self,
        node_id: str,
        message: str,
        technical: str,
        *,
        now: str | None = None,
    ) -> None:
        """Mark the run failed at ``node_id`` (TECH_SPEC §5.6).

        ``stage`` is deliberately left pointing at the failing stage so resume
        restarts it from its last good checkpoint (§5.3); ``stage_status=failed``
        is the failure marker. ``message`` is the plain, calm line; ``technical``
        sits behind "Show technical detail" (design §7.2.4). The last checkpoint
        stays intact.
        """
        self.stage_status = StageStatus.FAILED
        self.last_error = {"stage": node_id, "message": message, "technical": technical}
        self.touch(now)

    def set_attested(self, attested: bool = True, *, now: str | None = None) -> None:
        """Record the usage-warning attestation (set at submission, §7)."""
        self.attestation["attested"] = attested
        self.touch(now)

    # -- caps (CLAUDE.md §3 "Caps hold") ---------------------------------------

    def can_revise(self, artefact: str) -> bool:
        """Whether ``artefact`` has revisions left (< REVISION_CAP)."""
        self._check_artefact(artefact)
        return self.revisions[artefact] < REVISION_CAP

    def record_revision(self, artefact: str, *, now: str | None = None) -> int:
        """Consume one revision for ``artefact``; return the new count. Raises at
        the cap — a revision beyond the cap is refused, not silently dropped (§7)."""
        self._check_artefact(artefact)
        if self.revisions[artefact] >= REVISION_CAP:
            raise StateError(
                f"Revision cap reached for {artefact!r} "
                f"({self.revisions[artefact]}/{REVISION_CAP}). No further revisions (brief §7)."
            )
        self.revisions[artefact] += 1
        self.touch(now)
        return self.revisions[artefact]

    def can_review_again(self) -> bool:
        """Whether the reviewer internal loop may run another cycle (< cap, §11)."""
        return self.review_cycles < REVIEW_CYCLE_CAP

    def reset_review_cycles(self, *, now: str | None = None) -> None:
        """Reset the reviewer cycle counter to zero at REVIEW entry. REVIEW is a single
        pipeline checkpoint that re-runs its whole bounded ≤2-cycle loop on resume
        (§5.3), so the counter must reflect the current execution — a failed prior
        attempt (whose increments were committed by §5.6) must not shorten the fresh
        loop or trip the cap immediately."""
        self.review_cycles = 0
        self.touch(now)

    def record_review_cycle(self, *, now: str | None = None) -> int:
        """Consume one reviewer cycle; return the new count. Raises at the cap —
        unresolved conflicts after cycle 2 are recorded, not looped (§5.5, §11)."""
        if self.review_cycles >= REVIEW_CYCLE_CAP:
            raise StateError(
                f"Reviewer loop cap reached ({self.review_cycles}/{REVIEW_CYCLE_CAP}). "
                "Record unresolved disagreements rather than loop (§11)."
            )
        self.review_cycles += 1
        self.touch(now)
        return self.review_cycles

    @staticmethod
    def _check_artefact(artefact: str) -> None:
        if artefact not in REVISION_ARTEFACTS:
            raise StateError(
                f"Unknown revisable artefact: {artefact!r}. "
                f"Expected one of {list(REVISION_ARTEFACTS)}."
            )

    # -- serialisation ----------------------------------------------------------

    def to_dict(self) -> dict:
        """The run.json document, keys in the §4 order."""
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "stage": str(self.stage),
            "stage_status": str(self.stage_status),
            "phase": str(self.phase),
            "checkpoints": dict(self.checkpoints),
            "revisions": dict(self.revisions),
            "review_cycles": self.review_cycles,
            "attestation": dict(self.attestation),
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RunState:
        """Parse and validate a run.json document. Raises StateError on an unknown
        stage/status/phase or a missing required field (loud failure, §5.3)."""
        try:
            version = data["schema_version"]
            if version != SCHEMA_VERSION:
                raise StateError(
                    f"Unsupported run.json schema_version {version!r} (expected {SCHEMA_VERSION})."
                )
            stage = _parse_enum(Stage, data["stage"], "stage")
            stage_status = _parse_enum(StageStatus, data["stage_status"], "stage_status")
            phase = _parse_enum(Phase, data["phase"], "phase")
            revisions = {a: int(data["revisions"].get(a, 0)) for a in REVISION_ARTEFACTS}
            return cls(
                run_id=data["run_id"],
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                stage=stage,
                stage_status=stage_status,
                phase=phase,
                checkpoints=dict(data.get("checkpoints", {})),
                revisions=revisions,
                review_cycles=int(data.get("review_cycles", 0)),
                attestation=dict(data.get("attestation", {})),
                last_error=data.get("last_error"),
                schema_version=version,
            )
        except KeyError as exc:
            raise StateError(f"run.json missing required field: {exc}") from exc

    # -- local I/O (no git; commit is the caller's job, §14) --------------------

    @classmethod
    def load(cls, run_dir: str | os.PathLike) -> RunState:
        """Read ``<run_dir>/run.json`` — the authoritative resume read (§5.3)."""
        path = Path(run_dir) / RUN_JSON
        try:
            with path.open(encoding="utf-8") as fh:
                return cls.from_dict(json.load(fh))
        except FileNotFoundError as exc:
            raise StateError(f"No run.json at {path} — run not found or not created.") from exc
        except json.JSONDecodeError as exc:
            raise StateError(f"run.json is not valid JSON: {path} — {exc}") from exc

    def save(self, run_dir: str | os.PathLike) -> Path:
        """Atomically write ``<run_dir>/run.json`` (temp file + os.replace) so a
        crash mid-write never leaves a truncated authoritative file. Returns path.
        """
        run_path = Path(run_dir)
        run_path.mkdir(parents=True, exist_ok=True)
        target = run_path / RUN_JSON
        tmp = target.with_name(target.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, target)
        return target


def _parse_enum(enum_cls: type[StrEnum], value: str, field_name: str):
    try:
        return enum_cls(value)
    except ValueError as exc:
        valid = [str(m) for m in enum_cls]
        raise StateError(f"Unknown {field_name}: {value!r}. Expected one of {valid}.") from exc
