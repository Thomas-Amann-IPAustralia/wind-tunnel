# pipeline/rating/ — Deterministic rating engine (LLM-free)

**Governs:** TECH_SPEC.md §10. Invariant: CLAUDE.md §3 ("models argue, code computes").

This package computes every risk rating deterministically. LLMs supply only
`consequence`, `likelihood`, and `rationale`; this code maps them through the
instrument's **Table 2** (`instrument/risk_matrix.json`) and applies
**highest-wins** to produce category ratings (3.1–3.8) and the overall
rating (3.9). **No LLM ever emits a rating, and no revision instruction may set
one.**

## Rules

- **Importable, no LLM, no network.** Pure functions over the encoded instrument.
- **Unit-tested is non-negotiable** (TECH_SPEC §15). Hand-worked rating cases live in `fixtures/`; the Stage 2 exit test is that threshold output matches a hand-worked assessment's ratings *exactly*.
- Build the engine and tests against a **clearly-marked scaffold matrix** until Tom supplies the real Table 2 values; it cannot be trusted until the real values are encoded (CLAUDE.md §8, TECH_SPEC §16).
