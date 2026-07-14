# Build status

## Current stage

**Stage 0 — Foundations** (PROJECT_BRIEF.md §9) — **exit test MET.**

Scope: single-repo scaffold (TECH_SPEC §2), run-state model + run codes,
ingestion pipeline, one populated specialist KB end-to-end.

**Exit test:** a fetch/search returns pinpoint-cited chunks from a real corpus
doc. **Met.** All six specialist KBs build from the real corpus
(`python -m retrieval.ingest`), and `KB.search`/`KB.fetch` return chunks carrying
`(short_name, locator)` citations — verified end-to-end against real documents in
`retrieval/tests/test_retrieval.py::test_stage0_exit_real_corpus_md`. Live
examples: `[ISM, p.17]` (true PDF page), `[Archives Act 1983, s 30A]` (legislative
provision), `[NAA AI Records Guidance, §Disposal of generative AI assistant
prompts and inputs]` (heading path), and `fetch("ISM-2002")` returns the exact
control by key. **Not yet built** (the Stage-0 line items that were about run
identity/state — carried into Stage 1): run-code creation, `run.json`/`status.json`
(TECH_SPEC §3–§6). The retrieval half of Stage 0 is complete; the run-state half
is the natural next pickup.

**Boundary note:** the rating engine + instrument encoding (a Stage 2 target) were
built now because they were unblocked, self-contained and testable — do not read
their presence as Stage 2 being underway. Stage 2's exit test (ratings match a
hand-worked assessment) is met *for the engine in isolation*; the generalists,
reconciler and the wiring that feed it do not exist yet.

## Done

- **Deterministic rating engine (`pipeline/rating/`) — the integrity core**
  (TECH_SPEC §10). LLM-free `rating(consequence, likelihood)` and
  `overall_rating(ratings)` load the instrument tables, validate inputs, and raise
  `RatingError` on any off-vocabulary label (loud failure, never silent). 12
  engine tests hand-worked from the **real** Table 2. **Key fidelity finding: the
  real Table 2 tops out at "High" — there is NO "Very high" tier**, and several
  cells differ from the conventional scaffold once shown in TECH_SPEC §10.1.
- **Instrument encoding (`instrument/*.json`)** — transcribed verbatim from
  `instrument/guidance/*.md` (TECH_SPEC §9.3, §10.1):
  - `likelihood_table.json` (Table 1), `risk_matrix.json` (Table 2, real cells),
    `consequence_table.json` (5-tier scale + per-section §3.1–3.8 descriptors).
  - `questions.json` — question inventory for the coverage checklist (§11.1) and
    specialist prompts (§9.3): verbatim prompts for §3 and §5–12.
  - `sections.json` — the ownership contract encoding §6.2; **asserts each
    full-assessment section maps to exactly one owner** (the 1:1 build-time check,
    CLAUDE.md §8), via `pipeline/tests/test_instrument.py`.
- **Ingestion + retrieval (`pipeline/retrieval/`) — Stage-0 exit path**
  (TECH_SPEC §8). Licence hard gate → structure-aware extraction (pdf/docx/xlsx/
  md/txt/rtf) → structural chunking (never crosses a boundary; no overlap) →
  sqlite (§8.3 schema + FTS5) + index (§8.4, budget-bounded coarsening ladder) +
  manifest (§8.5). Two-tool `fetch`/`search` interface (§8.1). No embeddings
  (§8.8) — stdlib `sqlite3`/FTS5 + one chunker. Format highlights: PDFs keep true
  pages; legislation cites provisions (`s 30A`) from the `ActHead`/`SubsectionHead`
  style tree; ISM controls are detected inline and made fetchable by key
  (`fetch("ISM-1612")`); spreadsheets emit keyed records. 42 retrieval tests pass.
- **`.github/workflows/ingestion.yml`** (TECH_SPEC §8.6) — `workflow_dispatch` +
  push-to-`corpus/**`; runs tests, ingests via `uv`, commits KBs back with the
  built-in `GITHUB_TOKEN`. Path-filtered.
- **Built KBs committed** (`kb/*.sqlite` + `.index.json` + `.manifest.json`, ~17 MB
  total) — the durable Stage-0 output (§8.5 "commit directly at this size"). Regen
  is idempotent from source.
- **`config/licences.yml`** — the ingestion licence allow-list (STATUS step 1,
  resolved): the gate keeps `licence ∈ allow_list` as defence-in-depth and
  enumerates the exact strings the 106 cleared sidecars carry.
- **Corpus `.meta.yml` sidecars authored — all 106 documents** (TECH_SPEC §8.6
  step 1, `corpus/README.md` template). One sidecar per document, seven fields
  each (`short_name`, `title`, `version`, `publisher`, `source_url`, `licence`,
  `redistributable`), named `<exact filename>.meta.yml`. `redistributable: true`
  on every file — **Tom (corpus owner) attested in-session that every document is
  cleared for use in the project**, discharging the licence-attestation that was
  Blocked-on-Tom. Metadata was researched per document (embedded docx/pdf/xlsx
  metadata + web verification); the ~50 CSIRO *Responsible AI Pattern Catalogue*
  entries under `solution_architect/` share provenance and are generated with
  `title`/`short_name` = pattern name. Validated: all parse as YAML, all seven
  fields present, `short_name` unique within each specialist (it is the citation
  key). Generator kept at `scratchpad/gen_sidecars.py` (not committed) and
  **asserts no document is left without a sidecar** — re-runnable/idempotent.
  This clears the licence hard gate's *input* for ingestion; see handoff notes
  for the licence-allow-list follow-up and the few best-effort fields.
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

The four dependency-ordered steps that stood between the scaffold and the Stage-0
exit test (licence config → instrument encoding → ingestion → rating engine) are
**all done** (see Done). Next concrete steps, in rough dependency order:

1. **Run identity + state (`backend/`, `runs/`, TECH_SPEC §3–§6)** — the other
   half of Stage 0/1: run-code creation, `run.json` (authoritative) and the
   derived `status.json` projection with the fixed node graph (§6.2) and the
   controlled event vocabulary (§6.3). Nothing here is blocked.
2. **Prompts (`prompts/*.md` + `manifest.yml`, TECH_SPEC §9)** — author the
   versioned role prompts. The instrument JSON now gives each generalist/specialist
   its owned question text, guidance, and (for §3) consequence/likelihood tables.
   Wrap all user text in the untrusted delimiter (§9.2). Prompt *content* is
   authorable now; the first real **call** is blocked on the Gemini ids.
3. **Threshold stage (`pipeline/stages/`, `pipeline/agents/`)** — two generalists
   → reconciler → feed the rating engine (already built) → `divergence.json`.
   This is the first place the rating engine is wired in (§5.1, §10.3).
4. **Specialist retrieval loop wiring (`pipeline/agents/`)** — give each specialist
   its `kb/<specialist>.index.json` in-context + the `KB.fetch`/`KB.search` tools
   (`retrieval.KB`, already built), enforcing `config/retrieval.yml` caps and
   emitting `retrieval` events (§6.3). Retrieval mechanics are done; this is the
   agent-loop harness around them.

**Deferred within retrieval (not blocking):** the optional Flash-written one-line
descriptions for uninformative index headings (§8.4) are not generated — the index
uses extractive descriptions only. It is additive (a per-section string) and
gated on a Gemini id; the index structure won't change when it lands. The xlsx
shape classifier (§8.7) is a solid first pass (registry-vs-prose by key-column
heuristic; single-row headers), not the full two-row grouped-header/matrix
treatment — refine if Stage-3 quality testing shows spreadsheet recall gaps.

**Flag to Tom (instrument fidelity):** the DTA tool prints **identical text for the
Moderate and Major consequence tiers of §3.7** ("System feature causes data leak or
access issue. Contained but serious."). Transcribed verbatim
(`consequence_table.json` `3.7._transcription_note`) to preserve fidelity — this is
an apparent upstream error worth correcting in the tool, not in our encoding.

Provenance corrections from Tom (July 2026) — the three documents whose sidecars
were originally inferred (they had no embedded title metadata) are now fixed to
Tom's sources:

- `ethics/TRS-GUIDANCE-AI-150925.pdf` — **The Research Society**, *AI Guidelines*
  (`https://www.researchsociety.com.au/member-resources/ai-guidelines/`). "TRS" =
  The Research Society. (Originally mis-inferred as internal IP Australia — the
  wrong guess is corrected in place.)
- `data_governance/Data-quality-checklist.pdf` — **National AI Centre**,
  *Strengthen data quality: data quality checklist*
  (`https://www.ai.gov.au/planning-ai/strengthen-data-quality`).
- `ethics/Guidance-for-AI-adoption-implementation-guidance_0_0.pdf` — **National
  AI Centre** (`https://www.ai.gov.au/staying-safe-and-responsible/essential-ai-practices/guidance-ai-adoption-implementation-guidance`).
  (Both had been attributed to the DTA; ai.gov.au is the National AI Centre site.)

Residual soft fields (not blocking, not inferred provenance): a few
`version`/`source_url` values are landing-page-level rather than the exact
document permalink (e.g. OAIC guideline consolidation date, some ASD publication
URLs), and `licence` strings assume the standard imprint (CC-BY-4.0 for
Commonwealth material) rather than a per-document imprint-page check. Tom's
attestation covers redistributability regardless.

Corpus observations for whoever builds ingestion (from the July 2026 review):

- All 37 PDFs have a real text layer — no OCR needed. The ISM PDF renders its
  controls as `Control: ISM-XXXX; …` lines (regexable into `record` chunks);
  the Privacy Act and Archives Act compilations are docx with full legislative
  styles (`ActHead*`, `subsection`) — provision anchors come from the style tree.
- Spreadsheet headers are one or two rows with merged group headers (cloud
  controls matrix `Principles` sheet; the pattern-mapping workbook) —
  normalization per §8.7 must detect header depth and fill down groupings.
- The ADM Better Practice Guide appears twice: `legal/…March-2025.pdf` and
  `ethics/apo-nid306481.pdf` (an earlier edition of the same guide). They now
  carry distinct `short_name`s (`ADM Better Practice Guide` vs
  `ADM Guide (earlier ed.)`) and live in different specialists, so KBs stay
  independent; Tom may still drop the stale copy. The earlier edition's exact
  `version` is unconfirmed (marked `earlier edition`).
- `legal/Artificial-Intelligence-Guidance-May-2026.pdf` is confirmed the **UK Bar
  Standards Board's** guidance (in force 18 May 2026) — Tom to confirm it's
  wanted alongside the AU material, or swap for an AU equivalent.
- `solution_architect/f4a6c658-en.pdf` is an **OECD** paper, *The state of AI in
  public audit* — an odd fit for the solution-architect corpus; Tom to confirm
  it belongs there (kept as placed).
- `The-new-machinery-of-government…pdf.pdf` has a doubled extension; harmless
  (doc_id slugging normalizes it). `placeholder.md` files can now be deleted —
  every folder holds real documents with sidecars.

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
- **Sidecar `short_name` = citation key, unique per specialist** (not globally).
  KBs are per-specialist (§8.3), so uniqueness is only asserted within a folder;
  the CSIRO pattern entries use the pattern name as `short_name`, so a citation
  renders `[Fairness Assessor, §Benefits]`. Legislation cites by Act title
  (`[Privacy Act 1988, s 6]`), registries by their own short name (`[ISM, p.112]`).
  Chosen because these are the human-recognisable keys a reader would check.
- **`redistributable: true` on all 106 sidecars rests on Tom's in-session
  attestation**, not a per-document licence audit. The `licence` field still
  records the *actual* licence (CC-BY-4.0 for most Commonwealth material, plus
  CC-BY-SA / US public-domain / UK OGL / OECD / arXiv / ABA / UTS / BSB /
  IP-Australia-internal for the rest). The ingestion gate's allow-list
  reconciles with these — **resolved** in `config/licences.yml` (next bullet).
- **Licence gate keeps `licence ∈ allow_list`** rather than treating
  `redistributable: true` as sufficient (STATUS "In progress" step 1, resolved).
  Defence-in-depth: a new document with an unlisted licence fails the build and
  forces a human decision, instead of an inherited `true` waving it through.
  `config/licences.yml` enumerates the exact 10 licence strings the cleared
  sidecars carry; a test asserts the gate passes on the current corpus and that
  no allow-list entry is unused.
- **§8.5 "Offer appropriate explanations" → Ethics specialist.** TECH_SPEC §6.2
  was silent (listed ethics owning 8.1/8.2/8.4, omitted 8.5, no other claimant).
  Assigned to ethics — §8.5 sits in section 8's transparency/explainability
  cluster ethics already owns. TECH_SPEC §6.2 ethics row updated in the same
  commit (fix the losing doc, CLAUDE.md §2). Recorded in `sections.json`
  `_decisions.8.5` and asserted by a test.
- **Token estimation is a dependency-free word+punct count** (`retrieval/tokens.py`),
  not a model tokenizer. The 400–900 targets are structural caps, not quality
  dials (§8.8); consistency matters more than absolute accuracy, and it keeps the
  runners tokenizer-free.
- **Index budget enforced via a coarsening ladder** (§8.4): full section paths →
  top-level sections → lean nodes → one-line-per-doc summary; the builder picks
  the least-coarse rung under `index.max_tokens` (25K). it_security lands at the
  summary rung (~7.3K); records stay fetchable by key regardless of coarseness.
- **ISM controls detected inline in the PDF** (`Control: ISM-####`) and emitted as
  `record` chunks keyed by control id, so `fetch("ISM-1612")` returns the exact
  control at its true page. Legislative provision locators (`s 30A`) derive from
  `ActHead`/`SubsectionHead` styles; `toc`/header styles are skipped.
- **Built KBs are committed** (`kb/*.sqlite` + index + manifest, ~17 MB) per §8.5's
  "commit directly at this size". `ingested_at`/`generated_at` timestamps mean a
  re-ingest always diffs — accepted as the documented provenance tradeoff; the
  release-asset overflow valve (§14) remains for when a KB gets oversized.

## Blocked on Tom

These block the *next* tasks (CLAUDE.md §8, TECH_SPEC §16). The instrument
source and Table 1/Table 2 landed July 2026 (see Done) and are no longer here:

- **~~`.meta.yml` sidecars with verified licences~~ — DONE (July 2026), and the
  follow-on allow-list config is now RESOLVED** (`config/licences.yml`). Nothing
  from this item blocks anymore.
- **~~Exact Gemini model identifiers~~ in `config/models.yml` — DONE (July 2026).**
  Tom pinned the tier ids: lite → `gemini-3.1-flash-lite`, flash →
  `gemini-3.5-flash`, pro → `gemini-3.1-pro-preview`. The `GEMINI_API_KEY` secret
  is also set in the repo (backend + Actions). **No hard blockers remain** — the
  first real LLM call (interviewer, generalists, specialists, reconciler,
  architect, reviewer) is unblocked. Everything built so far is LLM-free and was
  already unblocked: the rating engine, the instrument encoding, and the whole
  ingestion/retrieval path.

## Deploy-layer reminders (pinned in CLAUDE.md §9, not yet actioned)

Not blocking now, but they bite the moment anyone deploys: Render auto-deploy
OFF or watch-scoped to `backend/**`; SPA path-aware with hash routing and a
path-filtered `pages.yml`; backend commits via the GitHub Contents/Git-Data API,
not `git push`.
