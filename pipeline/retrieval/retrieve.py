"""The two-tool retrieval interface (TECH_SPEC §8.1).

A specialist drives its own KB with two deterministic, LLM-free tools:

    fetch(refs)      — refs are chunk ids, record keys (ISM-1612, APP 6, G4),
                       section paths, or locators; returns exactly those chunks.
    search(query, k) — FTS5 BM25 over the KB; the lexical backstop.

Every returned chunk is a `RetrievedChunk` carrying (short_name, locator, text) —
the citation is `(short_name, locator)` (§8.2, §9.4). The model can only cite what
it actually fetched. This module does no LLM work and never mutates the KB.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

_TERMS = re.compile(r"\w+")


@dataclass(frozen=True)
class RetrievedChunk:
    short_name: str
    locator: str
    text: str
    doc_id: str
    chunk_id: str
    section_path: str
    record_key: str | None
    kind: str

    @property
    def citation(self) -> str:
        """Rendered citation, e.g. '[ISM, p.112]' (design §8, TECH_SPEC §9.4)."""
        return f"[{self.short_name}, {self.locator}]"

    def as_ref(self) -> dict:
        """The `ref` payload for a `retrieval` event (TECH_SPEC §6.3)."""
        return {"doc": self.short_name, "locator": self.locator}


_SELECT = (
    "SELECT d.short_name, c.locator, c.text, c.doc_id, c.chunk_id, "
    "c.section_path, c.record_key, c.kind "
    "FROM chunks c JOIN documents d ON d.doc_id = c.doc_id"
)


class KB:
    """A read-only handle on one specialist's KB (kb/<specialist>.sqlite)."""

    def __init__(self, sqlite_path: Path):
        if not Path(sqlite_path).is_file():
            raise FileNotFoundError(
                f"KB not found: {sqlite_path}. Run `python -m retrieval.ingest`."
            )
        self._conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "KB":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _rows_to_chunks(self, rows) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                short_name=r["short_name"],
                locator=r["locator"],
                text=r["text"],
                doc_id=r["doc_id"],
                chunk_id=r["chunk_id"],
                section_path=r["section_path"] or "",
                record_key=r["record_key"],
                kind=r["kind"],
            )
            for r in rows
        ]

    def fetch(self, refs: list[str] | str) -> list[RetrievedChunk]:
        """Return chunks for the given refs, in the order requested. A ref
        resolves in priority order: exact chunk_id, then record_key, then exact
        section_path, then exact locator, then a section_path whose deepest
        heading matches. Unresolvable refs are simply absent from the result
        (visible to the caller as a gap — §8.1)."""
        if isinstance(refs, str):
            refs = [refs]
        out: list[RetrievedChunk] = []
        seen: set[str] = set()
        for ref in refs:
            rows = self._resolve_ref(ref)
            for c in self._rows_to_chunks(rows):
                if c.chunk_id not in seen:
                    seen.add(c.chunk_id)
                    out.append(c)
        return out

    def _resolve_ref(self, ref: str):
        cur = self._conn.execute(_SELECT + " WHERE c.chunk_id = ? ORDER BY c.seq", (ref,))
        rows = cur.fetchall()
        if rows:
            return rows
        for clause in ("c.record_key = ?", "c.section_path = ?", "c.locator = ?"):
            rows = self._conn.execute(
                _SELECT + f" WHERE {clause} ORDER BY c.seq", (ref,)
            ).fetchall()
            if rows:
                return rows
        # deepest-heading match: section_path ends with the requested heading
        like = f"%{ref.lstrip('§')}"
        return self._conn.execute(
            _SELECT + " WHERE c.section_path LIKE ? ORDER BY c.seq", (like,)
        ).fetchall()

    def search(self, query: str, k: int = 8) -> list[RetrievedChunk]:
        """FTS5 BM25 lexical search over the KB (§8.1). Query text is reduced to
        its word tokens and OR-combined, so arbitrary user text is a safe MATCH
        (FTS operators in the raw string can't leak through)."""
        terms = _TERMS.findall(query)
        if not terms:
            return []
        # Quote each term so FTS keywords that happen to appear as words (AND, OR,
        # NOT, NEAR) are matched literally, not parsed as operators.
        match = " OR ".join(f'"{t}"' for t in terms)
        rows = self._conn.execute(
            _SELECT + " JOIN chunks_fts f ON f.rowid = c.rowid "
            "WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?",
            (match, k),
        ).fetchall()
        return self._rows_to_chunks(rows)

    def documents(self) -> list[sqlite3.Row]:
        return self._conn.execute("SELECT * FROM documents ORDER BY short_name").fetchall()
