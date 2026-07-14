# Build status

## Current stage

**Stage 0 — Foundations** (PROJECT_BRIEF.md §9).

Scope: single-repo scaffold (TECH_SPEC §2), run-state model + run codes,
ingestion pipeline, one populated specialist KB end-to-end.

**Exit test:** a fetch/search returns pinpoint-cited chunks from a real corpus
doc. *Not yet met* — the corpus has landed, but the sidecars and the
ingestion/retrieval code don't exist yet.

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
  - `config/retrieval.yml` — rewritten July 2026 for the index+fetch model:
    chunking targets, index token budget, fetch caps, search top-k. No
    embedding model, fusion weights, or reranker (see Decisions).
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
- **Instrument source landed (Tom, July 2026)** —
  `instrument/guidance/AI_impact_assessment_tool.md` (the tool itself:
  questions, Table 1 likelihood scale, the real Table 2 risk matrix,
  per-section consequence tiers) and `Guidance_AI_impact_assessment_tool.md`
  (the guidance, including the risk-consequence appendix table). Encoding
  `instrument/*.json` is unblocked, and the rating engine can be built against
  the real Table 2 from the start — no scaffold matrix needed.
- **Corpus landed (Tom, July 2026)** — 106 documents across the six specialist
  folders, ~1.8M extractable tokens: it_security ~507K, ethics ~432K,
  privacy ~402K, legal ~220K, solution_architect ~163K (56 files, mostly the
  RAI pattern catalogue), data_governance ~73K. Formats: 58 docx / 37 pdf /
  12 md / 4 xlsx / 1 txt / 1 rtf. No `.meta.yml` sidecars yet.
- **Retrieval reevaluated against the real corpus; TECH_SPEC §8 rewritten**
  (this branch). The inherited embedding/hybrid design is replaced by an
  LLM-navigated structural index + `fetch`/`search` (FTS5 BM25) tool loop, and
  citations generalize from pages to typed locators. Documents updated
  together so none contradict (CLAUDE.md §2): TECH_SPEC (§2 layout, §6.3 event
  ref, §8 rewritten, §9.4, §13, §15, §16), PROJECT_BRIEF (framing, specialist
  contract, architecture table, Stage-0 exit test, citation-integrity risk),
  DESIGN_BRIEF (event table ref, report citation apparatus),
  `config/retrieval.yml`, `config/budgets.yml`, `corpus/README.md` (now carries
  the sidecar template), `kb/README.md`, CLAUDE.md §8.

## In progress / handoff notes

Nothing mid-flight. Next concrete steps toward the Stage 0 exit test, in
dependency order:

1. **Tom: `.meta.yml` sidecars** per the template in `corpus/README.md`,
   including licence verification (see Blocked on Tom).
2. **Instrument encoding** (`instrument/*.json`) — now unblocked: deterministic
   transcription from `instrument/guidance/*.md`, asserting at build time that
   every section maps to exactly one specialist owner (TECH_SPEC §6.2).
3. **Ingestion build** (`pipeline/retrieval/`, `.github/workflows/ingestion.yml`)
   to the revised TECH_SPEC §8: licence gate → structure-aware extraction
   (PyMuPDF for PDFs; docx style trees; xlsx normalization per §8.7) →
   structural chunking → index build → sqlite/index/manifest write. No
   embedding stack: deps stay small (pymupdf, openpyxl, pyyaml, stdlib sqlite3).
   The code can be written now; the licence gate needs sidecars to pass.
4. **Rating engine** (`pipeline/rating/`) — against the **real** Table 2 now in
   the repo (TECH_SPEC §10); the scaffold-matrix contingency is obsolete.

Corpus observations for whoever builds ingestion (from the July 2026 review):

- All 37 PDFs have a real text layer — no OCR needed. The ISM PDF renders its
  controls as `Control: ISM-XXXX; …` lines (regexable into `record` chunks);
  the Privacy Act and Archives Act compilations are docx with full legislative
  styles (`ActHead*`, `subsection`) — provision anchors come from the style tree.
- Spreadsheet headers are one or two rows with merged group headers (cloud
  controls matrix `Principles` sheet; the pattern-mapping workbook) —
  normalization per §8.7 must detect header depth and fill down groupings.
- The ADM Better Practice Guide appears twice: `legal/…March-2025.pdf` and
  `ethics/apo-nid306481.pdf` (an earlier edition of the same guide).
  Per-specialist KBs are independent so this works, but Tom may want to drop
  the stale copy or give them distinct `short_name`s + versions.
- `legal/Artificial-Intelligence-Guidance-May-2026.pdf` is the **UK Bar
  Standards Board's** guidance — Tom to confirm it's wanted alongside the AU
  material, or swap for an AU equivalent.
- `The-new-machinery-of-government…pdf.pdf` has a doubled extension; harmless
  (doc_id slugging normalizes it). `placeholder.md` files can be deleted as
  sidecars land.

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
- **Retrieval = LLM-navigated index + fetch/search; no embeddings** (July 2026,
  after reviewing the landed corpus; full record TECH_SPEC §8.8). The corpora
  are small (≤~507K tokens/specialist) and registry-shaped; an in-context index
  gives specialists corpus awareness (better synthesis than top-k snippets),
  visible rather than silent recall failures, and zero ML infra in the runners.
  Reversible by construction: a dense channel can be added additively if
  Stage-3 quality testing shows recall gaps.
- **Citations anchor to typed locators, not only pages** (TECH_SPEC §8.2) —
  two-thirds of the corpus (docx/xlsx/md) has no true pages. PDFs keep the
  true-page guarantee; legislation cites provisions; sheets cite row ranges or
  record keys. The brief's citation-integrity intent is unchanged.
- **Spreadsheets ingest as normalized sheets classified by shape** (TECH_SPEC
  §8.7): instructions → prose; registries → row-group markdown chunks with
  `record_key`s; boolean matrices → per-row records naming only meaningful cells.

## Blocked on Tom

These block the *next* tasks (CLAUDE.md §8, TECH_SPEC §16). The instrument
source and Table 1/Table 2 landed July 2026 (see Done) and are no longer here:

- **`.meta.yml` sidecars with verified licences** — template in
  `corpus/README.md`; at least one cleared doc unlocks the Stage 0 exit test.
  Commonwealth material (DTA, OAIC, ASD/ACSC, NAA, eSafety, the DDG strategy)
  is usually CC BY 4.0 — confirm each imprint page. **Verify before flagging
  redistributable:** the OECD paper (OECD terms, not CC), the two arXiv papers
  (author-chosen licences), the two AHRC reports, the two HTI/UTS reports, the
  CSIRO/Data61 report + the 50 pattern-catalogue extracts, the Creative
  Australia paper, the three court items (SC PN Gen 23, the GenAI practice-note
  txt, the Perry J speech rtf), the Indigenous data governance framework, and
  the UK BSB guidance. US NIST/CISA/NSA publications are public domain; OWASP
  is already on the allow-list.
- **Exact Gemini model identifiers** in `config/models.yml` — blocks the first
  real LLM call.

## Deploy-layer reminders (pinned in CLAUDE.md §9, not yet actioned)

Not blocking now, but they bite the moment anyone deploys: Render auto-deploy
OFF or watch-scoped to `backend/**`; SPA path-aware with hash routing and a
path-filtered `pages.yml`; backend commits via the GitHub Contents/Git-Data API,
not `git push`.
