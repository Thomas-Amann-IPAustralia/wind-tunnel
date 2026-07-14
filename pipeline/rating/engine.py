"""Deterministic rating engine — "models argue, code computes" (TECH_SPEC §10).

LLM agents select a consequence tier and a likelihood tier with an evidenced
rationale; the risk rating is computed HERE, deterministically, from the DTA
tool's Table 2 (instrument/risk_matrix.json). The overall inherent rating (§3.9)
and overall residual rating (§12.4) are computed highest-wins. No model ever
asserts a rating, and this module never calls an LLM or does I/O beyond loading
the instrument JSON (TECH_SPEC §10.2).

Every public function validates its inputs against the instrument tables and
raises RatingError on anything unrecognised — an LLM that emits an off-vocabulary
tier fails loudly rather than silently miscomputing (TECH_SPEC §10.2, §9.4).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


class RatingError(ValueError):
    """Raised when a consequence/likelihood/rating label is not in the instrument
    tables, or the instrument data is missing/malformed. A hard, loud failure —
    never a silent fallback (TECH_SPEC §10.2)."""


def _find_instrument_dir() -> Path:
    """Locate the repo's instrument/ directory (holds the transcribed tables).

    Walks up from this file until it finds a directory named ``instrument`` that
    contains ``risk_matrix.json``. Keeps the engine location-independent so it
    works from the pipeline package, tests, or an Actions checkout alike.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "instrument"
        if (candidate / "risk_matrix.json").is_file():
            return candidate
    raise RatingError(
        "Could not locate instrument/ (with risk_matrix.json) above "
        f"{here}. The rating engine's data is the single source of truth "
        "(TECH_SPEC §10.1) and must be present."
    )


def _load_json(name: str) -> dict:
    path = _find_instrument_dir() / name
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        raise RatingError(f"Instrument file missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RatingError(f"Instrument file is not valid JSON: {path} — {exc}") from exc


@lru_cache(maxsize=1)
def _matrix() -> dict:
    """Load and structurally validate Table 2 once (cached).

    Asserts the matrix is complete and internally consistent: every declared
    consequence tier has a cell for every declared likelihood tier, and every
    cell value is a declared rating. A hole or a stray value is a transcription
    fault and must fail loudly (TECH_SPEC §10.1 fidelity rule).
    """
    data = _load_json("risk_matrix.json")
    consequence_tiers = data.get("consequence_tiers")
    likelihood_tiers = data.get("likelihood_tiers")
    ratings_ordered = data.get("ratings_ordered")
    matrix = data.get("matrix")
    if not (consequence_tiers and likelihood_tiers and ratings_ordered and matrix):
        raise RatingError("risk_matrix.json is missing required keys.")

    ratings_set = set(ratings_ordered)
    for consequence in consequence_tiers:
        row = matrix.get(consequence)
        if row is None:
            raise RatingError(f"risk_matrix.json: no row for consequence '{consequence}'.")
        for likelihood in likelihood_tiers:
            if likelihood not in row:
                raise RatingError(
                    f"risk_matrix.json: no cell for ('{consequence}', '{likelihood}')."
                )
            value = row[likelihood]
            if value not in ratings_set:
                raise RatingError(
                    f"risk_matrix.json: cell ('{consequence}', '{likelihood}') = "
                    f"'{value}' is not in ratings_ordered {ratings_ordered}."
                )
    return {
        "consequence_tiers": tuple(consequence_tiers),
        "likelihood_tiers": tuple(likelihood_tiers),
        "ratings_ordered": tuple(ratings_ordered),
        "matrix": matrix,
    }


def consequence_tiers() -> tuple[str, ...]:
    """The valid consequence labels, ascending (Insignificant → Severe)."""
    return _matrix()["consequence_tiers"]


def likelihood_tiers() -> tuple[str, ...]:
    """The valid likelihood labels, ascending (Rare → Almost certain)."""
    return _matrix()["likelihood_tiers"]


def ratings_ordered() -> tuple[str, ...]:
    """The rating set, ascending. For the real DTA Table 2 this is
    ('Low', 'Medium', 'High') — there is no 'Very high' tier (TECH_SPEC §10.1)."""
    return _matrix()["ratings_ordered"]


def rating(consequence: str, likelihood: str) -> str:
    """Return the Table 2 risk rating for a (consequence, likelihood) pair.

    Both labels must be exact members of the instrument tables (no case-folding
    or fuzzy matching — a mismatch is surfaced, not smoothed). Raises RatingError
    on any unrecognised label (TECH_SPEC §10.2).
    """
    data = _matrix()
    if consequence not in data["consequence_tiers"]:
        raise RatingError(
            f"Unknown consequence tier: {consequence!r}. "
            f"Expected one of {list(data['consequence_tiers'])}."
        )
    if likelihood not in data["likelihood_tiers"]:
        raise RatingError(
            f"Unknown likelihood tier: {likelihood!r}. "
            f"Expected one of {list(data['likelihood_tiers'])}."
        )
    return data["matrix"][consequence][likelihood]


def overall_rating(ratings: list[str]) -> str:
    """Highest-wins overall rating (TECH_SPEC §10.2; DTA guidance §3.9 / §12.4).

    Returns the highest rating present in ``ratings`` by the instrument's
    ratings_ordered. Every element must be a valid rating; an empty list raises
    (an overall rating with no component ratings is undefined). Raises
    RatingError on any unrecognised rating.
    """
    order = _matrix()["ratings_ordered"]
    if not ratings:
        raise RatingError(
            "overall_rating() requires at least one component rating "
            "(the §3.9 overall is the highest of §3.1–3.8)."
        )
    index = {label: i for i, label in enumerate(order)}
    highest = -1
    highest_label = ""
    for r in ratings:
        if r not in index:
            raise RatingError(f"Unknown rating: {r!r}. Expected one of {list(order)}.")
        if index[r] > highest:
            highest = index[r]
            highest_label = r
    return highest_label
