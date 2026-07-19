# Windtunnel

*Test the design under load before you build the aircraft.*

> **An Innovation Month 2026 (IM2026) entry.** Windtunnel is a demonstration
> system built for Innovation Month 2026 — *Ready or Not…*

<img src="frontend/src/img/ReadyOrNotColour.png" alt="Innovation Month 2026 — Ready or Not…" width="300">

Windtunnel takes a public servant's loose idea for an AI solution, sharpens it
through a co-design **Brainstorm** phase, then stress-tests it through a
multi-agent **Governance** phase built on the Australian Government's *AI impact
assessment tool* (DTA, v1.0) — producing a substantially complete draft impact
assessment as a notebook and a shareable HTML report. It compresses the distance
between *"I have an idea"* and *"here is a well-argued draft my SMEs can review"*
from weeks to hours.

> **📖 New here? Read [`SYSTEM_OVERVIEW.ipynb`](SYSTEM_OVERVIEW.ipynb).** It is a
> complete, plain-language, illustrated tour of how the whole system works — the
> phases, the agents, the interface, and the output — using one worked example
> throughout. This README is deliberately brief; the overview is where
> understanding lives.

## Two things to know before anything else

- **This output is a draft for SME and assessing-officer review — never an
  approval.** It is not legal advice, does not authorise any AI use case, and
  does not replace the assessing, approving, or accountable roles defined in the
  AI policy.
- **⚠️ Everything you submit or that the system generates is stored in a
  *public*, world-readable GitHub repository.** There is no authentication and no
  security accreditation. Do **not** enter classified, sensitive, or personally
  identifiable information — the rule is simply not to put in anything you
  wouldn't be comfortable seeing made public.

## How it works, in brief

Two phases around one durable store — the repository itself.

1. **Brainstorm** (interactive): an interviewer sharpens the idea into a
   structured **outline**, optionally with an HTML proof-of-concept and an
   information-flow map.
2. **Governance** (multi-agent): the outline is stress-tested against the DTA
   instrument — two generalists and a reconciler for the **threshold**
   assessment, then a **specialist college**, a question checkpoint, a
   solution-architect appendix, and an adjudicating reviewer for the **full**
   assessment. A deterministic engine computes every risk rating: **models argue,
   code computes.**

Every run is resumable from its run code (e.g. `WT-7K3D-Q2`) because the
repository — not any process's memory — is the system of record. The full story,
with annotated screenshots and diagrams, is in
[`SYSTEM_OVERVIEW.ipynb`](SYSTEM_OVERVIEW.ipynb).

## Repository layout

```
frontend/     React/Vite SPA (the whole UI, on GitHub Pages)
backend/      FastAPI Brainstorm backend (on Render)
pipeline/     Governance pipeline (in GitHub Actions)
  rating/     deterministic, LLM-free rating engine
prompts/      versioned per-agent system prompts
templates/    outline.md — the concept's contract
instrument/   the DTA tool, encoded as data
corpus/       source docs per specialist (licence-gated)
kb/           built knowledge bases
config/       models / retrieval / budgets
runs/         all run state, runs/<run-id>/
docs/         supporting assets (e.g. System Overview images)
.github/workflows/  governance, ingestion, pages
```

## Documentation

The foundational documents are the source of truth. In reading order:

1. **[`SYSTEM_OVERVIEW.ipynb`](SYSTEM_OVERVIEW.ipynb)** — the plain-language,
   illustrated tour (start here to understand the system).
2. **`PROJECT_BRIEF.md`** — what the product is and why (governs *intent*).
3. **`TECH_SPEC.md`** — the build: layout, state machine, contracts, engine
   (governs *the pipeline and the build*).
4. **`DESIGN_BRIEF.md`** — interface, transparency animation, report (governs
   *the interface and the report*).
5. **`instrument/guidance/`** — the DTA instrument itself, the source content
   encoded into `instrument/`.

**Building on Windtunnel?** Read **`CLAUDE.md`** (conventions, invariants,
handoff protocol) and **`STATUS.md`** (current build state) before writing code.

## Licence

See `LICENSE`. Corpus material is limited to genuinely redistributable sources;
ingestion enforces this as a hard gate.
