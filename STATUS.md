# Build status

## Current stage

**Stage 0 — Foundations** (PROJECT_BRIEF.md §9).

Scope: single-repo scaffold (TECH_SPEC §2), run-state model + run codes,
ingestion pipeline, one populated specialist KB end-to-end.

**Exit test:** a retrieval query returns page-cited chunks from a real corpus
doc. *Not yet met* — no corpus, KB, or retrieval code exists yet.

## Done

- **Repo scaffold** matching TECH_SPEC §2 — every directory in the layout now
  exists with a `README.md` (structural dirs) or `.gitkeep` (code leaves)
  pointing to its governing tech-spec section.
- **`outline.md` moved to `templates/outline.md`** — the outline contract's
  home per TECH_SPEC §2 / §7.1 (it was loose at repo root). Header comment and
  section registry unchanged.
- **Committed non-secret config** (CLAUDE.md §6, TECH_SPEC §13):
  - `config/models.yml` — tier→role mapping transcribed from TECH_SPEC §13
    (decided); exact Gemini ids left as `TODO(Tom)` placeholders.
  - `config/retrieval.yml` — scaffold: embedding model, top-k, BM25/cosine
    fusion weights, rerank off.
  - `config/budgets.yml` — per-stage call budgets + `expected_range_seconds`
    from the §13 worked example.
- **`prompts/manifest.yml`** — empty registry (`prompts: {}`) with the role list
  to author and the shape to follow (TECH_SPEC §9).
- **`pyproject.toml` for `backend/` and `pipeline/`** — Python 3.11, ruff +
  pytest config, empty pinned deps (conventions locked per CLAUDE.md §4).
- **`.gitignore`** — keeps env files and build cruft out; explicitly does *not*
  ignore `runs/` (durable store) or `kb/*.sqlite`.
- **`README.md`** — public-facing: what Windtunnel is, the usage warning,
  architecture, repo map, and orientation pointers.
- **`STATUS.md`** — this ledger (created; CLAUDE.md §7).
- **`CLAUDE.md`** updated with a "Repo state (first instance)" note so the next
  instance knows the scaffold exists.

## In progress / handoff notes

Nothing left mid-flight. The scaffold is directories + placeholders only — **no
executable code has been written yet.** Suggested next concrete steps toward the
Stage 0 exit test, in dependency order:

1. **Instrument encoding** (`instrument/*.json`) — deterministic transcription
   from `AI_IMPACT_ASSESSMENT.md` (**blocked on Tom**, see below). Assert at
   build time that every section maps to exactly one specialist owner
   (TECH_SPEC §6.2). A legitimate early task once the source doc lands.
2. **Rating engine** (`pipeline/rating/`) — LLM-free, unit-tested, built against
   a clearly-marked scaffold Table 2 until real values arrive (TECH_SPEC §10, §16).
3. **KB schema + ingestion** (`pipeline/retrieval/`, `.github/workflows/ingestion.yml`)
   with the licence hard-gate (TECH_SPEC §8) — needs at least one cleared corpus
   doc to exercise the exit test.
4. **Run identity + run-state** (`backend/`, `pipeline/statefile.py`) — run codes
   (TECH_SPEC §3), `run.json` / `status.json` (§4, §6).

Ordering rationale: 2 and the rating tests can proceed against scaffold data
while Tom supplies the instrument and corpus; 3 is what the Stage 0 exit test
actually measures, so it needs the corpus doc to truly pass.

## Decisions made (that the documents were silent on)

- **Directory-preservation convention:** structural directories get a
  `README.md` (which doubles as orientation); pure code-leaf directories that
  are otherwise empty get a `.gitkeep`. Chosen so git tracks the empty scaffold
  *and* the next instance finds a section pointer in each folder.
- **`.gitignore` allowlists `config/*.yml`** under the secrets block so the
  committed non-secret config is never accidentally ignored, while `.env*`
  stays excluded. `runs/` and `kb/*.sqlite` are deliberately **not** ignored —
  they are durable state / build outputs the repo is meant to hold.
- **Config files committed as scaffolds now** rather than deferred: they are
  non-secret and CLAUDE.md §6 names them as committed, so encoding the decided
  parts (tier→role, budget structure) and marking only the genuinely-open values
  `TODO(Tom)` gives the next instance a concrete starting point.

## Blocked on Tom

These block the *next* tasks, not this scaffold (CLAUDE.md §8, TECH_SPEC §16):

- **`AI_IMPACT_ASSESSMENT.md` is not in the repo.** CLAUDE.md §1 names it as a
  read; it is absent. Needed to encode `instrument/*.json`. Confirm the real
  filename and add it.
- **The DTA Table 2 matrix + consequence/likelihood descriptors** — blocking for
  Stage 2 rating correctness. Engine + tests can be built against a scaffold
  matrix but cannot be trusted until the real values land.
- **At least one licence-cleared corpus document** in `corpus/<specialist>/`
  with its `.meta.yml` — required for the **Stage 0 exit test**.
- **Exact Gemini model identifiers** in `config/models.yml` — blocks the first
  real LLM call.
- **Embedding model choice** (recommended `BAAI/bge-small-en-v1.5`) — ingestion
  and query must use the same one.

## Deploy-layer reminders (pinned in CLAUDE.md §9, not yet actioned)

Not blocking now, but they bite the moment anyone deploys: Render auto-deploy
OFF or watch-scoped to `backend/**`; SPA path-aware with hash routing and a
path-filtered `pages.yml`; backend commits via the GitHub Contents/Git-Data API,
not `git push`.
