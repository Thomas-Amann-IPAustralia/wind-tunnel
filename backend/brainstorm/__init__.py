"""Brainstorm phase — the co-design interview that fills the outline (TECH_SPEC §7, §7.1).

The backend half of Stage 1: the interviewer (Flash-Lite) that runs one conversational turn
and writes resolved outline sections, and the sufficiency judge (Flash-Lite + a deterministic
gate) that tells the user when the outline is a sound basis for governance; plus the three
synthesis agents that produce the optional brainstorm artefacts — the feasibility gate
(Flash-Lite), the PoC generator (Flash → self-contained ``poc.html``), and the flow-map
generator (Flash → Mermaid source the SPA renders to SVG, CLAUDE.md §9). The outline document
model itself lives in ``backend/outline.py`` (its single owner, §7.1); the transcript
persistence lives in ``transcript.py`` here.
"""

from __future__ import annotations

from brainstorm.feasibility import FeasibilityResult, assess_feasibility
from brainstorm.interviewer import InterviewerResult, ingest_seed_material, run_interviewer
from brainstorm.mapgen import MapResult, generate_flow_map, validate_mermaid
from brainstorm.poc import PocResult, generate_poc, validate_poc_html
from brainstorm.sufficiency import assess_sufficiency
from brainstorm.transcript import Transcript

__all__ = [
    "InterviewerResult",
    "run_interviewer",
    "ingest_seed_material",
    "assess_sufficiency",
    "assess_feasibility",
    "FeasibilityResult",
    "generate_poc",
    "validate_poc_html",
    "PocResult",
    "generate_flow_map",
    "validate_mermaid",
    "MapResult",
    "Transcript",
]
