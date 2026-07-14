# kb/ — Built knowledge bases, indexes + manifests

**Governs:** TECH_SPEC.md §8 (KB schema, index + ingestion).

Built SQLite KBs, their LLM-readable indexes, and their manifests, produced by
`.github/workflows/ingestion.yml` from `corpus/`. One triple per specialist:

```
kb/
├─ <specialist>.sqlite          # chunks + FTS5 (schema: TECH_SPEC §8.3)
├─ <specialist>.index.json      # the LLM-readable catalogue (TECH_SPEC §8.4)
└─ <specialist>.manifest.json   # what citations resolve against (TECH_SPEC §8.5)
```

(Or release-asset pointers if the built KBs are too large to commit directly —
TECH_SPEC §2, §14.)

## Notes

- **No embedding model.** Retrieval is index navigation + `fetch` + FTS5 BM25
  `search` (TECH_SPEC §8.1, decision record §8.8); specialists read the index
  and pull exactly the chunks they need.
- Chunks store **typed locators** — true source pages for PDFs; provision /
  heading / sheet-row anchors for formats without fixed pages (TECH_SPEC §8.2) —
  so retrieval returns pinpoint-cited chunks (the Stage 0 exit test;
  PROJECT_BRIEF.md §9, §10).
- These are build outputs — do not hand-edit; rebuild via ingestion.
