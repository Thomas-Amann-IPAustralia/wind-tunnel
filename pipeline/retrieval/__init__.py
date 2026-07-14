"""pipeline.retrieval — KB ingestion and the fetch/search retrieval loop (TECH_SPEC §8).

Ingestion (Actions-side): `python -m retrieval.ingest` builds, per specialist,
kb/<specialist>.sqlite + .index.json + .manifest.json from corpus/<specialist>/.

Retrieval (specialist-side): `KB(path).fetch(refs)` / `.search(query, k)` return
RetrievedChunks carrying (short_name, locator, text) for citation (§8.1, §9.4).
"""

from retrieval.retrieve import KB, RetrievedChunk

__all__ = ["KB", "RetrievedChunk"]
