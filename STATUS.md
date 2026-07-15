# Build status

## Current stage

**Stage 2 — Threshold** (PROJECT_BRIEF.md §9) — **governance slice built and tested;
exit test MET for the deterministic wiring.** (Stage 0 — Foundations remains met;
its record is preserved below under Done.)

Scope of Stage 2: generalists, reconciler, deterministic rating engine, review/revise
UI, markdown export. **Built this branch:** the whole pipeline-side threshold path —
two generalists → code higher-wins resolution → the deterministic engine → routing →
the `THRESHOLD_REVIEW` pause — driven end-to-end by `pipeline/run.py`, plus markdown
export. **Not yet built:** the backend API that serves/routes a paused run and the
frontend review/revise UI (those are Stage 2's remaining surface), and live Gemini
calls (the seam is mockable; the live transport is written but only exercised in
Actions with a key).

**Exit test** ("threshold output for a known test case matches a hand-worked
assessment's ratings exactly", brief §9): **met for the engine wiring.**
`tests/test_threshold_pipeline.py::test_ratings_match_hand_worked` and the
end-to-end `test_pipeline_runs_threshold_to_review_pause` drive the full path with a
scripted transport and assert every §3.1–3.8 rating and the §3.9 overall match values
hand-worked from the real Table 2 (e.g. resolved Major/Possible → High, overall High).
The LLM's *judgement* (which consequence/likelihood a real model picks) is not unit
tested — that needs a live model and a Stage-2 eval — but the integrity-critical part
(ratings are a provable output of code from the resolved inputs) is.

**Stage 0 boundary (still true):** the rating engine + instrument encoding were built
under Stage 0 as unblocked, self-contained pieces. They are now *wired in* by the
threshold stage — this is the first place `pipeline/rating/` is consumed by a running
pipeline.

## Done

- **Threshold governance slice — generalists → reconciler → engine → routing,
  driven end-to-end (TECH_SPEC §5.1, §9, §10; Stage 2).** 12 new tests
  (`tests/test_threshold_pipeline.py`), 89 total green; ruff clean. The pieces:
  - **LLM seam (`pipeline/llm.py`).** Role→model resolution from `config/models.yml`,
    a `CallBudget` enforcing `run_max_calls` (§13), and JSON discipline
    (`complete_json` parses loudly — a non-JSON answer is a loud `LLMError`, never a
    silent empty result). The transport is injectable: `ScriptedTransport` for
    tests/offline (the whole path runs LLM-free, §15) and `GeminiTransport` — the
    live `:generateContent` REST call over stdlib urllib (no new dep), the sole
    holder of `GEMINI_API_KEY` (§6). The live transport is written but exercised only
    in Actions with a key.
  - **Prompts (`prompts/threshold_generalist.v1.md`, `threshold_reconciler.v1.md`)**
    + manifest entries (§9.1). Both encode the untrusted-content discipline (§9.2),
    the precautionary threshold posture (higher-when-uncertain, likelihood ≥ Possible
    on thin evidence), and the **hard rule that no agent emits a rating** (§10). The
    generalist schema forbids a `rating` key; the reconciler emits narrative +
    rationale only (it does not even select tiers).
  - **Agent layer (`pipeline/agents/`).** `prompting.py` owns prompt loading, the
    untrusted wrapper, and the threshold instrument context (question text +
    consequence/likelihood descriptor tables from `instrument/*.json`, §9.3).
    `threshold.py` runs the two generalists and the reconciler and **validates the
    output at the boundary**: off-vocabulary tiers and any asserted-rating key are
    *rejected*, not repaired (§9.4, §10).
  - **Threshold stages (`pipeline/stages/threshold.py`).** `THRESHOLD_DRAFTING` (two
    independent generalists) → `THRESHOLD_RECONCILING`: **code resolves the two
    drafts' §3 tiers higher-wins** (§10.3), the deterministic engine (`pipeline/rating/`,
    already built — now *wired in*) computes every rating and the §3.9 overall, and
    routing is computed from §3.9 per the tool's own rule (guidance §4: Low ⇒ conclude
    possible / full optional; Medium/High ⇒ full required; High ⇒ + governance-body
    flag §12.5). Emits `reconciled.json`, `divergence.json`, `ratings.json`,
    `routing.json`, and a readable `threshold_assessment.md` (Stage 2 markdown export).
  - **Pipeline driver (`pipeline/run.py`).** The §5 state machine: reads `run.json`,
    routes to the stage handler, and advances to the `THRESHOLD_REVIEW` pause.
    Idempotent resume keyed on **checkpoint-output-file existence** (§5.3's literal
    test); the §5.7 start handshake (first action = heartbeat + `overall_state=running`,
    committed); calm §5.6 failure (any error → `run.json` failed + `status.json`
    failure payload, run code surfaced, resumable, no stack trace to the primary UI);
    and a **commit seam** — `FakeCommitter` for tests, `GitCommitter` (Actions-side
    `GITHUB_TOKEN`, §14) for real — so the whole driver is testable with no git. CLI
    `python -m run <run-id> [--resume-from STAGE]`.
  - **`status.py` additions** (additive, existing tests unaffected): `Event.from_dict`
    + `StatusModel.load` — reload the committed `status.json` log on resume so event
    ids stay monotonic, rebuilt through the existing `rebuild()` projection (§6).
  - **Exit test (Stage 2) met for the deterministic wiring:** ratings for a known
    case match values hand-worked from the real Table 2 (resolved Major/Possible →
    High; overall highest-wins → High), asserted both in isolation and through the
    full driver run.
- **Run-state core (`pipeline/runcode.py`, `statefile.py`, `status.py`) — the
  resume model (TECH_SPEC §3–§6).** LLM-free, 36 tests (`tests/test_runstate.py`),
  exercised end-to-end (a run drives a threshold slice → real `run.json`/`status.json`).
  - `runcode.py` (§3): the 29-symbol alphabet, `WT-XXXX-XX` format, CSPRNG
    `generate()`, `normalize`/`is_valid`/`validate`, and an I/O-free
    `generate_unique(exists)` (the backend plugs its Contents-API existence check
    in). The single **Python** owner of the run-code fact (CLAUDE.md §6); the
    frontend keeps the one unavoidable TS copy.
  - `statefile.py` (§4, §5): `RunState` = the authoritative `run.json`. The §5.1
    `Stage`/`StageStatus`/`Phase` enums, phase derived from stage, atomic
    save/load, checkpoints + idempotent `has_checkpoint` (§5.3), loud `from_dict`
    validation, `fail()` (§5.6), and the **caps** as hard invariants
    (`record_revision` ≤2/artefact, `record_review_cycle` ≤2 — raise at the cap,
    CLAUDE.md §3).
  - `status.py` (§6): the fixed 14-node graph (§6.2) with specialist nodes +
    owned sections **derived from `instrument/sections.json`** (one owner, no
    re-statement); the controlled 9-type event vocabulary (§6.3); `StatusModel`
    that enforces the three invariants structurally — whole-graph `nodes` every
    write, append-only monotonic `evt_NNNNNN` ids, and node↔event coupling
    (`active`/`complete`/`failed` are only reachable via methods that append the
    matching `stage_started`/`stage_complete`/`error`). Questions (§6.4) + failure
    (§6.5) payloads; `expected_ranges` aggregated from `config/budgets.yml`; and
    `rebuild(run, log)` — the concrete "always safe to recompute from run.json +
    event log" projection guarantee, asserted against live-built models.
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

The former handoff steps 1–3 (commit/dispatch plumbing, prompts, threshold stage)
are **done** this branch — see Done → *Threshold governance slice*. `pipeline/run.py`
is the live driver, the threshold prompts are authored, and the two-generalists →
reconciler → engine → routing path runs end-to-end to the `THRESHOLD_REVIEW` pause.
Next concrete steps, in rough dependency order:

1. **Backend `POST /api/runs` + dispatch + status proxy (TECH_SPEC §7, §5.7, §14).**
   The pipeline driver is ready to be *dispatched*; what's missing is the backend
   that creates a run and triggers `governance.yml`. Needed: `backend/app.py`
   (`POST /api/runs` → `runcode.generate_unique` with a Contents-API existence check
   + `RunState.new().save()` + `StatusModel.initial().save()` + commit the skeleton
   incl. `brainstorm/outline.md`; the status/artefact GET proxies; `POST
   /api/runs/{id}/route` at the threshold pause → dispatch `resume_from=FULL_DRAFTING`
   or set `CONCLUDED`); `backend/github_io.py` (Contents/Git-Data API commit helper,
   serialise-per-run, §14); `backend/dispatch.py` (`workflow_dispatch` trigger, §5.7).
   Packaging note still open: backend and pipeline share only the repo at runtime, and
   the run-state + runcode modules live in `pipeline/` — vendor them into `backend/`
   or add a thin shared import when `backend/` lands.
2. **`.github/workflows/governance.yml`** — the `workflow_dispatch` workflow (inputs
   `{run_id, resume_from}`) that installs `pipeline/` deps via `uv` and runs
   `python -m run <run_id> --resume-from <stage>` with `GEMINI_API_KEY` + the built-in
   `GITHUB_TOKEN` (the driver's `GitCommitter` uses the working-copy checkout). This
   plus step 1 turns the built driver into a live, dispatchable run.
3. **Full-assessment stages (`pipeline/stages/`, `FULL_DRAFTING` onward, §5.1).** The
   driver stops at `THRESHOLD_REVIEW` and raises `StageNotImplemented` for `full.*`.
   Build: specialist prompts (per-specialist owned sections, §9.3) + the specialist
   retrieval loop (give each specialist its `kb/<specialist>.index.json` in-context +
   the `KB.fetch`/`KB.search` tools — `retrieval.KB`, already built — enforcing
   `config/retrieval.yml` caps and emitting `retrieval` events §6.3); the question
   checkpoint (`FULL_CHECKPOINT` pause, already a pause-stage in the driver); the
   architect appendix; the reviewer loop (§11, residual 12.3/12.4 reuse the engine);
   and notebook + HTML assembly (§12). Register each in `run.py`'s `_HANDLERS`/`_NEXT`/
   `_CHECKPOINT_OUTPUTS` maps — the driver is built to extend by table entry.
4. **Frontend threshold review/revise UI + live-model wiring** — the remaining Stage 2
   surface: the review screen at the pause (design §7.4), user revision (≤2) of the
   threshold artefact, and a first live Gemini run to eval real generalist/reconciler
   judgement (the seam is mockable and unit-tested; live quality is untested).

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
- **Sidecar sweep (this session):** Tom uploaded *Policy for the responsible use
  of AI in government* (v2.0, DTA) straight to GitHub into `data_governance/`
  and `legal/` — two identical 645 355-byte copies, neither with a sidecar. Both
  now have one (`short_name: "AI Use Policy v2.0"`); licence confirmed from the
  document's own imprint page (page 2: "© Commonwealth of Australia (Digital
  Transformation Agency) 2025", CC-BY-4.0), not inferred, so `CC-BY-4.0` needed
  no allow-list change. A corpus-wide sweep after this fix confirms every
  non-sidecar, non-README/placeholder file in all six specialist folders now
  has a matching `.meta.yml` (108 documents total). Note: the request described
  this as added to `data_governance` and `it_security`, but no such file exists
  under `it_security` — only `data_governance` and `legal` copies were found on
  disk. Flagging in case a third copy was intended for `it_security` and didn't
  land.
- `The-new-machinery-of-government…pdf.pdf` has a doubled extension; harmless
  (doc_id slugging normalizes it). `placeholder.md` files can now be deleted —
  every folder holds real documents with sidecars.

## Decisions made (that the documents were silent on)

- **§3 tier resolution is done in code, not by the reconciler LLM.** §10.3 describes
  the reconciler "taking the higher tier"; since higher-wins is a mechanical rule and
  the invariant is "code computes," the *tier resolution* is deterministic
  (`stages/threshold.py::resolve_inputs`) and the reconciler agent writes only
  narrative + rationale + divergence notes — it never emits a tier or a rating. This
  makes the entire §3 rating path a provable code output (the strongest reading of
  §10) and is why `threshold_reconciler.v1.md` has no tier fields in its schema.
- **Idempotent resume keys on checkpoint-output-file existence, not the `run.json`
  `checkpoints` sha.** §5.3 says literally "check whether its checkpoint outputs
  already exist." Because a stage's own commit sha cannot be known before that commit
  (a circular definition), the driver treats a stage as done iff its declared output
  files exist (`run.py::_CHECKPOINT_OUTPUTS`); `run.set_checkpoint(stage, sha)` still
  records the sha afterwards as best-effort provenance (it persists on the next
  commit). This is robust: a death after a stage's commit but before the next
  correctly skips the completed stage on resume.
- **`GeminiTransport` targets the Google Generative Language `:generateContent` REST
  endpoint via stdlib urllib** (no new dependency). The request shape
  (`systemInstruction` / `contents` / `generationConfig.responseMimeType`) is stable
  and independent of the specific tier id, so it stays correct as Tom's pinned ids
  change. It reads `GEMINI_API_KEY` from env and is exercised only in Actions; unit
  tests use `ScriptedTransport`.
- **The call budget is a per-run ceiling (`run_max_calls`), enforced in `CallBudget`.**
  §13's per-stage `max_calls` are documented in `budgets.yml`; the driver-shared
  `CallBudget` enforces the whole-run guard now (the cheap, always-correct backstop),
  and per-stage enforcement can be layered on when the full stages land.
- **The `run.py` driver extends by table entry.** New stages are added by registering
  a handler in `_HANDLERS`, a successor in `_NEXT`, and checkpoint outputs in
  `_CHECKPOINT_OUTPUTS` (plus a pause/terminal set if applicable) — the loop, resume,
  heartbeat and failure handling are stage-agnostic. `full.*` stages currently raise
  `StageNotImplemented`, which the §5.6 handler surfaces as a calm failure.
- **Cross-KB corpus duplication is retrieval-scoped and intentional.** A document
  may live in more than one `corpus/<specialist>/` folder so it lands in multiple
  specialist KBs. This affects only what a specialist can *retrieve and cite* — it
  does **not** touch the specialist write-scope invariant (CLAUDE.md §3), which is
  enforced separately by `instrument/sections.json` ownership. First applied: the
  **ADM / human-oversight cluster** (*ADM Better Practice Guide*, *New Machinery of
  Government*), Ombudsman-authored and administrative-law-framed (hence `legal/`),
  duplicated into `ethics/` because their substance — transparency of automated
  decisions, explanations to affected people, human oversight — maps onto ethics'
  owned §8.1/8.2/8.4/8.5. Ethics previously reached only the *older* ADM guide
  (`apo-nid306481.pdf`). Duplicate surgically, not broadly: each specialist index
  has a 25 000-token budget (`config/retrieval.yml`) that duplicates compete for
  (ethics after this change: 17 docs, index ~17.7k tokens — within budget), and
  every duplicate widens the public double-publish surface (CLAUDE.md §3).
- **Failure keeps `run.json.stage` pointing at the failing stage** (not a distinct
  `FAILED` stage value); `stage_status="failed"` + `last_error` is the failure
  marker. §5.1 lists FAILED as a state and §5.6 says "writes `stage_status=failed`",
  but §5.3 resumes by reading `stage`+`stage_status` and restarting the current
  stage from its last checkpoint — overwriting `stage` with FAILED would lose that
  resume target. `Stage.FAILED` stays in the enum for completeness/validation but
  is not written by `fail()`. (`statefile.RunState.fail`.)
- **`status.json` `nodes` is `node_id → state` strings only** (matching the §6.1
  shape), not node objects. The static topology (friendly name, model role, owned
  sections) lives in `status.py` and is mirrored in the frontend, since §6.2 says
  the node ids are "shared verbatim between pipeline and animation" — i.e. the
  frontend already holds the rest. Exposed via `node_specs()`/`friendly_name()`
  for pipeline + tests.
- **`waiting_user` is not narrated by its own event type.** §6.3's coupling rule
  enumerates only `active`/`complete`/`failed` (→ `stage_started`/`stage_complete`/
  `error`); there is no "pause" event type. So `wait_node` sets the node +
  `overall_state=paused` without a coupled event — the pause is narrated by the
  `question_raised` lines already emitted (checkpoint) or by `overall_state` alone
  (threshold review). `rebuild()` therefore derives `waiting_user` from `run.json`
  (stage + `awaiting_user`), not from the log.
- **`expected_ranges` is aggregated from `config/budgets.yml`, not hardcoded.**
  §6.1's example values ([120,300]/[600,1800]) are illustrative; the real
  projection sums the per-stage `expected_range_seconds` into per-phase ranges
  (threshold = drafting+reconciling = [50,210]; full = drafting+architect+reviewer
  = [170,630]) so tuning budgets flows straight into the animation hints. One owner
  (budgets.yml). (`status.load_expected_ranges`.)
- **The run-state core is placed in `pipeline/` and is git/API-I/O-free.** The §2
  layout puts `statefile.py`/`status.py` there; `runcode.py` joins them as the
  Python owner of §3. Committing `run.json`/`status.json` is left to the caller
  (backend `github_io.py` / an Actions commit helper, §14) so the modules stay
  pure and unit-testable. The backend↔pipeline packaging (they share only the repo
  at runtime) is deferred to when `backend/` lands — see handoff step 1.
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
