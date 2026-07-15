"""Brainstorm phase — the co-design interview that fills the outline (TECH_SPEC §7, §7.1).

The backend half of Stage 1: the interviewer (Flash-Lite) that runs one conversational turn
and writes resolved outline sections, and the sufficiency judge (Flash-Lite + a deterministic
gate) that tells the user when the outline is a sound basis for governance. The outline
document model itself lives in ``backend/outline.py`` (its single owner, §7.1); the
transcript persistence lives in ``transcript.py`` here. PoC / flow-map / feasibility (the
rest of the ``brainstorm/`` run directory) are a later slice.
"""

from __future__ import annotations

from brainstorm.interviewer import InterviewerResult, run_interviewer
from brainstorm.sufficiency import assess_sufficiency
from brainstorm.transcript import Transcript

__all__ = [
    "InterviewerResult",
    "run_interviewer",
    "assess_sufficiency",
    "Transcript",
]
