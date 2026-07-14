"""Ingestion orchestration + CLI (TECH_SPEC §8.6).

Per specialist folder, for each document: licence gate → structure-aware
extraction → structural chunking → write kb/<specialist>.sqlite + .index.json +
.manifest.json. Non-corpus files (*.meta.yml, README.md, placeholder.md,
.gitkeep) are skipped. Idempotent: the KB is rewritten from source each run
(CLAUDE.md §4). All compute is intended to run inside Actions runners, never on
Render (§8, unchanged from the inherited design).

Usage:
    python -m retrieval.ingest                 # all six specialists
    python -m retrieval.ingest privacy legal   # named specialists
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from retrieval.chunk import chunk_segments
from retrieval.db import write_kb
from retrieval.extract import extract, format_of
from retrieval.index_build import build_index
from retrieval.manifest import build_manifest
from retrieval.model import DocumentKB
from retrieval.sidecar import (
    LicenceGateError,
    Sidecar,
    enforce_licence_gate,
    load_licence_allow_list,
)

SPECIALISTS = ("it_security", "privacy", "ethics", "legal", "data_governance", "solution_architect")
_SKIP_SUFFIXES = (".meta.yml",)
_SKIP_NAMES = {"readme.md", "placeholder.md", ".gitkeep"}
_SLUG = re.compile(r"[^a-z0-9]+")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "instrument" / "risk_matrix.json").is_file():
            return parent
    raise RuntimeError("repo root (with instrument/) not found")


def _slug(name: str) -> str:
    stem = name
    # collapse doubled/real extensions: strip the final known suffix repeatedly
    stem = re.sub(r"\.(pdf|docx|xlsx|md|markdown|txt|rtf)$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\.(pdf|docx|xlsx|md|markdown|txt|rtf)$", "", stem, flags=re.IGNORECASE)
    return _SLUG.sub("-", stem.lower()).strip("-") or "doc"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _is_corpus_doc(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.name.lower() in _SKIP_NAMES:
        return False
    if any(path.name.endswith(s) for s in _SKIP_SUFFIXES):
        return False
    if path.name.startswith("."):
        return False
    return True


def _page_count(path: Path, fmt: str) -> int | None:
    if fmt != "pdf":
        return None
    import fitz

    with fitz.open(path) as doc:
        return doc.page_count


def ingest_specialist(
    specialist: str,
    repo_root: Path,
    chunk_min: int,
    chunk_max: int,
    index_max_tokens: int,
) -> dict:
    corpus_dir = repo_root / "corpus" / specialist
    kb_dir = repo_root / "kb"
    config_dir = repo_root / "config"
    if not corpus_dir.is_dir():
        raise FileNotFoundError(f"corpus folder missing: {corpus_dir}")

    allow_list = load_licence_allow_list(config_dir)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    documents: list[DocumentKB] = []
    seen_slugs: set[str] = set()
    seen_short_names: set[str] = set()

    for path in sorted(corpus_dir.iterdir()):
        if not _is_corpus_doc(path):
            continue
        fmt = format_of(path)
        sidecar: Sidecar = Sidecar.load(path)
        enforce_licence_gate(sidecar, allow_list, path)  # raises LicenceGateError

        if sidecar.short_name in seen_short_names:
            raise ValueError(
                f"Duplicate short_name {sidecar.short_name!r} within {specialist} — "
                f"short_name is the citation key and must be unique per specialist (§8.3)."
            )
        seen_short_names.add(sidecar.short_name)

        doc_id = _slug(path.name)
        while doc_id in seen_slugs:
            doc_id += "-x"
        seen_slugs.add(doc_id)

        segments = extract(path, fmt)
        chunks = chunk_segments(doc_id, segments, chunk_min, chunk_max)
        documents.append(
            DocumentKB(
                doc_id=doc_id,
                short_name=sidecar.short_name,
                title=sidecar.title,
                version=sidecar.version,
                publisher=sidecar.publisher,
                source_url=sidecar.source_url,
                licence=sidecar.licence,
                redistributable=sidecar.redistributable,
                format=fmt,
                sha256=_sha256_file(path),
                page_count=_page_count(path, fmt),
                chunks=chunks,
            )
        )

    sqlite_path = kb_dir / f"{specialist}.sqlite"
    index_path = kb_dir / f"{specialist}.index.json"
    manifest_path = kb_dir / f"{specialist}.manifest.json"

    write_kb(sqlite_path, documents, generated_at)
    index = build_index(specialist, documents, generated_at, index_max_tokens)
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest = build_manifest(
        specialist,
        documents,
        sqlite_path,
        index_path,
        repo_root,
        chunk_min,
        chunk_max,
        generated_at,
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "specialist": specialist,
        "documents": len(documents),
        "chunks": sum(len(d.chunks) for d in documents),
        "sqlite": str(sqlite_path),
        "index_tokens": index.get("index_tokens_estimate"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest specialist corpora into KBs (TECH_SPEC §8)."
    )
    parser.add_argument(
        "specialists", nargs="*", default=None, help="specialists to ingest (default: all)"
    )
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    cfg = yaml.safe_load((repo_root / "config" / "retrieval.yml").read_text(encoding="utf-8"))
    chunk_min = cfg["chunking"]["target_tokens_min"]
    chunk_max = cfg["chunking"]["target_tokens_max"]
    index_max = cfg["index"]["max_tokens"]

    targets = args.specialists or list(SPECIALISTS)
    unknown = [s for s in targets if s not in SPECIALISTS]
    if unknown:
        parser.error(f"unknown specialist(s): {unknown}; expected {list(SPECIALISTS)}")

    exit_code = 0
    for specialist in targets:
        try:
            summary = ingest_specialist(specialist, repo_root, chunk_min, chunk_max, index_max)
            print(
                f"[{specialist}] {summary['documents']} docs, {summary['chunks']} chunks, "
                f"index ~{summary['index_tokens']} tokens -> {summary['sqlite']}"
            )
        except LicenceGateError as exc:
            print(f"[{specialist}] FAILED: {exc}", file=sys.stderr)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
