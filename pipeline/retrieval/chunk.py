"""Structural chunking (TECH_SPEC §8.6 step 3).

Chunk along the document's own structure. Small prose siblings sharing a section
and locator are packed toward the target band; an oversized single segment is
split at paragraph then sentence boundaries with a part suffix on its locator.
Records (numbered controls/criteria/patterns) and serialized tables are kept
1:1 so their locator/record_key stays exact. A chunk NEVER crosses a structural
boundary, so its locator is unambiguous — that invariant is the citation-integrity
guarantee (PROJECT_BRIEF §10), not a nicety. No sliding-window overlap: structure
replaces it.
"""

from __future__ import annotations

import re

from retrieval.model import Chunk, Segment
from retrieval.tokens import estimate_tokens

_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _split_text(text: str, max_tokens: int) -> list[str]:
    """Split an oversized text at sentence boundaries, packing back toward the
    cap. A single sentence longer than the cap is emitted whole (never mid-word)."""
    if estimate_tokens(text) <= max_tokens:
        return [text]
    parts: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for sentence in _SENTENCE.split(text):
        st = estimate_tokens(sentence)
        if current and current_tokens + st > max_tokens:
            parts.append(" ".join(current))
            current, current_tokens = [], 0
        current.append(sentence)
        current_tokens += st
    if current:
        parts.append(" ".join(current))
    return parts


def _part_locator(locator: str, part: int, total: int) -> str:
    return locator if total == 1 else f"{locator} (pt {part}/{total})"


def _finalize(doc_id: str, drafts: list[dict]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for seq, d in enumerate(drafts):
        chunks.append(
            Chunk(
                chunk_id=f"{doc_id}:{seq:05d}",
                seq=seq,
                locator=d["locator"],
                section_path=d["section_path"],
                kind=d["kind"],
                record_key=d.get("record_key"),
                text=d["text"],
                token_count=estimate_tokens(d["text"]),
            )
        )
    return chunks


def chunk_segments(
    doc_id: str,
    segments: list[Segment],
    target_min: int,
    target_max: int,
) -> list[Chunk]:
    drafts: list[dict] = []
    i, n = 0, len(segments)
    while i < n:
        seg = segments[i]

        # records and tables: keep atomic; split only if a single one is oversized.
        if seg.kind in ("record", "table"):
            pieces = _split_text(seg.text, target_max)
            for p, piece in enumerate(pieces, start=1):
                drafts.append(
                    {
                        "locator": _part_locator(seg.locator, p, len(pieces)),
                        "section_path": seg.section_path,
                        "kind": seg.kind,
                        "record_key": seg.record_key,
                        "text": piece,
                    }
                )
            i += 1
            continue

        # prose: gather the contiguous run sharing this section_path AND locator,
        # so packing never merges across a boundary or a locator change.
        run = [seg]
        j = i + 1
        while (
            j < n
            and segments[j].kind == "prose"
            and segments[j].section_path == seg.section_path
            and segments[j].locator == seg.locator
        ):
            run.append(segments[j])
            j += 1
        i = j

        # greedily pack the run's paragraphs into the target band.
        buf: list[str] = []
        buf_tokens = 0
        for para in run:
            pt = estimate_tokens(para.text)
            if pt > target_max:
                # flush what we have, then split the oversized paragraph.
                if buf:
                    drafts.append(_prose_draft(seg, " ".join(buf)))
                    buf, buf_tokens = [], 0
                pieces = _split_text(para.text, target_max)
                for p, piece in enumerate(pieces, start=1):
                    drafts.append(_prose_draft(seg, piece, part=p, total=len(pieces)))
                continue
            if buf and buf_tokens + pt > target_max:
                drafts.append(_prose_draft(seg, " ".join(buf)))
                buf, buf_tokens = [], 0
            buf.append(para.text)
            buf_tokens += pt
        if buf:
            drafts.append(_prose_draft(seg, " ".join(buf)))

    return _finalize(doc_id, drafts)


def _prose_draft(seg: Segment, text: str, part: int = 1, total: int = 1) -> dict:
    return {
        "locator": _part_locator(seg.locator, part, total),
        "section_path": seg.section_path,
        "kind": "prose",
        "record_key": None,
        "text": text,
    }
