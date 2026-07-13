# corpus/ — Source documents, per specialist

**Governs:** TECH_SPEC.md §8 (KB schema + ingestion). Licence gate: CLAUDE.md §3;
PROJECT_BRIEF.md §10.

Source documents that get chunked, embedded, and ingested into the specialist
KBs under `kb/`. Laid out one directory per specialist:

```
corpus/
└─ <specialist>/
   ├─ <doc>.pdf
   └─ <doc>.meta.yml   # short_name, version, licence, redistributable, source_url
```

## The licence flag is a hard gate (invariant — CLAUDE.md §3)

The repo is public, so every corpus document is republished twice — as source
and as chunked text inside the KBs. **Ingestion refuses any document not cleared
as publicly redistributable.** Commonwealth CC-BY material and OWASP are fine;
verify anything else before adding it. There is no exception.

Each `.meta.yml` must carry the `redistributable` flag that `ingestion.yml`
checks. True source **page numbers** must survive chunking — page-level
citations are only as good as the extraction (PROJECT_BRIEF.md §10).

## Blocked on Tom (CLAUDE.md §8)

At least **one licence-cleared corpus document** (with its `.meta.yml`) is
required for the **Stage 0 exit test**: a retrieval query returns page-cited
chunks from a real corpus doc. Easy to overlook; without it Stage 0 can't pass.
