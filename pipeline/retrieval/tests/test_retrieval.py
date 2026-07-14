"""Ingestion + retrieval tests, incl. the Stage 0 exit test (TECH_SPEC §8).

The Stage 0 exit test (STATUS.md / PROJECT_BRIEF §9): "a fetch/search returns
pinpoint-cited chunks from a real corpus doc." `test_stage0_exit_real_corpus_md`
is that check, run against an actual markdown document in corpus/ (no network,
no LLM, deterministic). The remaining tests exercise each mechanism in isolation
on synthetic inputs so failures localise.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from retrieval.chunk import chunk_segments
from retrieval.db import write_kb
from retrieval.extract import _split_control_records, extract_md, format_of
from retrieval.model import DocumentKB, Segment
from retrieval.retrieve import KB
from retrieval.sidecar import (
    LicenceGateError,
    Sidecar,
    enforce_licence_gate,
)

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "instrument").is_dir())
CORPUS = REPO_ROOT / "corpus"
_NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_kb(tmp_path: Path, doc: DocumentKB) -> KB:
    sqlite_path = tmp_path / f"{doc.doc_id}.sqlite"
    write_kb(sqlite_path, [doc], _NOW)
    return KB(sqlite_path)


def _md_doc(tmp_path: Path, text: str, short_name: str = "Test Doc") -> DocumentKB:
    src = tmp_path / "doc.md"
    src.write_text(text, encoding="utf-8")
    segments = extract_md(src)
    chunks = chunk_segments("test-doc", segments, target_min=20, target_max=120)
    return DocumentKB(
        doc_id="test-doc",
        short_name=short_name,
        title="Test Document",
        version="v1",
        publisher="pub",
        source_url=None,
        licence="CC-BY-4.0",
        redistributable=True,
        format="md",
        sha256="deadbeef",
        page_count=None,
        chunks=chunks,
    )


SAMPLE_MD = """# Guidance on widgets

Intro paragraph about widgets and their general use in government.

## Storage of widgets

Widgets must be stored securely in an approved repository. Access is logged.

## Disposal of widgets

Dispose of widgets per the retention schedule. Keep an audit trail of disposal.
"""


# --- Stage 0 exit test (real corpus) -----------------------------------------


def test_stage0_exit_real_corpus_md(tmp_path):
    """Ingest a REAL corpus markdown document and prove fetch + search return
    pinpoint-cited chunks. This is the Stage 0 exit test."""
    md_files = sorted(
        f
        for f in CORPUS.glob("*/*.md")
        if f.name.lower() != "readme.md" and "placeholder" not in f.name.lower()
    )
    assert md_files, "expected at least one real markdown corpus document"
    src = md_files[0]
    sidecar = Sidecar.load(src)
    segments = extract_md(src)
    chunks = chunk_segments("real", segments, target_min=400, target_max=900)
    assert chunks, "real doc produced no chunks"

    doc = DocumentKB(
        doc_id="real",
        short_name=sidecar.short_name,
        title=sidecar.title,
        version=sidecar.version,
        publisher=sidecar.publisher,
        source_url=sidecar.source_url,
        licence=sidecar.licence,
        redistributable=sidecar.redistributable,
        format="md",
        sha256="x",
        page_count=None,
        chunks=chunks,
    )
    with _build_kb(tmp_path, doc) as kb:
        # search returns results, each with a resolvable citation
        hits = kb.search("artificial intelligence", k=5)
        assert hits, "search returned nothing on a real AI-topic document"
        for h in hits:
            assert h.short_name == sidecar.short_name
            assert h.locator  # a non-empty, human-checkable anchor
            assert h.text.strip()
            assert h.citation.startswith(f"[{sidecar.short_name}, ")
        # fetch round-trips the exact chunk id a search returned
        cid = hits[0].chunk_id
        refetched = kb.fetch([cid])
        assert len(refetched) == 1 and refetched[0].chunk_id == cid


# --- Markdown mechanics ------------------------------------------------------


def test_md_headings_become_locators(tmp_path):
    with _build_kb(tmp_path, _md_doc(tmp_path, SAMPLE_MD, short_name="Widgets")) as kb:
        hits = kb.search("dispose retention audit", k=3)
        assert hits
        top = hits[0]
        assert top.locator == "§Disposal of widgets"
        assert top.citation == "[Widgets, §Disposal of widgets]"
        assert "Guidance on widgets > Disposal of widgets" == top.section_path


def test_fetch_by_section_heading(tmp_path):
    with _build_kb(tmp_path, _md_doc(tmp_path, SAMPLE_MD)) as kb:
        got = kb.fetch(["§Storage of widgets"])
        assert got and all("Storage of widgets" in c.section_path for c in got)


def test_fetch_unknown_ref_is_silent_gap(tmp_path):
    with _build_kb(tmp_path, _md_doc(tmp_path, SAMPLE_MD)) as kb:
        assert kb.fetch(["no-such-ref"]) == []
        # a mix: the good ref resolves, the bad one is simply absent
        good = kb.search("widgets", k=1)[0].chunk_id
        mixed = kb.fetch([good, "no-such-ref"])
        assert [c.chunk_id for c in mixed] == [good]


# --- Licence hard gate -------------------------------------------------------


def _sidecar(**kw) -> Sidecar:
    base = dict(
        short_name="X",
        title="T",
        version=None,
        publisher=None,
        source_url=None,
        licence="CC-BY-4.0",
        redistributable=True,
        path=Path("x.meta.yml"),
    )
    base.update(kw)
    return Sidecar(**base)


def test_licence_gate_blocks_non_redistributable():
    with pytest.raises(LicenceGateError):
        enforce_licence_gate(_sidecar(redistributable=False), {"CC-BY-4.0"}, Path("d.pdf"))


def test_licence_gate_blocks_unlisted_licence():
    with pytest.raises(LicenceGateError):
        enforce_licence_gate(_sidecar(licence="All rights reserved"), {"CC-BY-4.0"}, Path("d.pdf"))


def test_licence_gate_passes_cleared_document():
    # no exception
    enforce_licence_gate(_sidecar(), {"CC-BY-4.0"}, Path("d.pdf"))


# --- Chunker invariants ------------------------------------------------------


def test_chunker_keeps_records_atomic_and_keyed():
    segs = [
        Segment(
            "Control: ISM-0001; do a thing.", "record", "S", "p.1", record_key="ISM-0001", page=1
        ),
        Segment(
            "Control: ISM-0002; do another.", "record", "S", "p.1", record_key="ISM-0002", page=1
        ),
    ]
    chunks = chunk_segments("d", segs, 400, 900)
    assert len(chunks) == 2
    assert {c.record_key for c in chunks} == {"ISM-0001", "ISM-0002"}
    assert all(c.kind == "record" for c in chunks)


def test_chunker_packs_small_prose_but_not_across_boundaries():
    segs = [
        Segment("First para here.", "prose", "A", "§A"),
        Segment("Second para here.", "prose", "A", "§A"),
        Segment("Different section para.", "prose", "B", "§B"),
    ]
    chunks = chunk_segments("d", segs, 5, 900)
    # the two A-paras pack together; B stays separate (never crosses the boundary)
    a_chunks = [c for c in chunks if c.section_path == "A"]
    b_chunks = [c for c in chunks if c.section_path == "B"]
    assert (
        len(a_chunks) == 1
        and "First para" in a_chunks[0].text
        and "Second para" in a_chunks[0].text
    )
    assert len(b_chunks) == 1 and b_chunks[0].locator == "§B"


def test_chunker_splits_oversized_prose_with_part_locator():
    long_text = " ".join(f"Sentence number {i} about the topic." for i in range(80))
    segs = [Segment(long_text, "prose", "A", "p.5", page=5)]
    chunks = chunk_segments("d", segs, 40, 80)
    assert len(chunks) > 1
    assert all(c.token_count <= 120 for c in chunks)  # bounded near the cap
    assert any("(pt " in c.locator for c in chunks)  # part suffix applied
    assert all(c.locator.startswith("p.5") for c in chunks)  # true page preserved


# --- Control-record detection (ISM-style) ------------------------------------


def test_split_control_records():
    seg = Segment(
        "Preamble text. Control: ISM-1234; Revision: 1; The control statement body. "
        "Control: ISM-5678; Revision: 2; Another control body.",
        "prose",
        "Hardening",
        "p.42",
        page=42,
    )
    out = _split_control_records([seg])
    records = [s for s in out if s.kind == "record"]
    assert [r.record_key for r in records] == ["ISM-1234", "ISM-5678"]
    assert all(r.locator == "p.42" for r in records)  # true page kept as locator
    assert any(s.kind == "prose" and "Preamble" in s.text for s in out)


# --- Search safety -----------------------------------------------------------


def test_search_is_injection_safe(tmp_path):
    with _build_kb(tmp_path, _md_doc(tmp_path, SAMPLE_MD)) as kb:
        # raw FTS5 operators in the query must not raise
        assert isinstance(kb.search('widgets AND (OR "unterminated', k=3), list)
        assert kb.search("", k=3) == []


# --- Format detection --------------------------------------------------------


def test_format_of_handles_doubled_extension():
    assert format_of(Path("The-new-machinery.pdf.pdf")) == "pdf"
    assert format_of(Path("x.markdown")) == "md"
    assert format_of(Path("y.DOCX")) == "docx"
