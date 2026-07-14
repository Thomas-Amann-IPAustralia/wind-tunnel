"""Instrument-encoding integrity (TECH_SPEC §6.2, §9.3, §10.1; CLAUDE.md §8).

These are non-negotiable test targets (CLAUDE.md §4): they assert the transcribed
instrument JSON is internally consistent, that every full-assessment section maps
to exactly one specialist owner (or an explicit non-specialist marker), and that
the ownership map has no silent hole.
"""

from tests.conftest import CONFIG, CORPUS, load_yaml

SPECIALISTS = {"it_security", "privacy", "ethics", "legal", "data_governance", "solution_architect"}
NON_SPECIALIST_OWNERS = {"reviewer", "human_action"}


# --- Table cross-consistency -------------------------------------------------


def test_likelihood_tiers_agree_across_tables(likelihood_table, risk_matrix):
    assert likelihood_table["tiers_ordered"] == risk_matrix["likelihood_tiers"]
    labels = [t["label"] for t in likelihood_table["tiers"]]
    assert labels == likelihood_table["tiers_ordered"]


def test_consequence_tiers_agree_across_tables(consequence_table, risk_matrix):
    assert consequence_table["tiers_ordered"] == risk_matrix["consequence_tiers"]


def test_every_risk_section_has_full_consequence_descriptors(consequence_table, risk_matrix):
    tiers = risk_matrix["consequence_tiers"]
    for sec_id in ("3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.8"):
        section = consequence_table["sections"][sec_id]
        assert set(section["descriptors"]) == set(tiers), (
            f"{sec_id} descriptors do not cover every consequence tier"
        )
        for tier in tiers:
            assert section["descriptors"][tier].strip(), f"{sec_id}/{tier} descriptor is empty"


def test_matrix_is_complete_and_in_vocabulary(risk_matrix):
    ratings = set(risk_matrix["ratings_ordered"])
    for consequence in risk_matrix["consequence_tiers"]:
        row = risk_matrix["matrix"][consequence]
        for likelihood in risk_matrix["likelihood_tiers"]:
            assert row[likelihood] in ratings


# --- Ownership: the 1:1 assertion (TECH_SPEC §6.2, CLAUDE.md §8) --------------


def test_specialist_set_matches_spec(sections):
    assert set(sections["specialists"]) == SPECIALISTS


def test_full_assessment_ownership_is_single_valued(sections):
    ownership = sections["full_assessment_ownership"]
    allowed = SPECIALISTS | NON_SPECIALIST_OWNERS
    for sec_id, owner in ownership.items():
        assert isinstance(owner, str) and owner in allowed, (
            f"{sec_id} owner {owner!r} is not a single valid owner"
        )


def test_every_specialist_owns_at_least_one_section(sections):
    owned = set(sections["full_assessment_ownership"].values())
    missing = SPECIALISTS - owned
    assert not missing, f"specialists with no owned section (silent hole): {missing}"


def test_ownership_and_questions_cover_the_same_full_sections(sections, questions):
    """Every full-assessment subsection in questions.json must have an owner in
    sections.json, and vice versa — no drifting between the two encodings."""
    q_full = {
        sub["id"]
        for section in questions["sections"]
        if section.get("phase") == "full"
        for sub in section["subsections"]
    }
    owned = set(sections["full_assessment_ownership"])
    assert q_full == owned, f"questions-only: {q_full - owned}; ownership-only: {owned - q_full}"


def test_question_owner_matches_ownership_map(sections, questions):
    ownership = sections["full_assessment_ownership"]
    for section in questions["sections"]:
        if section.get("phase") != "full":
            continue
        for sub in section["subsections"]:
            assert sub["owner"] == ownership[sub["id"]], (
                f"{sub['id']}: questions.json owner {sub['owner']!r} != "
                f"sections.json owner {ownership[sub['id']]!r}"
            )


def test_8_5_is_owned_ethics_not_a_hole(sections):
    # The decision recorded in sections.json _decisions.8.5 must hold in the map.
    assert sections["full_assessment_ownership"]["8.5"] == "ethics"


def test_no_full_section_between_5_and_12_is_missing(sections, questions):
    """Guard against a dropped subsection: every X.Y heading in questions.json
    for sections 5–12 is present in the ownership map."""
    expected = set()
    for section in questions["sections"]:
        if section.get("phase") != "full":
            continue
        for sub in section["subsections"]:
            expected.add(sub["id"])
    assert expected == set(sections["full_assessment_ownership"])


# --- Corpus ↔ KB specialist mapping ------------------------------------------


def test_kb_specialists_match_corpus_folders(sections):
    kb = {k: v for k, v in sections["kb_specialists"].items() if not k.startswith("_")}
    assert set(kb) == SPECIALISTS
    for specialist, rel in kb.items():
        assert rel == f"corpus/{specialist}"
        assert (CORPUS / specialist).is_dir(), f"corpus folder missing for {specialist}"


# --- Licence gate config coherence (TECH_SPEC §8.6 step 1) -------------------


def test_every_sidecar_licence_is_in_allow_list():
    """Prove the ingestion licence gate will PASS on the current corpus: every
    sidecar records redistributable: true and a licence in config/licences.yml."""
    allow = set(load_yaml(CONFIG / "licences.yml")["allow_list"])
    offenders = []
    for meta in sorted(CORPUS.glob("*/*.meta.yml")):
        d = load_yaml(meta)
        if d.get("redistributable") is not True or str(d.get("licence")).strip() not in allow:
            offenders.append((str(meta.relative_to(CORPUS)), d.get("licence")))
    assert not offenders, f"documents that would fail the licence gate: {offenders}"


def test_allow_list_has_no_unused_entries():
    """Keep the allow-list honest: every listed licence is actually used by a
    sidecar (a stale entry would mask a typo). If Tom adds a new-licence doc,
    add its licence here in the same change."""
    allow = load_yaml(CONFIG / "licences.yml")["allow_list"]
    used = {str(load_yaml(m).get("licence")).strip() for m in CORPUS.glob("*/*.meta.yml")}
    unused = set(allow) - used
    assert not unused, f"allow-list entries not used by any sidecar: {unused}"
