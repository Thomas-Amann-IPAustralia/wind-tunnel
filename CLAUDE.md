# CLAUDE.md — Windtunnel

You are a Claude Code instance building Windtunnel. You are almost certainly **not the first** and won't be the last. This file orients you: what to read, what's already decided, the conventions to hold, and how to leave the repo so the next instance can continue. Read it fully before writing code.

Windtunnel takes a public servant's loose idea for an AI solution, sharpens it through a co-design **Brainstorm** phase, then stress-tests it through a multi-agent **Governance** phase built on the DTA *AI impact assessment tool*, producing a draft impact assessment as a notebook and an HTML report. Read `PROJECT_BRIEF.md` §1 for the full framing.

> **Repo state — the first instance has run.** The single-repo scaffold
> (TECH_SPEC §2) now exists: every directory is present with a `README.md` or
> `.gitkeep`, `outline.md` has moved to its home at `templates/outline.md`, the
> committed non-secret config lives under `config/`, and `README.md` +
> `STATUS.md` exist. **No executable code has been written yet.** Read
> `STATUS.md` next for exactly what's done, what's blocked on Tom, and the
> suggested next steps toward the Stage 0 exit test.

---

## 1. Read these first, in this order

1. **`PROJECT_BRIEF.md`** — what the product is and why; the decisions taken as fixed. Governs *intent*.
2. **`TECH_SPEC.md`** — the build: repo layout, state machine, data contracts, API, engine, prompts. Governs *the pipeline and the build*. This is your primary working document.
3. **`DESIGN_BRIEF.md`** — the interface, the transparency animation, and the report. Governs *the interface and the report*.
4. **`instrument/guidance/AI_impact_assessment_tool.md`** and its companion **`Guidance_AI_impact_assessment_tool.md`** — the DTA instrument itself (tool + guidance, including Table 1, Table 2 and the consequence appendix), the source content you encode into `instrument/*.json` and assess against. (Landed July 2026.)
5. **`templates/outline.md`** — the outline contract made concrete; pair it with `TECH_SPEC.md` §7.1.

Don't reread all four every session. Read this file, skim the brief, then go deep on the tech-spec sections your task touches — the section map in §5 below tells you which.

## 2. Precedence — when documents disagree

Promoted here from the tech spec's closing line because it is load-bearing across instances:

> **The project brief governs intent. The design brief governs the interface and the report. The tech spec governs the pipeline, the data contracts, and the build.**

If you find a genuine contradiction between documents (not just silence), the owning document above wins for its domain — and **fixing the contradiction in the losing document is part of your task**, not a thing to leave for later. Note it in the progress ledger (§7). If a document is simply silent on something, that is a decision to make and record, not a blocker to stop on. One overriding rule sits above all of this: the Governance phase is the heart of the product, and **citation quality and instrument fidelity are never traded for polish or speed.**

## 3. The invariants — things you must not quietly break

These are the load-bearing decisions the whole design rests on. Violating one to make a task easier is never the right call; if one seems to be in your way, record the tension in the ledger and work around it.

- **One public repo holds everything** — code, workflows, corpus, built KBs, and all run state under `runs/<run-id>/`. User submissions are world-readable by design; the usage warning discloses it. There is no second repo and no private store. (brief §3, tech spec §2)
- **Models argue, code computes.** LLMs output consequence + likelihood + rationale only. Every risk rating is computed deterministically by `pipeline/rating/` from the instrument's Table 2 + highest-wins. No LLM ever emits a rating, and no revision instruction may set one. (brief §5.1, tech spec §10, §5.8)
- **`run.json` is authoritative; `status.json` is a derived projection.** The pipeline resumes from `run.json` only. `status.json` is regenerated for the UI and must always be safe to recompute. Never resume from it. (tech spec §4, §6)
- **One poll fully determines visible state.** `status.json` `nodes` is a whole-graph map on every write; the event log is append-only with stable ids; a `heartbeat` always exists. The frontend may miss polls and must still render correctly. (tech spec §6)
- **The outline is the single source of truth for the concept.** Downstream artefacts regenerate from the amended outline, never patched independently. (brief §4, tech spec §7.1)
- **The licence flag is a hard gate.** Ingestion refuses any corpus document not cleared as publicly redistributable. The repo is public; there is no exception. (tech spec §8)
- **Untrusted-content discipline.** Every agent that touches user text delimits it as untrusted data. (tech spec §9.2)
- **Specialist write scope is structural.** Each specialist writes only its owned DTA sections; ownership is 1:1 and asserted at build time. (tech spec §6.2, §9.3)
- **Caps hold:** user revisions ≤2 per artefact; reviewer internal loop ≤2 cycles; specialist questions ≤3 each, one batched pause. (brief §7)

## 4. Engineering conventions

Decided here so instances don't diverge. If you have strong reason to change one, change it *everywhere* and record it in the ledger — never leave the repo in two styles.

- **Backend / pipeline:** Python **3.11**. Dependency management with a `pyproject.toml` per deployable (`backend/`, `pipeline/`) using **uv**; pinned. Format + lint with **ruff** (format and check). Tests with **pytest**; `pipeline/rating/` and the instrument encoding are the non-negotiable test targets (tech spec §15).
- **Frontend:** **TypeScript**, React + Vite. Lint with ESLint, format with Prettier. No CSS framework mandated by the tech spec; follow the design brief's type/token system (design §3) — implement the tokens as CSS custom properties, don't reach for a component kit that fights them.
- **No secrets in the repo, ever.** Not in code, not in committed config, not in a run directory. See §6. The repo is world-readable.
- **Commits between instances are the memory.** Small, coherent commits with messages that say what stage/task they advance. The repo *is* the shared state; treat commit hygiene as communication to the next instance.
- **Idempotence is the resume model.** Any stage must be safe to re-enter: check whether its checkpoint outputs already exist and are committed before redoing work (tech spec §5.3). Write code that assumes it may be run twice.

## 5. Where things live — task-to-section map

| If you're building… | Read | Code lands in |
| --- | --- | --- |
| Repo scaffold, run creation, run codes | tech spec §2, §3, §4 | `backend/`, `runs/` skeleton |
| Brainstorm interview + outline canvas | tech spec §7, §7.1; `templates/outline.md`; design §6 | `backend/brainstorm/`, `frontend/` |
| PoC / flow map generation | brief §4; tech spec §7; design §6.3–6.4 | `backend/brainstorm/` |
| KB schema + ingestion | tech spec §8 | `pipeline/retrieval/`, `.github/workflows/ingestion.yml` |
| Instrument encoding (`instrument/*.json`) | tech spec §9.3, §10.1 | `instrument/` |
| Rating engine | tech spec §10 | `pipeline/rating/` (LLM-free, unit-tested) |
| Pipeline state machine + resume | tech spec §5 | `pipeline/run.py`, `pipeline/stages/` |
| status.json + event vocabulary | tech spec §6 | `pipeline/status.py` |
| Threshold stage (generalists, reconciler) | tech spec §5.1, §6.2; design §7.4 | `pipeline/stages/`, `pipeline/agents/` |
| Full stage (specialists, checkpoint, architect) | tech spec §5.1; design §7.2–7.3 | `pipeline/stages/`, `pipeline/agents/` |
| Reviewer protocol | tech spec §11 | `pipeline/reviewer/` |
| User revision of the full assessment | tech spec §5.8 | `pipeline/stages/`, `backend/` |
| Notebook + HTML assembly | tech spec §12; design §8 | `pipeline/assembly/` |
| Transparency animation | design §7.2; tech spec §6 | `frontend/` |
| API endpoints | tech spec §7 | `backend/app.py` |

## 6. Configuration and secrets inventory

**Secrets** — never committed; held only where noted. The backend is the sole holder of the Gemini key and the PAT; neither ever reaches the SPA.

| Secret | Held as | Used by |
| --- | --- | --- |
| `GEMINI_API_KEY` | Render env var; GitHub Actions secret | Backend (brainstorm) and pipeline (governance) |
| `WINDTUNNEL_PAT` (fine-grained, contents:write, this repo only) | Render env var | Backend, to commit brainstorm state |
| Actions token (`GITHUB_TOKEN`) | Provided by Actions automatically | Pipeline, to commit run state — no PAT needed inside Actions |

**Non-secret config** — committed. `config/models.yml` (tier→role decided; exact Gemini ids pinned by Tom), `config/retrieval.yml`, `config/budgets.yml` (tech spec §13). Deployment identity the SPA needs — the backend base URL, the repo `owner/name`, the run-code alphabet — belongs in a committed `frontend/` config (e.g. a typed `config.ts`) and a pipeline constant, **not** hardcoded across files. One owner per fact.

**Environment the pieces assume:** SPA on GitHub Pages (project site, served from `/<repo>/`); backend on Render free tier (sleeps when idle — cold start ~60s, handled per tech spec §7); pipeline in GitHub Actions via `workflow_dispatch`.

## 7. The progress ledger — how instances hand off

**`STATUS.md` at the repo root is the running record of build state.** It is the first thing you read after this file and the last thing you update before you finish. If it doesn't exist yet, you are early — create it. Keep it honest and current; it is how the next instance knows what you did.

Structure it as:

```
# Build status

## Current stage
Stage N (per PROJECT_BRIEF.md §9). One line on what "done" means here (the exit test).

## Done
- Bullet per completed, committed, working piece — with the tech-spec section it satisfies.

## In progress / handoff notes
- What you were mid-way through, where it is, and the next concrete step.
- Anything a fresh instance would otherwise have to rediscover.

## Decisions made (that the documents were silent on)
- Decision + one-line reason. These accrete; don't delete them.

## Blocked on Tom
- Items from the "Open items for Tom" lists that are actually blocking now (see §8).
```

Update `STATUS.md` in the **same commit** as the work it describes, so state and record never drift. Don't narrate routine progress anywhere else — the ledger is the single place.

## 8. What only Tom can supply

These come from outside the documents. Scaffold around them — none blocks starting — but flag any that block your *current* task in `STATUS.md`, and never invent a substitute silently.

- **The DTA instrument content** → encoded into `instrument/*.json`. **Landed July 2026** at `instrument/guidance/` (tool + guidance, including the real Table 1/Table 2 and the consequence appendix), so the deterministic transcription is an open early task, not a blocked one. **Assert at build time that every instrument section maps to exactly one specialist owner (tech spec §6.2), or the ownership map has a silent hole.** The rating engine and its tests build against the real Table 2 from the start; the scaffold-matrix contingency (tech spec §16) is obsolete.
- **`.meta.yml` sidecars with verified licences** for the corpus documents (the documents themselves landed July 2026). At least one cleared document is needed for the Stage 0 exit test; the licence attestation is inherently Tom's.
- **Exact Gemini model identifiers** in `config/models.yml`. Blocks the first real LLM call, nothing before it.

Full lists: tech spec §16 and design §11.

## 9. Deploy-layer decisions — pinned here

Decided so no instance has to guess, and so the guesses don't diverge. They don't block Stage 0 but bite the moment you deploy.

- **Render auto-deploy is OFF (or watch-path-scoped to `backend/**`).** The pipeline commits to the repo every ~20s during a run; with default auto-deploy Render would restart the backend continuously and evict in-memory brainstorm sessions. Whoever first connects Render must disable auto-deploy or scope its watch paths. Record which, in `STATUS.md`.
- **The SPA is path-aware.** GitHub Pages project sites serve from `/<repo>/`, so Vite `base` is set accordingly and routing is **hash-based** (Pages has no server-side rewrites; the 404.html trick is the fallback if hash routing is ever dropped). The CORS origin on the backend is the resulting Pages URL.
- **A Pages deploy workflow exists and is path-filtered to `frontend/**`.** It is not in the tech spec's workflow list — add `.github/workflows/pages.yml`. Path-filter it, or every status-commit during a run triggers a needless frontend redeploy.
- **Mermaid → SVG renders client-side, not on Render.** `mermaid-cli` needs headless Chromium, a poor fit for a 512MB free-tier instance. The SPA renders the flow map with `mermaid.js` in-browser and posts the SVG back for commit; the pipeline's report diagrams, which run in Actions, may use the CLI there where Chromium is available.
- **The backend commits via the GitHub Contents / Git Data API, not a working-copy `git push`.** Render's disk is ephemeral and a working copy grows unboundedly as `runs/` and KBs accumulate; API commits keep the backend stateless. Reads also go through the Contents API (tech spec §7). Serialise writes per run directory; retry on non-fast-forward.

## 10. Working rhythm

Read this file → read `STATUS.md` → confirm the current stage and its exit test (brief §9) → go deep on the tech-spec sections for your task → build in small idempotent commits → update `STATUS.md` in the final commit. When a stage's exit test passes, say so plainly in the ledger; don't drift into the next stage's polish without noting the boundary. If you hit a genuine contradiction between documents, resolve it per §2, fix the losing document, and record it. Leave the repo the way you'd want to find it.
