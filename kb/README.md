# kb/ — Built knowledge bases + manifests

**Governs:** TECH_SPEC.md §8 (KB schema + ingestion).

Built SQLite KBs and their manifests, produced by
`.github/workflows/ingestion.yml` from `corpus/`. One pair per specialist:

```
kb/
├─ <specialist>.sqlite
└─ <specialist>.manifest.json
```

(Or release-asset pointers if the built KBs are too large to commit directly —
TECH_SPEC §2.)

## Notes

- **Embedding model** must be identical for ingestion and query (recommended `BAAI/bge-small-en-v1.5`; confirm with Tom — CLAUDE.md §8).
- Chunks store **true source page numbers** so retrieval returns page-cited chunks (the Stage 0 exit test; PROJECT_BRIEF.md §9, §10).
- These are build outputs — do not hand-edit; rebuild via ingestion.
