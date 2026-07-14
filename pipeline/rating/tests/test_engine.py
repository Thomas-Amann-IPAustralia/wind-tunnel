"""Rating-engine tests — hand-worked from the REAL DTA Table 2 (TECH_SPEC §15).

The expected values below are read directly from Table 2 in
instrument/guidance/AI_impact_assessment_tool.md, not from the conventional 5x5
scaffold once shown in TECH_SPEC §10.1 (which differs). Stage 2's exit test is
"ratings match a hand-worked assessment exactly" (PROJECT_BRIEF §9); this is that
check for the engine itself. A single wrong cell here is a fidelity failure.
"""

import pytest

from rating import (
    RatingError,
    consequence_tiers,
    likelihood_tiers,
    overall_rating,
    rating,
    ratings_ordered,
)

# The entire Table 2, transcribed from the source tool (likelihood-rows x
# consequence-columns), as a flat truth table. Independent of the JSON so a
# transcription error in either the engine data or here is caught by the other.
# Row order: Almost certain, Likely, Possible, Unlikely, Rare.
TABLE_2 = {
    # consequence:      Insig.   Minor    Moderate Major    Severe
    "Almost certain": ["Medium", "Medium", "High", "High", "High"],
    "Likely": ["Medium", "Medium", "Medium", "High", "High"],
    "Possible": ["Low", "Medium", "Medium", "High", "High"],
    "Unlikely": ["Low", "Low", "Medium", "Medium", "High"],
    "Rare": ["Low", "Low", "Low", "Medium", "Medium"],
}
CONSEQUENCE_COLS = ["Insignificant", "Minor", "Moderate", "Major", "Severe"]


@pytest.mark.parametrize("likelihood", list(TABLE_2))
def test_every_table2_cell_matches_source(likelihood):
    for col, consequence in enumerate(CONSEQUENCE_COLS):
        expected = TABLE_2[likelihood][col]
        got = rating(consequence, likelihood)
        assert got == expected, (
            f"Table 2 mismatch at ({consequence}, {likelihood}): engine={got} source={expected}"
        )


def test_rating_set_has_no_very_high():
    # The real Table 2 tops out at High — the scaffold's 'Very high' does not exist.
    assert ratings_ordered() == ("Low", "Medium", "High")


def test_tier_vocabularies_are_ascending_and_complete():
    assert consequence_tiers() == ("Insignificant", "Minor", "Moderate", "Major", "Severe")
    assert likelihood_tiers() == ("Rare", "Unlikely", "Possible", "Likely", "Almost certain")


def test_spot_check_known_cells():
    # A few explicit anchors a human can eyeball against the printed table.
    assert rating("Insignificant", "Rare") == "Low"
    assert rating("Severe", "Rare") == "Medium"  # NOT High — Rare/Severe is Medium
    assert rating("Severe", "Almost certain") == "High"  # top of the matrix is High
    assert rating("Major", "Possible") == "High"
    assert rating("Moderate", "Almost certain") == "High"
    assert rating("Moderate", "Likely") == "Medium"  # differs from the scaffold


def test_rating_raises_on_unknown_consequence():
    with pytest.raises(RatingError):
        rating("Catastrophic", "Likely")


def test_rating_raises_on_unknown_likelihood():
    with pytest.raises(RatingError):
        rating("Major", "Certain")


def test_rating_is_case_sensitive_and_loud():
    # No silent case-folding — an off-vocabulary label fails loudly (TECH_SPEC §10.2).
    with pytest.raises(RatingError):
        rating("major", "possible")


def test_overall_rating_highest_wins():
    assert overall_rating(["Low", "Medium", "High"]) == "High"
    assert overall_rating(["Low", "Low", "Medium"]) == "Medium"
    assert overall_rating(["Low"]) == "Low"
    # Order-independent.
    assert overall_rating(["High", "Low", "Medium"]) == "High"


def test_overall_rating_worked_example_from_reconciler():
    # Design §7.4 / TECH_SPEC §10.3 worked example: disagreement resolves upward,
    # then the engine computes. Assessor A: Moderate; Assessor B: Major -> Major.
    resolved_consequence = "Major"
    resolved_likelihood = "Possible"
    section_rating = rating(resolved_consequence, resolved_likelihood)
    assert section_rating == "High"
    # If that were the only medium+ section, the overall is High.
    assert overall_rating(["Low", "Medium", section_rating]) == "High"


def test_overall_rating_empty_raises():
    with pytest.raises(RatingError):
        overall_rating([])


def test_overall_rating_raises_on_unknown_rating():
    with pytest.raises(RatingError):
        overall_rating(["Low", "Extreme"])
