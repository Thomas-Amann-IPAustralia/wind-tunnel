# Windtunnel

*Test the design under load before you build the aircraft.*

Windtunnel takes a public servant's loose idea for an AI solution, sharpens it
through a co-design **Brainstorm** phase, then stress-tests it through a
multi-agent **Governance** phase built directly on the Australian Government's
*AI impact assessment tool* (DTA, v1.0) — producing a substantially complete
draft impact assessment as a Jupyter notebook (the source of record) and a
rendered HTML report (the thing you hand to subject matter experts).

It compresses the distance between "I have an idea" and "here is a well-argued
draft assessment my SMEs can review" from weeks to hours. Built as an entry in a
competition for Australian public servants: a demonstration system that must
behave like a serious one.

> **This output is a draft for SME and assessing-officer review — never an
> approval.** It is not legal advice, does not authorise any AI use case, and
> does not replace the assessing, approving, or accountable roles defined in the
> AI policy.

## ⚠️ Usage warning — read before submitting anything

Everything you submit or that the system generates is stored in a **public**
GitHub repository and is **world-readable**. There is no authentication. The
sensitivity ceiling is **OFFICIAL** — do **not** enter OFFICIAL: Sensitive
information, security-classified information, or personally identifiable
information.

## How it works

Two phases around one durable store — the repository itself.

1. **Brainstorm** (interactive, on the backend): an interviewer sharpens the
   idea into a structured **outline**, optionally with an HTML proof-of-concept
   and an information-flow map. "A lens coming into focus."
2. **Governance** (multi-agent, in GitHub Actions): the outline is stress-tested
   against the DTA instrument — generalists and a reconciler for the **threshold**
   assessment, then a **specialist college**, a question checkpoint, a solution-
   architect appendix, and an adjudicating reviewer for the **full** assessment.
   A deterministic engine computes every risk rating; **models argue, code
   computes.**

A live transparency animation makes the wait legible, and every run is
resumable from its run code (e.g. `WT-7K3D-Q2`) because the repo — not any
process's memory — is the system of record.

## Architecture at a glance

| Component | Runtime | Home | Role |
| --- | --- | --- | --- |
| **SPA** | React / Vite | GitHub Pages | The whole UI; polls run status. |
| **Brainstorm backend** | Python / FastAPI | Render | Runs Brainstorm, issues run codes, triggers Governance. |
| **Governance pipeline** | Python | GitHub Actions | The multi-agent assessment; commits state back to the repo. |
| **The repository** | Git | this public repo | The single durable store and public audit trail. |

Nothing holds state in memory it cannot rebuild from the repository. See
`TECH_SPEC.md` §1.

## Repository layout

```
frontend/     React/Vite SPA (GitHub Pages)          — DESIGN_BRIEF.md, TECH_SPEC §6–7
backend/      FastAPI Brainstorm backend (Render)    — TECH_SPEC §7
pipeline/     Governance pipeline (GitHub Actions)   — TECH_SPEC §5, §6, §8–13
  rating/     deterministic, LLM-free rating engine  — TECH_SPEC §10
prompts/      versioned per-agent system prompts      — TECH_SPEC §9
templates/    outline.md — the concept's contract     — TECH_SPEC §7.1
instrument/   the DTA tool, encoded as data           — TECH_SPEC §9.3, §10
corpus/       source docs per specialist (licence-gated) — TECH_SPEC §8
kb/           built SQLite knowledge bases            — TECH_SPEC §8
config/       models / retrieval / budgets (committed) — TECH_SPEC §13
runs/         all run state, runs/<run-id>/           — TECH_SPEC §3, §4
fixtures/     golden-path + hand-worked rating cases  — TECH_SPEC §15
.github/workflows/  governance, ingestion, pages      — TECH_SPEC §2, CLAUDE.md §9
```

Each directory carries a `README.md` pointing to the tech-spec section that
governs it.

## Orientation — start here

The foundational documents are the source of truth; read them in this order:

1. **`PROJECT_BRIEF.md`** — what the product is and why (governs *intent*).
2. **`TECH_SPEC.md`** — the build: layout, state machine, contracts, engine
   (governs *the pipeline and the build*).
3. **`DESIGN_BRIEF.md`** — interface, transparency animation, report (governs
   *the interface and the report*).
4. **`instrument/guidance/AI_impact_assessment_tool.md`** (+ its companion
   guidance file) — the DTA instrument, the source content encoded into
   `instrument/`.

**Building on Windtunnel?** Read **`CLAUDE.md`** (working conventions, invariants,
handoff protocol) and **`STATUS.md`** (current build state) before writing code.

## Status

Early. Stage 0 — Foundations. Current state and next steps live in `STATUS.md`.

## Licence

See `LICENSE`. Corpus material is limited to genuinely redistributable sources;
ingestion enforces this as a hard gate.
