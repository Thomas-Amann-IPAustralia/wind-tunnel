"""pipeline.stages — the state-machine stage handlers (TECH_SPEC §5).

Each handler does exactly one state's work over a :class:`StageContext`: it reads
the committed inputs, runs its agents / deterministic computations, writes the
state's checkpoint artefacts, and narrates progress on ``status``. It never commits
or advances the stage — the driver (run.py) checkpoints and advances (§5.3).
"""

from stages.context import StageContext
from stages.threshold import threshold_drafting, threshold_reconciling

__all__ = ["StageContext", "threshold_drafting", "threshold_reconciling"]
