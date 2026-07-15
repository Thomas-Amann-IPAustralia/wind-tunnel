"""Reference resolution for the report (TECH_SPEC §12.1, design §8).

The specialists cite corpus documents by ``short_name`` + ``locator`` (§9.4). The
report ends with a full reference list — every cited document once, resolved against
the KB **manifests** (``kb/<specialist>.manifest.json``, §8.5) to its title,
publisher, version, and source URL, so a reader can find and check the source.

Pure and LLM-free: it takes the specialists' citation blocks and the manifest
documents and returns a deduplicated, ordered reference list. ``short_name`` is the
citation key (unique per specialist, §8.5); a document cited by more than one
specialist appears once, with all its cited locators gathered.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Reference:
    """One resolved bibliography entry. ``resolved`` is False when a cited
    ``short_name`` has no matching manifest document — surfaced honestly rather than
    dropped, so a dangling citation is visible in the report, not silently hidden."""

    short_name: str
    title: str
    publisher: str
    version: str
    source_url: str
    locators: list[str] = field(default_factory=list)
    specialists: list[str] = field(default_factory=list)
    resolved: bool = True

    def to_dict(self) -> dict:
        return {
            "short_name": self.short_name,
            "title": self.title,
            "publisher": self.publisher,
            "version": self.version,
            "source_url": self.source_url,
            "locators": self.locators,
            "specialists": self.specialists,
            "resolved": self.resolved,
        }


def build_document_index(manifests: list[dict]) -> dict[str, dict]:
    """Merge the KB manifests into a ``short_name → document`` map. A ``short_name`` is
    unique within a specialist's manifest (§8.5); across specialists a shared document
    resolves to the same entry, so first-seen wins and the merge is stable."""
    index: dict[str, dict] = {}
    for manifest in manifests:
        for doc in manifest.get("documents") or []:
            short = doc.get("short_name")
            if short and short not in index:
                index[short] = doc
    return index


def resolve_references(
    citations_by_specialist: dict[str, dict[str, list[dict]]],
    document_index: dict[str, dict],
) -> list[Reference]:
    """Collect every citation across the specialists, dedupe by ``short_name``, resolve
    each against ``document_index``, and return the reference list ordered by title (a
    dangling, unresolved citation sorts under its own short_name). Locators are gathered
    and de-duplicated per document, preserving first-seen order."""
    refs: dict[str, Reference] = {}
    for specialist, sections in citations_by_specialist.items():
        for entries in (sections or {}).values():
            for entry in entries or []:
                short = entry.get("short_name")
                locator = entry.get("locator", "")
                if not short:
                    continue
                ref = refs.get(short)
                if ref is None:
                    ref = _new_reference(short, document_index.get(short))
                    refs[short] = ref
                if locator and locator not in ref.locators:
                    ref.locators.append(locator)
                if specialist not in ref.specialists:
                    ref.specialists.append(specialist)
    return sorted(
        refs.values(), key=lambda r: (not r.resolved, r.title.lower(), r.short_name.lower())
    )


def _new_reference(short_name: str, doc: dict | None) -> Reference:
    if doc is None:
        return Reference(
            short_name=short_name,
            title=short_name,
            publisher="",
            version="",
            source_url="",
            resolved=False,
        )
    return Reference(
        short_name=short_name,
        title=str(doc.get("title") or short_name),
        publisher=str(doc.get("publisher") or ""),
        version=str(doc.get("version") or ""),
        source_url=str(doc.get("source_url") or ""),
    )
