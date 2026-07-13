# prompts/ — Versioned per-agent system prompts

**Governs:** TECH_SPEC.md §9 (prompt architecture).

```
prompts/
├─ manifest.yml        # role → current prompt file → model role
└─ <role>.v<N>.md      # one versioned prompt per agent role
```

## Rules

- Prompts are **versioned** (`.v<N>.md`); `manifest.yml` maps each role to its current prompt file and its model role (which resolves through `config/models.yml`).
- **Untrusted-content discipline** (invariant — CLAUDE.md §3): every agent that touches user text must delimit it as untrusted data (TECH_SPEC §9.2).
- **Specialist write scope is structural**: a specialist prompt owns only its DTA sections (TECH_SPEC §9.3).
- **No LLM emits a rating** — specialist/generalist prompts produce consequence + likelihood + rationale only (§10).
