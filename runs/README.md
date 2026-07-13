# runs/ — All run state (world-readable by design)

**Governs:** TECH_SPEC.md §3 (run identity), §4 (run-state schema), §5 (state machine).

Every run's durable state lives under `runs/<run-id>/`. The run code *is* the
run id (e.g. `WT-7K3D-Q2` → `runs/WT-7K3D-Q2/`) — there is no separate UUID, so
resume is a path lookup and the audit trail stays human-navigable.

## Two state files, different jobs (invariant — CLAUDE.md §3)

- **`run.json` is authoritative** — the state machine the pipeline reads to resume (§5.1).
- **`status.json` is a derived projection** for the UI (§6). The pipeline **never** resumes from it, and it must always be safe to recompute.

See TECH_SPEC §4 for the full `runs/<run-id>/` tree (`brainstorm/`,
`threshold/`, `full/`, `artefacts/`, `provenance.json`, …).

## World-readable by design (invariant — CLAUDE.md §3)

The repo is public; user submissions here are world-readable, disclosed in the
usage warning. There is no private store. **No secrets in a run directory, ever.**

This directory holds no committed run at scaffold time; runs are created by the
backend's first commit at run creation (§3, §4).
