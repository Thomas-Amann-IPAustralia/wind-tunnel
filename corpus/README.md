# corpus/ — Source documents, per specialist

**Governs:** TECH_SPEC.md §8 (KB, index + ingestion). Licence gate: CLAUDE.md §3;
PROJECT_BRIEF.md §10.

Source documents that get chunked along their own structure and ingested into
the specialist KBs under `kb/` (TECH_SPEC §8 — index + fetch retrieval, revised
July 2026). Laid out one directory per specialist:

```
corpus/
└─ <specialist>/
   ├─ <doc>.pdf|docx|xlsx|md|txt|rtf
   └─ <doc>.<ext>.meta.yml   # sidecar — see template below
```

Ingestion skips non-corpus files (`*.meta.yml`, `README.md`, `placeholder.md`);
the `placeholder.md` files can be deleted once a folder holds real documents.

## Sidecar template (`<exact document filename>.meta.yml`)

One sidecar per document, named after the full document filename, e.g.
`Information security manual (June 2026).pdf.meta.yml`:

```yaml
short_name: ISM             # citation key → renders [ISM, p.112]
title: Information security manual
version: June 2026          # edition / compilation date as printed on the doc
publisher: Australian Signals Directorate
source_url: https://…       # where the document was obtained
licence: CC-BY-4.0          # must be on the ingestion allow-list
redistributable: true       # the hard gate — verify before setting (see below)
```

These seven fields are all a sidecar carries. Retrieval needs nothing else:
structure detection (pages, heading/legislative styles, sheet layout) is
automatic at ingestion (TECH_SPEC §8.6–8.7).

## The licence flag is a hard gate (invariant — CLAUDE.md §3)

The repo is public, so every corpus document is republished twice — as source
and as chunked text inside the KBs. **Ingestion refuses any document not cleared
as publicly redistributable.** Commonwealth CC-BY material and OWASP are fine;
verify anything else before adding it. There is no exception.

Each `.meta.yml` must carry the `redistributable` flag that `ingestion.yml`
checks. True source **locators** must survive chunking — real page numbers for
PDFs; provision / heading / sheet-row anchors for formats without fixed pages
(TECH_SPEC §8.2) — because pinpoint citations are only as good as the extraction
(PROJECT_BRIEF.md §10).

## Blocked on Tom (CLAUDE.md §8)

The documents landed (July 2026). What remains is the **sidecars with verified
licences** — at least one cleared document is required for the **Stage 0 exit
test**: a fetch/search returns pinpoint-cited chunks from a real corpus doc.
