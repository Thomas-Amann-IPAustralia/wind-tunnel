"""Initialising a run's outline from the template (TECH_SPEC §7.1).

``POST /api/runs`` "copies [the template] verbatim ... with run_id/created_at
filled" — the only backend-side write to ``outline.md`` this build makes.
Turn-by-turn amendment (the interviewer, the canvas edit endpoint) is
Brainstorm-interview work, out of scope here (see STATUS.md).
"""

from __future__ import annotations

from pathlib import Path

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "outline.md"


def render_initial_outline(run_id: str, now: str) -> str:
    """The template with ``run_id``/``created_at``/``updated_at`` filled into the
    front-matter, otherwise byte-for-byte the committed template (§7.1: "copies
    it verbatim"). Front-matter fields are known-empty (``""``) in the template,
    so a first-occurrence literal replace is exact and does not risk touching
    the body."""
    text = _TEMPLATE_PATH.read_text(encoding="utf-8")
    text = text.replace('run_id: ""', f'run_id: "{run_id}"', 1)
    text = text.replace('created_at: ""', f'created_at: "{now}"', 1)
    text = text.replace('updated_at: ""', f'updated_at: "{now}"', 1)
    return text
