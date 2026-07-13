# instrument/ — The DTA AI impact assessment tool, encoded as data

**Governs:** TECH_SPEC.md §9.3 (prompt/section ownership), §10 (rating engine input).
Source content: `AI_IMPACT_ASSESSMENT.md` (the markdown copy of the DTA tool —
**blocked on Tom**, see below).

This is deterministic transcription of the DTA instrument into machine-readable
form. It is the single encoded source both the specialist prompts and the
LLM-free rating engine read.

## Expected files (TECH_SPEC §2)

| File | Contents |
| --- | --- |
| `questions.json` | full question inventory, per section, **each with its specialist owner** |
| `guidance/<section>.md` | guidance text per section (licence-checked before commit) |
| `consequence_table.json` | consequence descriptors (guidance appendix) |
| `likelihood_table.json` | Table 1 likelihood descriptors |
| `risk_matrix.json` | **Table 2** consequence × likelihood → rating |

## Build-time assertions (CLAUDE.md §3, §8; TECH_SPEC §6.2)

- **Every instrument section maps to exactly one specialist owner** (1:1). Assert it at build time, or the ownership map has a silent hole.
- **Specialist write scope is structural:** each specialist writes only its owned DTA sections.

## Blocked on Tom (CLAUDE.md §8, TECH_SPEC §16)

- `AI_IMPACT_ASSESSMENT.md` is **not yet in the repo** — confirm the real filename and add it before transcription.
- The **Table 2 matrix** and consequence/likelihood descriptors are blocking for Stage 2 correctness. Build the engine against a clearly-marked scaffold matrix until the real values land; the encoding is untrustworthy until then.
