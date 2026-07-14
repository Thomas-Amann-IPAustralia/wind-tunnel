"""KB SQLite schema + write (TECH_SPEC §8.3).

One SQLite file per specialist: a `documents` table (sidecar metadata + the
licence flag that gated ingestion), a `chunks` table (true source anchors), and
an FTS5 index for lexical BM25 search — the only search channel (no embeddings,
§8.8). The whole KB is rewritten atomically on ingest so the build is idempotent
(CLAUDE.md §4).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from retrieval.model import DocumentKB

SCHEMA = """
CREATE TABLE documents (
  doc_id        TEXT PRIMARY KEY,
  short_name    TEXT NOT NULL,
  title         TEXT NOT NULL,
  version       TEXT,
  publisher     TEXT,
  source_url    TEXT,
  licence       TEXT NOT NULL,
  redistributable INTEGER NOT NULL,
  format        TEXT NOT NULL,
  sha256        TEXT NOT NULL,
  page_count    INTEGER,
  ingested_at   TEXT NOT NULL
);

CREATE TABLE chunks (
  chunk_id      TEXT PRIMARY KEY,
  doc_id        TEXT NOT NULL REFERENCES documents(doc_id),
  seq           INTEGER NOT NULL,
  locator       TEXT NOT NULL,
  section_path  TEXT,
  kind          TEXT NOT NULL,
  record_key    TEXT,
  text          TEXT NOT NULL,
  token_count   INTEGER NOT NULL
);

CREATE INDEX idx_chunks_doc ON chunks(doc_id);
CREATE INDEX idx_chunks_record_key ON chunks(record_key);

CREATE VIRTUAL TABLE chunks_fts USING fts5(
  text, section_path, record_key, content='chunks', content_rowid='rowid'
);
"""

# Keep the FTS index in step with chunks (we only ever bulk-insert on rebuild,
# but the triggers make the contentless table correct and future-proof).
TRIGGERS = """
CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
  INSERT INTO chunks_fts(rowid, text, section_path, record_key)
  VALUES (new.rowid, new.text, new.section_path, new.record_key);
END;
CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, text, section_path, record_key)
  VALUES ('delete', old.rowid, old.text, old.section_path, old.record_key);
END;
"""


def write_kb(sqlite_path: Path, documents: list[DocumentKB], ingested_at: str) -> None:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    if sqlite_path.exists():
        sqlite_path.unlink()  # rewrite atomically-ish; idempotent build
    conn = sqlite3.connect(sqlite_path)
    try:
        conn.executescript(SCHEMA)
        conn.executescript(TRIGGERS)
        for doc in documents:
            conn.execute(
                "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    doc.doc_id,
                    doc.short_name,
                    doc.title,
                    doc.version,
                    doc.publisher,
                    doc.source_url,
                    doc.licence,
                    1 if doc.redistributable else 0,
                    doc.format,
                    doc.sha256,
                    doc.page_count,
                    ingested_at,
                ),
            )
            conn.executemany(
                "INSERT INTO chunks "
                "(chunk_id, doc_id, seq, locator, section_path, kind, record_key, text, token_count) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                [
                    (
                        c.chunk_id,
                        doc.doc_id,
                        c.seq,
                        c.locator,
                        c.section_path,
                        c.kind,
                        c.record_key,
                        c.text,
                        c.token_count,
                    )
                    for c in doc.chunks
                ],
            )
        conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('optimize')")
        conn.commit()
    finally:
        conn.close()
