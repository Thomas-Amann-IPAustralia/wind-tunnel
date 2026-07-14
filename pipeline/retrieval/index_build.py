"""The LLM-readable index (TECH_SPEC §8.4).

Per document: sidecar metadata, a short extractive `what_it_is`, and a structure
tree of section/sheet nodes — each with a one-line description, its chunk-id
range, token count, and (for registries) the record-key range. This is the
catalogue a specialist navigates to decide *what applies* before it fetches
(§8.1). Descriptions here are EXTRACTIVE (headings, record-key ranges); the
optional Flash-written line for uninformative headings (§8.4) is deferred until a
Gemini id is pinned (config/models.yml) and is additive — it does not change this
structure.

A token budget bounds each index (config/retrieval.yml index.max_tokens, default
25K). The builder rolls the deepest levels up into their parents until under
budget, via a coarsening ladder: full section paths → top-level sections → lean
top-level nodes → a one-line-per-document summary. Individual records stay
addressable by record_key regardless of how coarse the index gets (§8.4).
"""

from __future__ import annotations

import json

from retrieval.model import DocumentKB
from retrieval.tokens import estimate_tokens

# (collapse_to_top, detail) rungs, least-coarse first.
_LADDER = [
    (False, "full"),
    (True, "full"),
    (True, "lean"),
    (True, "summary"),
]
_MAX_SECTION_NAMES = 60


def _group(doc: DocumentKB, collapse_to_top: bool) -> tuple[list[str], dict[str, list]]:
    grouped: dict[str, list] = {}
    order: list[str] = []
    for c in doc.chunks:
        key = c.section_path.split(" > ")[0] if collapse_to_top else c.section_path
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(c)
    return order, grouped


def _record_summary(chunks: list, detail: str) -> dict | None:
    keys = [c.record_key for c in chunks if c.record_key]
    if not keys:
        return None
    summary = {"count": len(keys), "range": [keys[0], keys[-1]]}
    if detail == "full":
        summary["examples"] = keys[:3]
    return summary


def _node(section: str, chunks: list, detail: str) -> dict:
    node: dict = {
        "section": section or "(document root)",
        "chunk_count": len(chunks),
        "token_count": sum(c.token_count for c in chunks),
    }
    if detail == "full":
        chunk_ids = [c.chunk_id for c in chunks]
        node["description"] = section or "(document root)"
        node["chunk_range"] = [chunk_ids[0], chunk_ids[-1]]
        node["kinds"] = sorted({c.kind for c in chunks})
    rec = _record_summary(chunks, detail)
    if rec:
        node["record_keys"] = rec
    return node


def _doc_entry(doc: DocumentKB, collapse_to_top: bool, detail: str) -> dict:
    entry = {
        "doc_id": doc.doc_id,
        "short_name": doc.short_name,
        "title": doc.title,
        "version": doc.version,
        "publisher": doc.publisher,
        "source_url": doc.source_url,
        "format": doc.format,
        "page_count": doc.page_count,
        "what_it_is": doc.title,
        "chunk_count": len(doc.chunks),
    }
    order, grouped = _group(doc, collapse_to_top)
    if detail == "summary":
        entry["sections"] = order[:_MAX_SECTION_NAMES]
        if len(order) > _MAX_SECTION_NAMES:
            entry["sections_truncated"] = len(order) - _MAX_SECTION_NAMES
        rec = _record_summary(doc.chunks, "lean")
        if rec:
            entry["record_keys"] = rec
    else:
        entry["structure"] = [_node(k, grouped[k], detail) for k in order]
    return entry


def _assemble(
    specialist: str, documents: list[DocumentKB], generated_at: str, collapse: bool, detail: str
) -> dict:
    return {
        "specialist": specialist,
        "generated_at": generated_at,
        "document_count": len(documents),
        "retrieval": "Navigate this index, then fetch(refs) or search(query, k) (TECH_SPEC §8.1).",
        "documents": [_doc_entry(d, collapse, detail) for d in documents],
    }


def build_index(
    specialist: str, documents: list[DocumentKB], generated_at: str, max_tokens: int
) -> dict:
    """Build the index dict at the least-coarse ladder rung that fits max_tokens."""
    index = None
    chosen = _LADDER[-1]
    for collapse, detail in _LADDER:
        index = _assemble(specialist, documents, generated_at, collapse, detail)
        chosen = (collapse, detail)
        if estimate_tokens(json.dumps(index, ensure_ascii=False)) <= max_tokens:
            break
    collapse, detail = chosen
    if (collapse, detail) != _LADDER[0]:
        index["_coarsened"] = (
            f"collapse_to_top={collapse}, detail={detail} to fit "
            f"index.max_tokens={max_tokens}; records remain fetchable by key."
        )
    index["index_tokens_estimate"] = estimate_tokens(json.dumps(index, ensure_ascii=False))
    return index
