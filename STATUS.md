# Build status

## Current stage

**Stage 2 — Threshold** (PROJECT_BRIEF.md §9) — **governance slice built and tested;
exit test MET for the deterministic wiring. The backend is now live-dispatchable
end-to-end** (run creation → submit → Governance Action → checkpoint pushes →
status proxy → threshold routing), still with the LLM seam mockable and the
frontend not yet built. (Stage 0 — Foundations remains met; its record is
preserved below under Done.)

Scope of Stage 2: generalists, reconciler, deterministic rating engine, review/revise
UI, markdown export. **Built previously:** the whole pipeline-side threshold path —
two generalists → code higher-wins resolution → the deterministic engine → routing →
the `THRESHOLD_REVIEW` pause — driven end-to-end by `pipeline/run.py`, plus markdown
export. **Built this branch:** the backend that dispatches it (`backend/app.py`,
`github_io.py`, `dispatch.py`, `config.py`, `outline.py`) and the `governance.yml`
Action that runs it, plus a durability fix to the pipeline's own commit helper (see
Done, below). **Not yet built:** the Brainstorm interview (interviewer, sufficiency,
PoC/flow-map endpoints, `templates/outline.md` amendment beyond initial copy), the
frontend entirely (review/revise UI, the transparency animation, resume-by-code
screen), the `full.*` pipeline stages, and a first live Gemini run (the seam is
mockable; the live transport is written but only exercised in Actions with a key).

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

- **Backend API + dispatch + status proxy, and the `governance.yml` Action that
  makes the pipeline live-dispatchable (TECH_SPEC §7, §5.7, §14; this branch).**
  21 new tests (`backend/tests/test_app.py`), all LLM-free and network-free
  (`FakeGitHubClient`/`FakeDispatcher`, TECH_SPEC §15); ruff clean. The slice
  built — deliberately narrower than the full §7 table, matching the prior
  handoff's step 1 scope:
  - **`backend/app.py`** — a FastAPI app factory (`create_app(github=, dispatcher=,
    settings=)`, so the real GitHub/dispatch clients are swappable for fakes with
    no network in tests). Endpoints: `GET /api/health`; `POST /api/runs` (draws +
    collision-checks a run code via `runcode.generate_unique`, commits the initial
    `run.json` + `status.json` + `brainstorm/outline.md` skeleton as **one** atomic
    commit); `GET /api/runs/{id}/status` (the primary poll — proxies `status.json`
    with `If-None-Match` → `304` passthrough); `GET /api/runs/{id}/artefact/{name}`
    (download proxy, `name` allow-listed against exactly the four artefacts TECH_SPEC
    §7 names — anything else refused before it ever becomes a repo path); `POST
    /api/runs/{id}/submit` (BRAINSTORM → SUBMITTED, dispatches
    `resume_from=THRESHOLD_DRAFTING`); `POST /api/runs/{id}/threshold/route` (`{outcome:
    conclude|full}` — conclude finalises to CONCLUDED/complete, full dispatches
    `resume_from=FULL_DRAFTING`, both refuse outside `THRESHOLD_REVIEW`+`awaiting_user`);
    `POST /api/runs/{id}/resume` (validated-code rehydration for the SPA). **Not**
    built: `/brainstorm/message`, `/edit-outline`, `/poc`, `/flow-map`, `/revise`,
    `/answers` — Brainstorm-interview and full-assessment-checkpoint work, out of
    this slice's scope (see handoff notes).
  - **Statelessness by construction.** Every endpoint re-reads `run.json`/`status.json`
    from the repo per call rather than trusting in-process memory — a cold Render
    instance has none, and the repo is the only durable store (CLAUDE.md §3, §9).
  - **Every `{run_id}` path param is validated through `runcode.validate` before it
    ever becomes a Contents-API path** — closes a real path-traversal surface (an
    unvalidated id could otherwise address arbitrary repo paths through the Contents
    API), not just a format nicety; tested (`test_status_proxy_rejects_malformed_run_id`
    et al.).
  - **`backend/github_io.py`** — the commit helper (§14): `RestGitHubClient` over
    stdlib `urllib` (no new HTTP-client dependency, matching `pipeline/llm.py`'s
    `GeminiTransport` pattern) — Contents API reads with `If-None-Match` passthrough,
    Git Data API writes (tree + commit + ref update) so a multi-file skeleton or
    checkpoint lands as one atomic commit rather than sequential Contents-API PUTs.
    A non-fast-forward ref update is retried by re-reading the tip and rebuilding the
    tree — because every writer touches only its own disjoint `runs/<run-id>/...`
    path, the retry always succeeds (§14's rebase-and-retry, expressed without a
    working copy). `FakeGitHubClient` (in-memory, real-enough 404/304/ok semantics)
    is the test double.
  - **`backend/dispatch.py`** — `WorkflowDispatcher` (the one `workflow_dispatch`
    POST, §5.7 — fire-and-forget, never waits on the run) + `FakeDispatcher` for
    tests. Shares the fine-grained PAT's env var with `github_io.py`
    (`WINDTUNNEL_PAT`), read lazily so construction never fails on an unconfigured
    env (CLAUDE.md §6: neither ever reaches the SPA).
  - **`backend/config.py`** — the Python owner of deployment identity (CLAUDE.md
    §6): GitHub owner/repo/branch, the governance workflow filename, CORS origins.
    Env-overridable, pinned defaults correct for this deployment. When
    `frontend/config.ts` lands it mirrors these by hand (see Decisions — no
    Python↔TS codegen exists or is planned).
  - **`backend/outline.py`** — `render_initial_outline`: copies `templates/outline.md`
    verbatim with `run_id`/`created_at`/`updated_at` filled into the front-matter
    (§7.1). The only outline write in this slice; turn-by-turn amendment is
    Brainstorm-interview work.
  - **Packaging (resolves the prior handoff's open question): "thin shared import,"
    not vendoring.** `backend/app.py` (and `backend/tests/conftest.py`) add
    `pipeline/` to `sys.path` and import `runcode`/`statefile`/`status` directly —
    both deployables share the one repo at runtime (TECH_SPEC §1), so this is a real
    import of the one owner of the run-code/run.json/status.json facts, not a fork
    of them (CLAUDE.md §3 "one owner per fact"). `backend/pyproject.toml` gained
    `fastapi`, `uvicorn`, and `pyyaml` (the last because `status.py`'s
    `load_expected_ranges()` needs it transitively).
  - **`.github/workflows/governance.yml`** — `workflow_dispatch` with
    `{run_id, resume_from}`, installs pipeline deps via `uv`, configures the
    Actions-bot git identity, runs `python -m run <run_id> --resume-from <stage>`
    with `GEMINI_API_KEY` from secrets. `concurrency: governance-<run_id>` so a
    retried dispatch for the same run (the §5.7 "hasn't started yet — retry?" path)
    queues rather than racing; different runs' disjoint paths run in parallel.
  - **Durability fix to `pipeline/run.py`'s `GitCommitter` (a real gap found while
    building the backend, not a spec contradiction — see Decisions).** It committed
    locally but never pushed; without a push, every checkpoint the backend's status
    proxy is supposed to see would stay invisible until the whole Actions job ended,
    silently breaking §7's near-real-time polling and §5.6's "last checkpoint stays
    intact" resume guarantee against a mid-job container death. Fixed: every commit
    now pushes immediately, with fetch→rebase→retry on a non-fast-forward (§14),
    injectable `sleep` for fast tests. 4 new tests (`pipeline/tests/test_git_committer.py`)
    against real local bare-repo remotes (no network): push-on-commit, no-op-stays-
    local, rebase-and-retry-past-another-writer's-race, and loud failure after
    exhausting retries.
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

The former handoff steps 1–2 (backend `POST /api/runs` + dispatch + status proxy,
`governance.yml`) are **done** this branch — see Done → *Backend API + dispatch +
status proxy*. The pipeline is now live-dispatchable end-to-end: `POST /api/runs`
creates a run, `POST /api/runs/{id}/submit` dispatches `governance.yml`, the Action
runs `pipeline/run.py` to the `THRESHOLD_REVIEW` pause and pushes every checkpoint,
and `GET /api/runs/{id}/status` proxies the result with conditional-GET support.
`POST /api/runs/{id}/threshold/route` closes the loop (conclude, or dispatch onward
to `FULL_DRAFTING` — which the driver does not yet implement, see step 1 below).
Next concrete steps, in rough dependency order:

1. **Full-assessment stages (`pipeline/stages/`, `FULL_DRAFTING` onward, §5.1).** The
   driver stops at `THRESHOLD_REVIEW` and raises `StageNotImplemented` for `full.*` —
   routing a run to "full" via the new endpoint dispatches it, but the Action will
   fail calmly at `FULL_DRAFTING` until this is built. Build: specialist prompts
   (per-specialist owned sections, §9.3) + the specialist retrieval loop (give each
   specialist its `kb/<specialist>.index.json` in-context + the `KB.fetch`/`KB.search`
   tools — `retrieval.KB`, already built — enforcing `config/retrieval.yml` caps and
   emitting `retrieval` events §6.3); the question checkpoint (`FULL_CHECKPOINT`
   pause, already a pause-stage in the driver, but nothing yet raises questions or
   drives `POST /api/runs/{id}/answers`, which also doesn't exist yet — add it
   alongside); the architect appendix; the reviewer loop (§11, residual 12.3/12.4
   reuse the engine); and notebook + HTML assembly (§12). Register each in `run.py`'s
   `_HANDLERS`/`_NEXT`/`_CHECKPOINT_OUTPUTS` maps — the driver is built to extend by
   table entry.
2. **Brainstorm interview + outline canvas (backend `brainstorm/` + frontend).**
   `POST /api/runs` currently only *seeds* `brainstorm/outline.md` from the template
   (`backend/outline.py`) — nothing yet amends it. Needed: the interviewer
   (Flash-Lite, §7.1), the sufficiency judge, `POST /api/runs/{id}/brainstorm/message`
   + `.../edit-outline`, the feasibility gate + PoC/flow-map generation
   (`POST .../poc`, `.../flow-map`), and `POST .../revise` for the ≤2-per-artefact
   brainstorm revisions (brief §7). This is what turns `Stage.BRAINSTORM` into
   something a user actually drives, ahead of hitting `/submit`.
3. **Frontend, entirely.** `frontend/` is still just a `README.md` + `.gitkeep`. Needed
   before *any* of the above is usable end-to-end by a person: the ghosted-canvas
   Brainstorm UI (design §6), the transparency animation driven by `status.json`
   polling (design §7, this branch's status proxy is what it polls), the threshold
   review/revise screen (design §7.4) talking to `/threshold/route`, the checkpoint
   question UI, the resume-by-code screen (`/api/runs/{id}/resume`, built this
   branch), and the report (design §8). `frontend/config.ts` also needs writing —
   see Decisions below on keeping it in sync with `backend/config.py` by hand.
4. **A first live Gemini run** to eval real generalist/reconciler judgement (the LLM
   seam is mockable and unit-tested end-to-end; live quality is untested). Exercisable
   now via `POST /api/runs` → `/submit` with `WINDTUNNEL_PAT` + `GEMINI_API_KEY` set,
   once step 1 or a threshold-only run is dispatched — no frontend required to smoke
   test this with a raw HTTP client.

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

- **`GitCommitter` now pushes every commit immediately, with fetch→rebase→retry
  on non-fast-forward (this branch, `pipeline/run.py`).** Not a documents
  contradiction — a real gap in the prior build: it committed locally only, which
  is fine for `FakeCommitter`-driven tests but would have silently broken §7's
  near-real-time status polling in real Actions runs (a checkpoint invisible to
  the backend until the whole job ended) and weakened §5.6's "last checkpoint
  stays intact" guarantee against a mid-job container death. Found and fixed while
  building the backend that depends on checkpoints actually being visible
  mid-run. Push uses `HEAD:<branch>` against `origin` with an injectable `sleep`
  for fast tests; retries rebase onto the latest remote tip on a non-fast-forward
  (§14) — safe because every writer's changes are confined to one run's disjoint
  path. `pipeline/tests/test_git_committer.py` exercises this against real local
  bare-repo remotes (push-on-commit, no-op stays local, rebase-past-another-
  writer's-race, loud failure after exhausting retries) — no network needed.
- **Backend↔pipeline packaging: a thin shared import, not vendoring (STATUS.md's
  own prior open question, resolved this branch).** `backend/app.py` and
  `backend/tests/conftest.py` add `pipeline/` to `sys.path` and import
  `runcode`/`statefile`/`status` directly, rather than copying those modules into
  `backend/`. Chosen over vendoring because both deployables check out the same
  repo at runtime (TECH_SPEC §1) — a real import costs nothing and keeps CLAUDE.md
  §3's "one owner per fact" literal (a vendored copy would silently drift the
  moment either side changed independently). Cost: `backend/pyproject.toml` needs
  `pyyaml` too, since `status.py`'s `load_expected_ranges()` reads
  `config/budgets.yml` with it — a small, correctly-attributed transitive
  dependency, not a new fact to own.
- **Every `{run_id}` path param is validated through `runcode.validate` before
  building any repo path (`backend/app.py::_valid_run_id`), on every endpoint —
  not only the `/resume` endpoint TECH_SPEC §7 explicitly calls this out for.**
  The spec's own text for the artefact proxy ("arbitrary repo paths are refused")
  implies the same discipline is needed wherever a client-supplied string reaches
  a GitHub Contents-API path; centralising it as a FastAPI dependency makes that
  true structurally rather than per-endpoint-by-convention.
- **`backend/config.py` is the one Python owner of deployment identity (repo
  owner/name, branch, CORS origins), env-overridable with pinned correct
  defaults.** CLAUDE.md §6 names "a pipeline constant" as the counterpart to
  `frontend/config.ts`; since only the backend (not the pipeline proper) needs
  these facts to make GitHub API calls, they live in `backend/config.py`, not a
  new `pipeline/` module. There is no Python↔TypeScript codegen — when
  `frontend/config.ts` is written it copies these values by hand; a mismatch
  would be a same-day-fixable config bug, not a structural one, and codegen for
  three constants would be over-engineering for this scale (CLAUDE.md's "don't
  design for hypothetical future requirements").
- **The commit helper's writes use the Git Data API (tree + commit + ref update)
  rather than sequential Contents-API `PUT`s.** TECH_SPEC §14 says "commits via
  the GitHub Contents / Git Data API" without picking one; Git Data API was
  chosen because run creation and every checkpoint commit are inherently
  multi-file (`run.json` + `status.json`, sometimes + an artefact), and the
  Contents API has no multi-file atomic write — sequential PUTs would let a
  crash between them land a run.json/status.json pair that disagree. One tree +
  one commit + one ref update is atomic by construction.
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
