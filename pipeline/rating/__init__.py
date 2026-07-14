"""pipeline.rating — the deterministic risk-rating engine (TECH_SPEC §10).

Public surface (TECH_SPEC §10.2):
    rating(consequence, likelihood) -> str   # Table 2 cell
    overall_rating(ratings)         -> str   # highest-wins (§3.9 / §12.4)

Plus the instrument vocabularies for callers that build schemas/prompts:
    consequence_tiers(), likelihood_tiers(), ratings_ordered()

and RatingError for the loud-failure contract.
"""

from rating.engine import (
    RatingError,
    consequence_tiers,
    likelihood_tiers,
    overall_rating,
    rating,
    ratings_ordered,
)

__all__ = [
    "RatingError",
    "rating",
    "overall_rating",
    "consequence_tiers",
    "likelihood_tiers",
    "ratings_ordered",
]
