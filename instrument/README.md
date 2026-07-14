# instrument/ — The DTA AI impact assessment tool, encoded as data

**Governs:** TECH_SPEC.md §9.3 (prompt/section ownership), §10 (rating engine input).
Source content (in-repo since July 2026): `guidance/AI_impact_assessment_tool.md`
(the tool: questions, Table 1, Table 2) and `guidance/Guidance_AI_impact_assessment_tool.md`
(the guidance, including the risk-consequence appendix table).

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

## Status (July 2026)

- The source documents **landed** under `guidance/` — transcription into the
  `*.json` files above is an open task, no longer blocked on Tom.
- Transcribe Table 1 / Table 2 / the consequence appendix **verbatim from the
  in-repo source** (the real Table 2 differs from the conventional 5×5
  scaffold in TECH_SPEC §10.1); the rating engine's tests are hand-worked from
  the actual tool (TECH_SPEC §15).
