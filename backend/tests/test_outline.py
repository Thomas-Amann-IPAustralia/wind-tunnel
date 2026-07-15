"""Tests for the outline document model (TECH_SPEC §7.1).

The outline is the single source of truth for the concept, so its parse/render/delta
machinery is the load-bearing part of Brainstorm: a dropped edit or a miscomputed
``resolved`` list corrupts everything downstream. LLM-free — this is pure document code.
"""

from __future__ import annotations

import pytest

from outline import (
    SECTION_IDS,
    SECTION_REGISTRY,
    Outline,
    OutlineError,
    render_initial_outline,
)

NOW = "2026-07-15T00:00:00Z"


def _doc() -> Outline:
    return Outline.parse(render_initial_outline("WT-ABCD-EF", NOW))


def test_template_has_every_registry_section_in_order():
    # The template mirrors the registry (§7.1) — same ids, same order, matching headings.
    doc = _doc()
    assert [s.id for s in doc.sections] == list(SECTION_IDS)
    for (sid, title), section in zip(SECTION_REGISTRY, doc.sections):
        assert section.id == sid
        assert title in section.heading


def test_initial_outline_resolves_nothing():
    doc = _doc()
    assert doc.resolved == []
    assert not doc.is_complete()
    assert doc.frontmatter["run_id"] == "WT-ABCD-EF"


def test_apply_updates_resolves_and_deltas():
    doc = _doc()
    u = doc.apply_updates({"problem": "The problem."}, title="T", summary="S", now=NOW)
    assert u.changed is True
    assert u.delta == {"updated": ["problem"], "newly_resolved": ["problem"], "title_changed": True}
    assert doc.resolved == ["problem"]
    assert doc.frontmatter["title"] == "T"
    assert doc.frontmatter["summary"] == "S"
    assert doc.frontmatter["updated_at"] == NOW


def test_apply_updates_refine_is_update_not_newly_resolved():
    doc = _doc()
    doc.apply_updates({"problem": "v1"}, now=NOW)
    u = doc.apply_updates({"problem": "v2"}, now=NOW)
    assert u.delta["updated"] == ["problem"]
    assert u.delta["newly_resolved"] == []
    assert doc.section_body("problem") == "v2"


def test_apply_updates_orders_by_registry_not_input():
    doc = _doc()
    u = doc.apply_updates({"data": "d", "problem": "p"}, now=NOW)
    assert u.delta["updated"] == ["problem", "data"]  # registry order
    assert doc.resolved == ["problem", "data"]


def test_apply_updates_rejects_unknown_section():
    doc = _doc()
    with pytest.raises(OutlineError, match="unknown section"):
        doc.apply_updates({"nope": "x"}, now=NOW)


def test_apply_updates_ignores_empty_body():
    doc = _doc()
    u = doc.apply_updates({"problem": "   "}, now=NOW)
    assert u.changed is False
    assert doc.resolved == []


def test_no_change_returns_null_delta():
    doc = _doc()
    u = doc.apply_updates({}, now=NOW)
    assert u.delta is None
    assert u.changed is False


def test_summary_only_change_commits_but_no_canvas_delta():
    doc = _doc()
    u = doc.apply_updates({}, summary="One sentence.", now=NOW)
    assert u.changed is True  # the file changed
    assert u.delta is None  # ...but the canvas animates nothing (§7.1)
    assert doc.frontmatter["summary"] == "One sentence."


def test_roundtrip_preserves_content():
    doc = _doc()
    doc.apply_updates(
        {"problem": "The problem.", "ux_ui": "Headless, no interface."}, title="T", now=NOW
    )
    doc2 = Outline.parse(doc.render())
    assert doc2.resolved == ["problem", "ux_ui"]
    assert doc2.section_body("problem") == "The problem."
    assert doc2.section_body("ux_ui") == "Headless, no interface."
    assert doc2.frontmatter["title"] == "T"


def test_is_complete_when_all_resolved():
    doc = _doc()
    doc.apply_updates({sid: f"body {sid}" for sid in SECTION_IDS}, now=NOW)
    assert doc.is_complete()


def test_resolved_sanitises_unknown_ids():
    doc = _doc()
    doc.frontmatter["resolved"] = ["problem", "bogus", "data"]
    assert doc.resolved == ["problem", "data"]  # registry order, unknown dropped


def test_parse_rejects_missing_frontmatter():
    with pytest.raises(OutlineError, match="front-matter"):
        Outline.parse("no front matter here\n## 1. Problem\n")
