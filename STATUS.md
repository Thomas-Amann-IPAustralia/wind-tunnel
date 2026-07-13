# Build status

## Current stage

**Stage 0 — Foundations** (PROJECT_BRIEF.md §9).

Scope: single-repo scaffold (TECH_SPEC §2), run-state model + run codes,
ingestion pipeline, one populated specialist KB end-to-end.

**Exit test:** a retrieval query returns page-cited chunks from a real corpus
doc. *Not yet met* — no corpus, KB, or retrieval code exists yet. The **only**
remaining external blocker for this test is one licence-cleared corpus document
(+ the embedding-model pin); everything else it needs is code we can now write.

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
- **Instrument source docs have landed** (previously "Blocked on Tom"):
  `instrument/guidance/AI_impact_assessment_tool.md` (the DTA tool, 1606 lines)
  and `instrument/guidance/Guidance_AI_impact_assessment_tool.md` (1175 lines).
  These are the source content for encoding `instrument/*.json` (TECH_SPEC §9.3,
  §10.1). Critically, they contain **Table 1 (likelihood scale)** and a
  **complete, fully-populated 5×5 Table 2 (risk matrix)** at
  `AI_impact_assessment_tool.md` lines 449–467, plus the eight risk sections
  3.1–3.8, the overall 3.9, and per-section consequence descriptors. This
  unblocks instrument encoding and the rating engine against **real** values,
  not a scaffold matrix.

## In progress / handoff notes

Nothing left mid-flight. The scaffold is directories + placeholders only — **no
executable code has been written yet.** The instrument source and Table 2 having
landed mean the LLM-free critical path is now fully unblocked. Suggested next
concrete steps toward the Stage 0 exit test, in dependency order:

1. **Instrument encoding** (`instrument/*.json`) — deterministic transcription
   from `instrument/guidance/AI_impact_assessment_tool.md` (**now in repo**).
   Assert at build time that every section maps to exactly one specialist owner
   (TECH_SPEC §6.2 table). This is startable today.
2. **Rating engine** (`pipeline/rating/`) — LLM-free, unit-tested, now buildable
   against the **real** Table 2 matrix (lines 461–467), not a scaffold
   (TECH_SPEC §10). Highest-value work available now; instrument fidelity is the
   thing CLAUDE.md §2 says never to compromise.
3. **KB schema + ingestion** (`pipeline/retrieval/`, `.github/workflows/ingestion.yml`)
   with the licence hard-gate (TECH_SPEC §8) — code is startable now; the exit
   test itself still needs ≥1 cleared corpus doc + the embedding-model pin.
4. **Run identity + run-state** (`backend/`, `pipeline/statefile.py`) — run codes
   (TECH_SPEC §3), `run.json` / `status.json` (§4, §6).

Ordering rationale: 1, 2, and 4 are pure code against material already in the
repo — start now. 3's code can be written now too, but its exit-test pass waits
on Tom's corpus doc, which is the sole remaining external gate for Stage 0.

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

Resolved since the last update (no longer blocking):

- ~~`AI_IMPACT_ASSESSMENT.md` is not in the repo.~~ **Landed** as
  `instrument/guidance/AI_impact_assessment_tool.md` (+ its guidance companion).
  Filename differs from the CLAUDE.md §1 reference; the two guidance files are
  the canonical source now.
- ~~The DTA Table 2 matrix + descriptors are missing.~~ **Present and complete**
  in that doc (Table 1 + full 5×5 Table 2 + per-section consequence descriptors).
  The rating engine can be trusted against these values.

Still blocked on Tom (CLAUDE.md §8, TECH_SPEC §16):

- **At least one licence-cleared corpus document** in `corpus/<specialist>/`
  with its sidecar `<doc>.meta.yml` — required for the **Stage 0 exit test**, and
  now the *single* external gate on it. `corpus/` currently holds only its
  README. See "What a corpus doc must be" below.
- **Embedding model choice** (recommended `BAAI/bge-small-en-v1.5`, 384-dim) —
  ingestion and query must use the **same** one; asserted equal at run start
  (TECH_SPEC §8.3). Pin it in `config/retrieval.yml`. Gates ingestion, and so
  the Stage 0 exit test, alongside the corpus doc.
- **Exact Gemini model identifiers** in `config/models.yml` — blocks the first
  real *LLM* call (Stage 1+), not the LLM-free Stage 0 critical-path work.

### What a corpus doc must be (TECH_SPEC §8.4, §8.1)

For the Stage 0 exit test, **one** document for **any one** of the six
specialists is enough. Each corpus entry Tom supplies is two files in
`corpus/<specialist>/`, where `<specialist>` is one of:
`it_security`, `privacy`, `ethics`, `legal`, `data_governance`,
`solution_architect` (TECH_SPEC §6.2).

1. **The source document** — PDF preferred (HTML/MD/TXT also supported, with
   synthetic page anchoring). Must carry **true page numbers** — page-level
   citations are only as good as the extraction (PROJECT_BRIEF §10).
2. **A sidecar `<doc>.meta.yml`** with: `short_name` (citation key, e.g. `ISM` →
   renders `(ISM, p.112)`), `version`, `licence`, `redistributable: true`,
   `source_url`.

**The licence gate is hard and non-negotiable (CLAUDE.md §3).** The repo is
public and every chunk republishes source text, so ingestion **fails the build
loudly** unless `redistributable: true` **and** `licence` is in the config
allow-list (Commonwealth CC-BY, OWASP terms, and similar cleared licences).
Pre-cleared candidates that also map cleanly to specialists: the **ISM /
Essential Eight** (Commonwealth CC-BY) → `it_security`; **OAIC APP guidelines**
→ `privacy`; **OWASP** material → `it_security`. Anything not obviously CC-BY /
OWASP must be licence-verified before it goes in — there is no exception.

## Deploy-layer reminders (pinned in CLAUDE.md §9, not yet actioned)

Not blocking now, but they bite the moment anyone deploys: Render auto-deploy
OFF or watch-scoped to `backend/**`; SPA path-aware with hash routing and a
path-filtered `pages.yml`; backend commits via the GitHub Contents/Git-Data API,
not `git push`.
