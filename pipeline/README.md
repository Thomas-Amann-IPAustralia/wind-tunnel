# pipeline/ — Governance pipeline (runs in GitHub Actions)

The multi-agent assessment. Triggered by `workflow_dispatch`
(`.github/workflows/governance.yml`), commits all state back to the repo with
the built-in Actions token after every stage.

**Governs:** TECH_SPEC.md §5 (state machine), §6 (`status.json`), §8–§13.

## Expected modules (TECH_SPEC §2)

| Path | Role |
| --- | --- |
| `run.py` | entrypoint: load `run.json`, route to current stage |
| `stages/` | one module per state (§5) |
| `agents/` | agent runners (prompt + model call + output parse) |
| `retrieval/` | KB query: BM25 + cosine + optional rerank (§8) |
| `rating/` | **deterministic rating engine (§10) — importable, no LLM, unit-tested** |
| `reviewer/` | coverage + coherence protocol (§11) |
| `assembly/` | nbformat notebook + nbconvert HTML (§12) |
| `status.py` | `status.json` projection + event-log append (§6) |
| `gemini.py` | provider wrapper: backoff, token accounting (§13) |
| `statefile.py` | `run.json` read/write, checkpoint commit |

## Invariants this package must not break (CLAUDE.md §3)

- **Models argue, code computes.** LLMs emit consequence + likelihood + rationale only; every rating is computed by `rating/` from the instrument's Table 2 + highest-wins. No LLM ever emits a rating.
- **`run.json` is authoritative; `status.json` is a derived projection.** Resume from `run.json` only.
- **One poll fully determines visible state.** `status.json` `nodes` is a whole-graph map on every write; the event log is append-only with stable ids; a `heartbeat` always exists.
- **Idempotence is the resume model.** Every stage checks whether its committed checkpoint outputs already exist before redoing work (§5.3).

`rating/` is deliberately self-contained and LLM-free so it can be unit-tested
in isolation and imported by both the threshold and residual-rating stages.

Python 3.11, `uv`, ruff, pytest — see `pyproject.toml`.
