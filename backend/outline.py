"""The outline document — the single source of truth for the concept (TECH_SPEC §7.1).

Two jobs live here, and only here (the backend is the sole writer of ``outline.md``, §7.1):

  * **Initialisation** — ``render_initial_outline`` copies ``templates/outline.md`` verbatim
    with ``run_id``/``created_at`` filled, the one write ``POST /api/runs`` makes.
  * **Amendment** — the ``Outline`` document model: parse the front-matter + the nine
    anchored sections, replace whole section bodies between anchors (regeneration at
    section granularity, never a text patch), maintain ``resolved``/``updated_at``/
    ``title``/``summary``, and compute the ``outline_delta`` the canvas animates.

The section registry (ids + headings) is fixed (§7.1); machine operations locate sections
by their ``<!-- section: <id> -->`` anchor, never by heading text. ``resolved`` is the single
deterministic record of completeness — there is no text heuristic; an explicit negative
statement ("headless, no interface") is a resolution, written like any other body.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "outline.md"

# The fixed section registry (§7.1): id → heading title, in document order. The one owner
# of this fact on the backend side; the outline template mirrors it and is asserted against
# it in tests.
SECTION_REGISTRY: tuple[tuple[str, str], ...] = (
    ("problem", "Problem"),
    ("solution", "Proposed solution"),
    ("users_stakeholders", "Users and stakeholders"),
    ("data", "Data"),
    ("happy_path", "Happy path"),
    ("alternatives", "Alternatives considered"),
    ("ux_ui", "UX and interface"),
    ("constraints", "Constraints and preferences"),
    ("success_criteria", "Success criteria"),
)
SECTION_IDS: tuple[str, ...] = tuple(sid for sid, _ in SECTION_REGISTRY)

# The front-matter keys, in the canonical order they are re-emitted (§7.1).
_FRONTMATTER_KEYS: tuple[str, ...] = (
    "schema_version",
    "run_id",
    "title",
    "summary",
    "created_at",
    "updated_at",
    "resolved",
)

_ANCHOR_RE = re.compile(r"(?m)^<!-- section: (?P<id>[a-z_]+) -->[ \t]*$")
_FRONTMATTER_RE = re.compile(r"\A(?P<lead>.*?)---\n(?P<fm>.*?)\n---\n(?P<rest>.*)\Z", re.DOTALL)
_HEADING_RE = re.compile(r"(?m)^## .*$")


class OutlineError(RuntimeError):
    """A malformed outline document, or an operation on an unknown section id. Loud — the
    backend re-reads the outline from the repo per request (§14), so a corrupt file must
    fail visibly rather than silently drop a user's edit."""


def render_initial_outline(run_id: str, now: str) -> str:
    """The template with ``run_id``/``created_at``/``updated_at`` filled into the
    front-matter, otherwise byte-for-byte the committed template (§7.1: "copies it
    verbatim"). Front-matter fields are known-empty (``""``) in the template, so a
    first-occurrence literal replace is exact and does not touch the body."""
    text = _TEMPLATE_PATH.read_text(encoding="utf-8")
    text = text.replace('run_id: ""', f'run_id: "{run_id}"', 1)
    text = text.replace('created_at: ""', f'created_at: "{now}"', 1)
    text = text.replace('updated_at: ""', f'updated_at: "{now}"', 1)
    return text


@dataclass
class _Section:
    id: str
    heading: str  # the "## N. Title" line, preserved verbatim
    body: str  # everything between the heading and the next anchor, stripped


@dataclass
class OutlineUpdate:
    """The result of applying interviewer/canvas updates to an outline. ``delta`` is the
    §7.1 ``outline_delta`` the canvas animates (or ``None`` when nothing the canvas cares
    about changed); ``changed`` is whether the document bytes changed at all (a summary-only
    edit changes the file but carries no canvas delta)."""

    delta: dict | None
    changed: bool


@dataclass
class Outline:
    """The ``outline.md`` document model (§7.1). Round-trips: ``Outline.parse(text).render()``
    reproduces an equivalent document (front-matter re-emitted in canonical order)."""

    lead: str  # everything before the front-matter (the template's HTML comment)
    frontmatter: dict
    sections: list[_Section] = field(default_factory=list)

    # -- parse / render ---------------------------------------------------------

    @classmethod
    def parse(cls, text: str) -> "Outline":
        m = _FRONTMATTER_RE.match(text)
        if not m:
            raise OutlineError("outline.md has no YAML front-matter block.")
        frontmatter = yaml.safe_load(m.group("fm")) or {}
        if not isinstance(frontmatter, dict):
            raise OutlineError("outline.md front-matter is not a mapping.")
        rest = m.group("rest")

        sections: list[_Section] = []
        anchors = list(_ANCHOR_RE.finditer(rest))
        for i, anchor in enumerate(anchors):
            start = anchor.end()
            end = anchors[i + 1].start() if i + 1 < len(anchors) else len(rest)
            block = rest[start:end]
            heading_match = _HEADING_RE.search(block)
            if not heading_match:
                raise OutlineError(f"section {anchor.group('id')!r} has no '## ' heading.")
            heading = heading_match.group(0)
            body = block[heading_match.end() :].strip()
            sections.append(_Section(id=anchor.group("id"), heading=heading, body=body))
        return cls(lead=m.group("lead"), frontmatter=frontmatter, sections=sections)

    def render(self) -> str:
        out = [self.lead, "---\n", self._render_frontmatter(), "---\n"]
        for section in self.sections:
            out.append(f"\n<!-- section: {section.id} -->\n{section.heading}\n\n{section.body}\n")
        return "".join(out)

    def _render_frontmatter(self) -> str:
        fm = self.frontmatter
        lines: list[str] = []
        for key in _FRONTMATTER_KEYS:
            if key == "schema_version":
                lines.append(f"schema_version: {int(fm.get('schema_version', 1))}")
            elif key == "resolved":
                # a JSON array is valid YAML flow-sequence; ids are safe bare scalars but
                # quoting keeps the round-trip unambiguous.
                lines.append(f"resolved: {json.dumps(self.resolved)}")
            else:
                lines.append(f"{key}: {json.dumps(str(fm.get(key, '')))}")
        return "\n".join(lines) + "\n"

    # -- accessors --------------------------------------------------------------

    @property
    def resolved(self) -> list[str]:
        """Populated section ids, in registry order (§7.1: the single record of
        completeness). Sanitised to known ids so a malformed front-matter list can never
        leak an unknown id downstream."""
        raw = self.frontmatter.get("resolved") or []
        present = {str(s) for s in raw}
        return [sid for sid in SECTION_IDS if sid in present]

    def section_body(self, section_id: str) -> str:
        for section in self.sections:
            if section.id == section_id:
                return section.body
        raise OutlineError(f"unknown section id {section_id!r}.")

    def is_complete(self) -> bool:
        """The deterministic sufficiency gate (§7.1): every registry section resolved."""
        return set(self.resolved) == set(SECTION_IDS)

    # -- mutation ---------------------------------------------------------------

    def _set_body(self, section_id: str, body: str) -> None:
        for section in self.sections:
            if section.id == section_id:
                section.body = body
                return
        raise OutlineError(f"unknown section id {section_id!r}.")

    def apply_updates(
        self,
        section_updates: dict[str, str],
        *,
        title: str | None = None,
        summary: str | None = None,
        now: str,
    ) -> OutlineUpdate:
        """Apply section-body updates (and optional title/summary), maintaining ``resolved``
        and ``updated_at`` in the same write (§7.1 write rules). A section is validated
        against the registry; an empty body is ignored (never un-resolves a section here).
        Returns the ``outline_delta`` + whether the document changed at all."""
        unknown = set(section_updates) - set(SECTION_IDS)
        if unknown:
            raise OutlineError(f"unknown section id(s): {sorted(unknown)} (registry §7.1).")

        prior_resolved = set(self.resolved)
        updated: set[str] = set()
        for sid, body in section_updates.items():
            clean = (body or "").strip()
            if not clean:
                continue
            if self.section_body(sid) != clean:
                self._set_body(sid, clean)
            updated.add(sid)

        title_changed = False
        if (
            title is not None
            and title.strip()
            and title.strip() != str(self.frontmatter.get("title", ""))
        ):
            self.frontmatter["title"] = title.strip()
            title_changed = True

        summary_changed = False
        if (
            summary is not None
            and summary.strip()
            and summary.strip() != str(self.frontmatter.get("summary", ""))
        ):
            self.frontmatter["summary"] = summary.strip()
            summary_changed = True

        newly_resolved = [
            sid for sid in SECTION_IDS if sid in updated and sid not in prior_resolved
        ]
        changed = bool(updated) or title_changed or summary_changed
        if changed:
            self.frontmatter["resolved"] = [
                sid for sid in SECTION_IDS if sid in prior_resolved or sid in updated
            ]
            self.frontmatter["updated_at"] = now

        # The canvas delta (§7.1) exists when a section body or the title changed; a
        # summary-only edit still commits but animates nothing.
        delta = None
        if updated or title_changed:
            delta = {
                "updated": [sid for sid in SECTION_IDS if sid in updated],
                "newly_resolved": newly_resolved,
                "title_changed": title_changed,
            }
        return OutlineUpdate(delta=delta, changed=changed)
