"""KB manifest (TECH_SPEC §8.5).

Records what a citation resolves against and what built the KB: chunker
parameters, the document list with versions and licence/redistributable flags,
sha256 of the sqlite and the index, and the build's git SHA + timestamp.
Provenance (§13) records the manifest version used for a run so a reader can
audit exactly which corpus produced which claim.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from retrieval.model import DocumentKB


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _git_sha(repo_root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover
        return None


def build_manifest(
    specialist: str,
    documents: list[DocumentKB],
    sqlite_path: Path,
    index_path: Path,
    repo_root: Path,
    chunk_min: int,
    chunk_max: int,
    generated_at: str,
) -> dict:
    return {
        "specialist": specialist,
        "generated_at": generated_at,
        "git_sha": _git_sha(repo_root),
        "chunker": {
            "target_tokens_min": chunk_min,
            "target_tokens_max": chunk_max,
            "overlap": "none (structural)",
            "token_estimator": "word+punct count (retrieval/tokens.py)",
        },
        "retrieval_model": "index + fetch/search (FTS5 BM25); no embeddings (TECH_SPEC §8.8)",
        "sqlite": {"path": sqlite_path.name, "sha256": _sha256_file(sqlite_path)},
        "index": {"path": index_path.name, "sha256": _sha256_file(index_path)},
        "document_count": len(documents),
        "documents": [
            {
                "doc_id": d.doc_id,
                "short_name": d.short_name,
                "title": d.title,
                "version": d.version,
                "publisher": d.publisher,
                "source_url": d.source_url,
                "licence": d.licence,
                "redistributable": d.redistributable,
                "format": d.format,
                "sha256": d.sha256,
                "page_count": d.page_count,
                "chunk_count": len(d.chunks),
            }
            for d in documents
        ],
    }
