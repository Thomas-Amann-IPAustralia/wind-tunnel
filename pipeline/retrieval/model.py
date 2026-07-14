"""Shared data structures for ingestion and retrieval (TECH_SPEC §8).

A `Segment` is a leaf structural unit emitted by an extractor (§8.6 step 2): the
smallest piece of a document that still carries an unambiguous, human-checkable
locator (§8.2). The chunker (§8.6 step 3) packs/splits segments into `Chunk`s
that never cross a structural boundary. A `DocumentKB` is one ingested document
with its chunks, ready to write into kb/<specialist>.sqlite (§8.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Segment:
    text: str
    kind: str  # prose | record | table
    section_path: str  # heading path "A > B > C", or "" at document root
    locator: str  # typed, human-checkable anchor (§8.2)
    record_key: str | None = None  # ISM-1612 / APP 6 / G4 … fetchable by key
    page: int | None = None  # PDF true source page (1-based); None otherwise


@dataclass
class Chunk:
    chunk_id: str
    seq: int  # reading order within the document
    locator: str
    section_path: str
    kind: str
    record_key: str | None
    text: str
    token_count: int


@dataclass
class DocumentKB:
    doc_id: str
    short_name: str
    title: str
    version: str | None
    publisher: str | None
    source_url: str | None
    licence: str
    redistributable: bool
    format: str  # pdf | docx | xlsx | md | txt | rtf
    sha256: str
    page_count: int | None
    chunks: list[Chunk] = field(default_factory=list)
