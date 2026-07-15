# Build status

## Current stage

**Stage 3 — Full assessment** (PROJECT_BRIEF.md §9): **the full governance path now
runs end-to-end to a `COMPLETE` run.** `FULL_DRAFTING → ARCHITECT → REVIEW → ASSEMBLY
→ COMPLETE` all drive in one dispatch (still pausing at `FULL_CHECKPOINT` only when a
specialist raises a question). This branch added the last two: **`REVIEW`** (the
bounded reviewer loop — coverage + coherence + amend directives + residual §12.3/§12.4)
and **`ASSEMBLY`** (the nbformat notebook + nbconvert HTML report, §12). Stage 2 —
Threshold remains met in full (record preserved below); Stage 0 — Foundations remains
met.

**Built this branch, part 2 (ASSEMBLY — the report, §5.1, §12; design §8):** the
`pipeline/assembly/` package — `references.py` (citation dedup + manifest resolution),
`notebook.py` (the §12.1 cell plan as a non-executable nbformat notebook), `render.py`
+ `templates/report.css` (the self-contained nbconvert HTML render in the Report
register) — plus `pipeline/stages/assembly.py` (the I/O boundary: gathers every
committed artefact, builds `artefacts/assessment.ipynb` + `assessment.html`), the
`run.py` table entries + the **terminal-COMPLETE finalisation** (`_finalise_terminal`:
the driver now sets `stage_status=complete`/`overall_state=complete` and commits when a
run reaches COMPLETE), and `nbformat`/`nbconvert` pinned in `pipeline/pyproject.toml` +
`uv.lock`. 12 new tests (`pipeline/tests/test_assembly.py`); the two REVIEW driver
tests updated (the full path now completes rather than stopping at the once-unbuilt
ASSEMBLY). **159 total pipeline tests green; ruff clean.** Verified once by rendering a
worked sample report end-to-end (title block, DTA numbering, residual table with
shape+label chips, unresolved panel, provenance, references), LLM-free.

**Built this branch, part 1 (REVIEW — the reviewer protocol, §5.1, §5.5, §11,
§12.3/§12.4):** `pipeline/agents/reviewer.py` (a single Pro call per cycle that
validates directive write-scope and the no-asserted-rating rule at the boundary),
`prompts/reviewer.v1.md` (registered under role `reviewer` → Pro), the `review`
handler + coverage checklist + amend loop + residual-engine call + `render_review_markdown`
in `pipeline/stages/full.py`, `run_specialist_amendment` + `SpecialistDraft.from_dict`
+ a shared retrieval-loop refactor in `pipeline/agents/specialist.py`, the
`reset_review_cycles` invariant on `RunState`, the reviewer-scope/coverage accessors
in `pipeline/agents/prompting.py`, and the `run.py` table entries that slot `REVIEW`
between `ARCHITECT` and `ASSEMBLY`. 22 new tests (`pipeline/tests/test_review.py`).

**Prior branch (ARCHITECT):** `pipeline/agents/architect.py` (a single-shot
Pro agent — no retrieval loop — that validates the plan at the boundary),
`prompts/architect.v1.md` (registered in `prompts/manifest.yml` under role
`architect` → Pro), the `architect` handler + `render_architect_markdown` +
specialist-context renderer in `pipeline/stages/full.py`, and the `run.py` table
entries that slot `ARCHITECT` between `FULL_DRAFTING` and `REVIEW`.

**Prior branch (FULL_DRAFTING):** `pipeline/agents/specialist.py` (the retrieval
tool loop + output validation), `pipeline/stages/full.py` (the `FULL_DRAFTING`
handler + questions payload + markdown render), `prompts/specialist.v1.md`, and
the `agents/prompting.py` additions that give every specialist call its
owned-section instrument text. `pipeline/run.py` gained conditional stage
resolution (`_resolve_next`) and a pause-setup hook (`_PAUSE_SETUP`), both
general enough for the remaining `full.*` stages to reuse.

**Not yet built:** `FULL_REVISING` (specialist re-draft after checkpoint answers —
now mostly a thin wrapper over the `run_specialist_amendment` built this branch) and
its backend `POST /api/runs/{id}/answers` endpoint; `USER_REVISION` (§5.8, the ≤2
post-COMPLETE full-assessment revisions); the Brainstorm interview (interviewer,
sufficiency, PoC/flow-map endpoints — note the PoC embed slot in ASSEMBLY (§12.3) is
built and dormant, waiting on `brainstorm/poc.html`); the frontend entirely; and a
first live Gemini run. See handoff notes below for the
concrete next steps and how they build on this branch.

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

- **`ASSEMBLY` — the notebook + HTML report, and the full path to `COMPLETE`
  (TECH_SPEC §5.1, §12; design §8; Stage 3; this branch).** The final deliverable
  and the end of the governance pipeline. The pieces:
  - **`pipeline/assembly/` — the report builder, pure and LLM-free.**
    `references.py` collects every specialist citation, dedupes by `short_name`, and
    resolves each against the KB **manifests** (§8.5) to title/publisher/version/URL —
    a dangling citation is marked unresolved, not dropped. `notebook.py::build_notebook`
    assembles the §12.1 cell plan as a **non-executable** nbformat notebook (asserted:
    zero code cells): title block, threshold §1–4, full §5–12 in tool order with inline
    citations (or a gap note), residual §12.3 table + §12.4 overall + the §12.5
    human-action flag, the appendices (implementation plan, recommended next steps = the
    aggregated gap register, unresolved disagreements, provenance), and the deduplicated
    reference list. `render.py` + `templates/report.css` render it via nbconvert's
    `basic` template wrapped in a **self-contained** HTML document (stylesheet inlined,
    no external fonts/scripts) delivering the design §8 Report register — serif body,
    DTA numbering, mono citations, risk chips carrying **shape + label** (greyscale-safe,
    design §3.2), the calm bordered unresolved panel, a mono provenance record, and a
    print stylesheet (running-footer disclaimer, risk tables never split).
  - **`pipeline/stages/assembly.py` — the I/O boundary.** `gather_inputs` reads every
    committed artefact (threshold, six specialists, architect, reviewer residual +
    unresolved, KB manifests, run provenance) into one bundle; `assembly` builds and
    writes `artefacts/assessment.ipynb` + `assessment.html`. Reads only committed state,
    so it re-runs identically on resume. The §12.3 PoC embed slot is built (sandboxed
    `<iframe srcdoc>`) and dormant until Brainstorm writes `brainstorm/poc.html`.
  - **`run.py` — terminal-COMPLETE finalisation.** `ASSEMBLY` slots in via the five
    stage→X maps (→ `COMPLETE`), and a new `_finalise_terminal` makes the driver set
    `run.json` `stage_status=complete` + `status.json` `overall_state=complete` and
    commit when a run first reaches COMPLETE/CONCLUDED — the signal the SPA's poll needs
    to see the run finish. Idempotent (a re-entry after completion is a no-op).
  - **Dependencies.** `nbformat` + `nbconvert` pinned in `pipeline/pyproject.toml` +
    `uv.lock`; the `governance.yml` job's `uv sync` picks them up with no workflow
    change. No execution stack is used (the notebook never runs a kernel).
  - **12 new tests** (`pipeline/tests/test_assembly.py`): reference dedup/resolution/
    unresolved-marking, the no-code-cells invariant, nbformat round-trip validity, the
    cell-plan contents, unresolved-omitted-when-none, gap-rendering, the self-contained
    HTML render (embedded HTML not escaped, chips, disclaimer inlined), the stage handler
    writing both artefacts, `gather_inputs` ordering §5–12 and excluding reviewer/human
    sections, and a driver end-to-end test (seed at ASSEMBLY → run → `COMPLETE`). Two
    REVIEW driver tests updated to the new terminal boundary. LLM-free throughout (§15).
- **`REVIEW` — the reviewer protocol, driven end-to-end (TECH_SPEC §5.1, §5.5,
  §11, §12.3/§12.4; Stage 3; this branch).** The heart-of-the-product audit
  stage. The pieces:
  - **`pipeline/agents/reviewer.py` — one Pro call per cycle, boundary-validated.**
    `run_reviewer(...)` gives the model the residual instrument tiers, the valid
    directive-target scope, the computed coverage checklist, the assembled specialist
    drafts (untrusted-wrapped, §9.2), the threshold and the outline, and returns
    `{coherence_findings, amend_directives, unresolved, residual}`. Two invariants are
    enforced at the boundary, the same "reject, don't repair" discipline the other
    agents use: (1) **a directive may only name a section its specialist owns** — an
    unknown specialist or an out-of-scope/wrong-owner section is rejected (§11.3
    structural write-scope); (2) **the reviewer never asserts a rating** — a `rating`
    key anywhere in `residual` is rejected, and each area's consequence/likelihood must
    be a valid instrument tier (§12.4). Accepts the §11.3 node-id form
    (`full.specialist.privacy`) or a bare id and normalises to the bare id used
    everywhere else.
  - **`prompts/reviewer.v1.md`** — registered under role `reviewer` → Pro. Encodes the
    coherence/contradiction brief, the amend-directive and unresolved-disagreement
    formats (§11.3/§11.4), the residual §12.3/§12.4 task, the untrusted-content
    discipline, and the two hard rules (never re-draft a section, never state a rating).
  - **`pipeline/stages/full.py` — the `review` handler.** Builds the **deterministic
    coverage checklist** (§11.1 — every §5–12 subsection is addressed/gapped/missing/
    human-action, a checklist walk not a judgement), then runs the **bounded ≤2-cycle
    loop** (§5.5): each cycle runs the reviewer, writes `full/reviewer/cycle_N.json`,
    and — if it emitted directives and a cycle remains — the targeted specialists amend
    their own directed sections via `run_specialist_amendment`. Conflicts still live at
    the cap become `unresolved.json` (§11.4). The **deterministic engine computes the
    residual** ratings + §12.4 overall from the reviewer's post-mitigation tiers
    (`full/reviewer/ratings_residual.json`) — the one place a residual rating comes into
    being (§10, §12.4). Also writes `coverage.json` and a readable `review.md` (the
    §12.3 table + coherence findings + unresolved block for ASSEMBLY).
  - **`pipeline/agents/specialist.py` — `run_specialist_amendment` + a shared loop.**
    The retrieval loop was refactored into `_drive_retrieval` (parameterised by a
    user-builder and a parse fn) so drafting and amendment share it. An amendment is
    **scoped to the directed sections only** (a subset of owned): its output may touch
    no other section, and it is merged over the prior draft so a directive cannot drop
    a specialist's other work (§11.3). Raises no new questions (§5.8). `SpecialistDraft.from_dict`
    rehydrates a committed draft for the merge. This capability is the reusable core
    `FULL_REVISING`/`USER_REVISION` will call next.
  - **`RunState.reset_review_cycles` + `run.py` table entries.** REVIEW is one
    checkpoint that re-runs its whole bounded loop on resume; the cycle counter is reset
    at entry so a failed prior attempt (whose increments §5.6 committed) cannot shorten
    the fresh loop or trip the cap. `REVIEW` slots into `_HANDLERS`/`_NEXT` (→ `ASSEMBLY`)/
    `_CHECKPOINT_OUTPUTS` (`ratings_residual.json`)/`_STAGE_FAIL_NODE` (`full.reviewer`)/
    `_STAGE_PHRASE` — a mostly table-entry addition (the loop lives in the handler, §5.5).
  - **22 new tests** (`pipeline/tests/test_review.py`): reviewer happy path + provenance,
    every directive write-scope rejection, the no-asserted-rating + missing-area +
    invalid-tier residual rejections, unresolved-shape validation, the deterministic
    coverage classification, `_compute_residual` hand-worked against the engine, the
    scoped amendment merge + out-of-scope/non-owned rejections, the stage handler
    (no-directives, amend-then-settle, cap-reached-→-unresolved, cycle-reset-on-entry),
    the review markdown, and two driver end-to-end tests — REVIEW alone and the whole
    `FULL_DRAFTING → ARCHITECT → REVIEW` chain in one dispatch, both stopping calmly at
    the unbuilt `ASSEMBLY`. LLM-free throughout (§15). 147 pipeline tests total green;
    ruff clean.
- **`ARCHITECT` — the Implementation Plan appendix stage, driven end-to-end
  (TECH_SPEC §5.1, §12.1; PROJECT_BRIEF §5.5; Stage 3; this branch).** The pieces:
  - **`pipeline/agents/architect.py` — a single Pro call, no retrieval loop.**
    `run_architect(...)` gives the model the outline, the completed threshold
    assessment, and every specialist's drafted sections/citations/gaps (all
    untrusted-wrapped, §9.2), plus an exhaustive **traceable-sections list**, and
    returns `{overview, steps[]}`. Two boundaries are enforced at the validation
    boundary, echoing "models argue, code computes" (§10) and structural
    write-scope (§9.3): (1) the architect's output has **no section-content
    field**, so it structurally *cannot* restate or re-draft a specialist's owned
    section (§5.1 "cannot modify other content") — it writes only the appendix;
    (2) **every step must trace to a `(specialist, section)` pair the specialist
    actually drafted** — a trace to an un-drafted, gapped, or wrong-owner section
    is *rejected*, not ignored. That is the machine-checkable half of §5.5's "the
    plan demonstrably answers the assessment rather than existing beside it": a
    step cannot implement a control the assessment never made.
  - **`prompts/architect.v1.md`** — registered in `prompts/manifest.yml` under
    role `architect` (resolving to Pro per `config/models.yml`). Encodes the
    architecture/sequencing/traceability brief (§5.5), the untrusted-content
    discipline, the "you never assert or change a rating / never re-draft a
    section" rules, and the strict-JSON output shape. Optional `mermaid` diagrams
    and code snippets are allowed inside a step's markdown `detail` (rendered
    later at ASSEMBLY, not by the architect — §12.3).
  - **`pipeline/stages/full.py` — the `architect` handler.** Loads the six
    specialist JSONs, renders them into the single context block the architect
    reads, builds `valid_targets` (each specialist → its **drafted** section ids,
    gaps excluded), narrates the design-brief log line ("Writing an
    implementation plan that answers the risks the specialists raised."), runs the
    agent, and writes `full/architect.json` (structured + provenance) +
    `full/architect.md` (the rendered appendix, each step footed with its
    `*Answers: [Friendly name, §x] — mitigation*` traceability line).
  - **`pipeline/run.py` — table entries only, no new machinery.** `ARCHITECT`
    slots in via `_HANDLERS`/`_NEXT` (→ `REVIEW`)/`_CHECKPOINT_OUTPUTS`
    (`full/architect.md`)/`_STAGE_FAIL_NODE` (`full.architect`)/`_STAGE_PHRASE`.
    The `_resolve_next` FULL_DRAFTING branch and `_NEXT[FULL_CHECKPOINT-skip]`
    already routed the happy path here; now the handler exists, so the driver
    runs it and stops calmly at the unbuilt `REVIEW`.
  - **13 new tests** (`pipeline/tests/test_architect.py`): the happy path +
    provenance, multi-trace-across-specialists, and every validation rejection
    (missing overview, empty steps, step with no detail, step with no trace, trace
    to an unknown specialist, trace to a section another specialist owns, trace to
    a *gapped* section) — plus the stage handler writing both artefacts and
    completing its node, the context actually containing all six specialists +
    the traceable-sections list, and a driver end-to-end test (seed at ARCHITECT →
    run → stop at REVIEW). Two `test_full_drafting` driver tests updated to the new
    boundary (happy path now runs the architect and stops at REVIEW). LLM-free
    throughout (§15).
- **`FULL_DRAFTING` — the six-specialist retrieval + draft stage, driven
  end-to-end (TECH_SPEC §5.1, §8.1, §9.3; Stage 3; prior branch).** The pieces:
  - **`pipeline/agents/specialist.py` — the retrieval tool loop + output
    validation.** `run_specialist(...)` gives the model its owned-section
    instrument context, its KB index, the outline, and the completed threshold
    assessment, then loops: each round the model returns exactly one JSON
    object — `{"action":"fetch"|"search",...}` or `{"action":"draft",...}` —
    resolved against the real KB (`retrieval.KB`, no native LLM tool-calling
    used; the protocol is a plain JSON turn since `llm.py`'s seam is
    system+user→text). Bounded by `config/retrieval.yml` (`fetch.max_rounds`,
    `fetch.max_total_tokens`); on cap, one **forced final round** demands a
    draft from whatever was fetched (§8.1's literal rule) rather than looping.
    A pre-fetch **seed search** (owned section titles + prompts, §8.1 step 2)
    runs before round 1 so grounding never starts empty. Every fetch/search
    emits a `retrieval` status event when a `StatusModel`+`node_id` are given.
    Validation enforces write-scope structurally (§9.3): `sections`/
    `citations`/`gaps` keys outside the specialist's owned set are **rejected**,
    every owned section must be either drafted or gapped (never both, never
    neither), a `yes_no_na` section must open with Yes/No/Not applicable, and
    the ≤3-questions cap (CLAUDE.md §3) is enforced with a required batch-level
    `why` whenever any question is raised.
  - **`prompts/specialist.v1.md`** — one prompt shared by all six specialists
    (registered in `prompts/manifest.yml` under role `specialist`, resolving to
    Flash per `config/models.yml`); what differs per call is the instrument
    context, KB index, and KB, all assembled by `specialist.py`, not the
    prompt text. Encodes the fetch/search/draft JSON protocol, the
    draft-or-gap discipline, the untrusted-content wrapping for the outline
    *and* the threshold assessment (§9.2 — the threshold text is
    pipeline-authored but still derived from user content, so it is wrapped
    too, not treated as trusted), and the structural write-scope rule.
  - **`agents/prompting.py` additions.** `specialists()`, `specialist_owned_sections()`,
    `specialist_friendly_name()`, `specialist_instrument_context()` (the DTA
    question text for one specialist's owned sections, grouped by containing
    §5–12 section — the tool's own wording, verbatim, mirroring how
    `threshold_instrument_context()` already worked for the generalists), and
    `specialist_seed_terms()`. All derive from `instrument/sections.json` +
    `instrument/questions.json` — no new encoding of the ownership fact.
  - **`pipeline/stages/full.py` — the `FULL_DRAFTING` handler.** Runs all six
    specialists (sequentially, matching the existing `threshold_drafting`
    precedent — TECH_SPEC §5.4's "concurrent within a job" is aspirational and
    not yet true of either drafting stage), writes
    `full/specialists/<id>.json` + a readable `.md` per specialist, and — iff
    at least one specialist raised a question — assembles and writes
    `full/questions.json` in the exact §6.4 batched shape (`batch_id`,
    per-specialist `{node_id, friendly, why, items}`, `counts`), narrating each
    with a `question_raised` event. `SPECIALISTS` is a hardcoded tuple (the
    established pattern in this codebase for section-id constants derived
    from, but not re-loaded from, `instrument/sections.json` at import time —
    see `stages/threshold.py`'s `_RISK_TITLES`); a test asserts it matches
    `sections.json` exactly.
  - **`pipeline/run.py` — two new pieces of general driver machinery, not
    FULL_DRAFTING-specific.** (1) `_resolve_next(stage, run_dir)`: the first
    place the driver needed a *runtime-conditional* next stage rather than a
    fixed `_NEXT` table entry — after `FULL_DRAFTING`, the next stage is
    `FULL_CHECKPOINT` if `full/questions.json` was written, or `ARCHITECT`
    (skipping both the checkpoint pause and `FULL_REVISING`, which exists only
    to act on answers) if not — used at both the "just ran the handler" and
    the "checkpoint already exists, resuming" call sites, so idempotent resume
    branches the same way a fresh run would. (2) `_PAUSE_SETUP`: a stage→setup
    hook run once when a pause stage is first entered, needed because
    `FULL_CHECKPOINT` (unlike `THRESHOLD_REVIEW`, which pauses via
    `overall_state` alone) must additionally set its node to `waiting_user` and
    attach the `questions` payload (§6.4) — `_setup_full_checkpoint` reads back
    the `full/questions.json` `FULL_DRAFTING` already wrote. `StageContext`
    gained a `kb_root: Path | None` field (default `None` ⇒ resolve the real
    repo `kb/`) so tests can inject fixture KBs without touching production
    resolution; `run_pipeline()`/`_drive()` thread it through.
  - **19 new tests** (`pipeline/tests/test_full_drafting.py`): the retrieval
    tool loop (search-then-draft, forced-final-round, and the "still no draft
    after forcing" loud failure), every write-scope/gap/yes-no-prefix/question-cap
    validation rejection, the stage handler writing all six specialists with
    and without a raised question, and driver-level tests — the
    `FULL_CHECKPOINT` pause payload, the no-questions path correctly *skipping*
    the checkpoint (landing at `ARCHITECT`, which fails calmly since it isn't
    built yet — the point of the test is the skip, not the failure), idempotent
    resume (re-dispatch does not re-call the model once all six specialist
    files exist), and calm-failure node attribution when one specialist errors
    mid-bloom (the generic active-node scan in `run.py`'s `_failing_node`
    correctly identifies the failing specialist, not a fallback default).
    Fixture KBs are schema-only (`retrieval.db.write_kb([], ...)`) — real
    SQLite/FTS5, zero documents, so the seed-search path runs for real without
    needing corpus content in the test; separately verified once by hand
    against a real committed KB (`kb/ethics.sqlite`) to confirm the loop also
    works against actual corpus data. 112 pipeline tests total green; ruff
    clean.
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
`governance.yml`) are **done** — see Done → *Backend API + dispatch + status
proxy*. The pipeline is live-dispatchable end-to-end through the threshold
path, and `POST /api/runs/{id}/threshold/route` can dispatch onward to
`FULL_DRAFTING`, which the driver implements, and now **`ARCHITECT`** as well
(this branch — see Done → *`ARCHITECT`* / *`FULL_DRAFTING`*). Next concrete
steps, in rough dependency order:

1. **The checkpoint-answer path (`FULL_REVISING` + `POST /api/runs/{id}/answers`,
   §5.1, §7).** The happy path is complete end-to-end (`FULL_DRAFTING → ARCHITECT →
   REVIEW → ASSEMBLY → COMPLETE`). What remains on the full-assessment side is the
   branch a `FULL_CHECKPOINT` pause takes when a specialist raised a question:
   - **`FULL_REVISING`** — each specialist that raised a question revises its own
     sections once in light of the answers; skipped questions become gaps. **Now a
     thin wrapper over `run_specialist_amendment` (built this branch)** — call it per
     specialist with the answers as the directive context (instead of a reviewer
     ruling) and the raised question ids as the target sections. Register it in
     `run.py`'s five stage→X maps with `_NEXT[FULL_REVISING] = ARCHITECT`; the
     `_resolve_next` FULL_DRAFTING→FULL_CHECKPOINT branch and a `_NEXT[FULL_CHECKPOINT]`
     entry still need wiring so the checkpoint resumes into `FULL_REVISING`.
   - The backend **`POST /api/runs/{id}/answers`** endpoint (TECH_SPEC §7)
     still doesn't exist — needed before a real user can act on a
     `FULL_CHECKPOINT` pause and dispatch `resume_from=FULL_REVISING`. Small:
     validate against `full/questions.json` question ids, commit
     `full/answers.json`, dispatch. Natural to build alongside `FULL_REVISING`
     rather than before it, since there's nothing to resume into yet without it.
   - **`USER_REVISION`** (§5.8) — the ≤2 post-COMPLETE full-assessment revisions:
     reviewer triage → targeted specialist amendment (again `run_specialist_amendment`)
     → one reviewer verify pass → `ASSEMBLY` re-runs (archiving the superseded artefacts
     to `artefacts/superseded/rev_<N>/` first). `RunState.record_revision("full")` and
     the revision caps already exist; ASSEMBLY already rebuilds idempotently.
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

- **ASSEMBLY renders via nbconvert's `basic` template wrapped in a hand-written
  self-contained HTML document, not a full custom nbconvert template (this branch,
  `assembly/render.py`).** §12.5 mandates "a custom template/stylesheet replacing the
  default theme"; nbconvert's own template system (jinja template dirs, `--template`)
  is fiddly and couples the render to nbconvert's internal template layout. Instead the
  `basic` template emits just the rendered cell bodies (no Jupyter chrome), and this
  module wraps them in a `<!doctype html>` document carrying the stylesheet **inlined**
  — so the report is a single portable file with no external font/script/style fetch
  (design §8's "a document taken seriously," and the artefact-embedded-elements contract,
  design §10). Reversible: a true nbconvert template can replace the wrapper later
  without changing the notebook or the CSS.
- **Structured report blocks are HTML embedded in markdown cells, not nbformat raw
  cells (this branch, `assembly/notebook.py`).** The notebook needs class-tagged blocks
  (title, risk table, unresolved panel, provenance) for the stylesheet to target; raw
  cells render inconsistently across nbconvert exporters, whereas a markdown cell's
  block-level HTML passes through mistune reliably (verified: the risk `<table>` renders
  unescaped). Prose stays plain markdown. The notebook has **zero code cells** — a test
  asserts it, keeping the §12.1 "non-executable" guarantee structural.
- **The residual §12.5 governance-review flag keys on the residual overall, not the
  inherent (this branch, `assembly/notebook.py`).** §12.5 is a human action "where the
  agency's governance policy requires it"; the report flags a mandatory referral when the
  **post-mitigation** overall is High (the risk that actually remains), and otherwise
  states 12.5 as a conditional human action. The threshold's inherent-High governance
  flag (routing.json, §12.5) still stands at the threshold stage; this is the residual
  counterpart, consistent with "the residual is what the reader acts on."
- **Reaching COMPLETE is finalised by the driver, not the stage handler (this branch,
  `run.py::_finalise_terminal`).** The §5.1 state table lists COMPLETE as a terminal
  state but no handler; the driver previously just returned on any terminal stage without
  setting `overall_state=complete`. `_finalise_terminal` now sets `stage_status=complete`
  + `overall_state=complete` and commits the first time a run reaches COMPLETE/CONCLUDED
  — the signal the SPA's poll needs to see the run finish (§7). Kept in the driver (not
  the ASSEMBLY handler) because it is the generic terminal-transition concern, shared
  with the threshold-CONCLUDED path, and idempotent (a re-entry after completion is a
  no-op).
- **A dangling citation (a `short_name` with no matching manifest document) is rendered
  as an unresolved reference, not dropped (this branch, `assembly/references.py`).**
  Citation integrity is never traded (CLAUDE.md §2); silently omitting a citation whose
  source can't be resolved would hide a real problem. The reference list keeps the entry,
  marked "(source not found in corpus manifest)", so the gap is visible to a human rather
  than erased.
- **REVIEW is one pipeline checkpoint that re-runs its whole bounded ≤2-cycle loop on
  resume — not a per-cycle checkpoint (this branch, `stages/full.py::review`,
  `RunState.reset_review_cycles`).** TECH_SPEC §5.5 says "each cycle commits so a death
  mid-review resumes at the right cycle," but the `run.py` driver's model is one commit
  per stage (extend-by-table-entry, §5.3 keyed on output-file existence), and REVIEW's
  in-loop `review_cycles` increments are not committed until the stage's checkpoint. So
  a death mid-REVIEW discards the uncommitted loop state and re-runs REVIEW from scratch
  — safe because the loop is bounded and idempotent (it overwrites its own `cycle_N.json`
  and, in a fresh Actions container, the specialist drafts revert to their
  FULL_DRAFTING-committed state). The one hazard: §5.6's `fail()` **does** commit
  `run.json` (with any increment) on a mid-loop error, which on resume would shorten the
  fresh loop or trip the cap. Closed by `reset_review_cycles()` at REVIEW entry — the cap
  is per-REVIEW-execution, and only the execution that checkpoints ever "counts."
  Reversible: if per-cycle durability is later wanted, the driver would need a
  sub-stage checkpoint mechanism, which `REVIEW`/`USER_REVISION` could share.
- **Coverage is computed deterministically in the stage and handed to the reviewer as
  context; the reviewer does not compute it (this branch, `_build_coverage`).** §11.1 is
  explicit that "a missing question is a deterministic finding" and coverage "is a
  checklist walk, not a judgement call." So the stage walks the full-assessment
  subsection inventory (`instrument/sections.json` ownership × the specialist drafts) and
  classifies each as addressed/gapped/missing/human-action in code; the reviewer receives
  the result so it does not paper over a gap, but the finding itself is code's, not the
  model's. 12.3/12.4 (reviewer-owned) count as addressed because REVIEW produces the
  residual; 12.5 (human_action) is flagged, never drafted.
- **The residual §12.3/§12.4 rating is a provable code output of the reviewer's tiers,
  exactly like the threshold path (this branch, `_compute_residual` + `agents/reviewer.py`).**
  §5.1 REVIEW says "residual 12.3/12.4 computed by the engine" without a mechanism. The
  reviewer emits post-mitigation consequence + likelihood + rationale per §3 area (its
  argument); `pipeline/rating/` computes every residual rating and the §12.4 highest-wins
  overall (`overall_residual`). The reviewer schema **forbids a `rating` key** and the
  boundary rejects one — the same "models argue, code computes" invariant as the threshold
  reconciler (§10). Residual is taken from the **last** reviewer cycle's tiers (which read
  the settled draft), so it always reflects the assessment as it finally stands.
- **A reviewer amend directive is scoped to the sections it names, and the specialist
  amendment output is scoped to those sections and merged over the prior draft (this
  branch, `run_specialist_amendment` + `_merge_amendment`).** §11.3 says "only the named
  specialist may act, and only on its own sections." Enforced twice: (1) the reviewer
  boundary rejects a directive naming a non-owned section; (2) the amendment's own output
  may contain **only** the directed sections (a subset of owned) — any other key is
  rejected — and the merge replaces exactly those, leaving every other section, citation
  and gap untouched. So an amendment cannot silently drop or rewrite a specialist's other
  work. Amendments raise no new questions (skips → gaps, §5.8). The bounded retrieval loop
  is shared with fresh drafting via `_drive_retrieval` (one loop, two entry points) rather
  than duplicated.
- **Directives still live when the ≤2 cap is reached become unresolved disagreements, not
  forced amendments (this branch, `_directives_as_unresolved`).** §11.4 says conflicts
  after cycle 2 "are written to `unresolved.json` rather than forced." When the second
  reviewer cycle still emits directives, they are not applied — they are converted into the
  §11.4 unresolved shape (the ruling as the topic, the conflicting claims as the two
  positions) alongside any the reviewer itself flagged as unresolved. Honest disagreement
  over manufactured consensus (design §8).
- **The architect emits structured `{overview, steps[]}` JSON (→ rendered to
  `full/architect.md`), and its traceability is validated against the real
  ownership map — not free-form prose (this branch, `agents/architect.py`).**
  TECH_SPEC §5.1 names only `full/architect.md` as the output and describes
  "explicit traceability to specialists' mitigations" without a mechanism. A
  free-form markdown blob would make §5.5's "the plan demonstrably answers the
  assessment rather than existing beside it" unenforceable — nothing would stop a
  step from citing a control no specialist made, or the architect from quietly
  re-drafting a section. So the architect returns a structured plan whose every
  step carries a non-empty `traces_to` of `(specialist, section)` pairs, and the
  agent boundary **rejects** any trace to a section that specialist did not
  actually draft (out-of-scope, wrong-owner, or gapped) — the same "reject, don't
  repair" discipline the specialists and threshold agents use (§9.3, §9.4).
  Because the output has no section-content field, the architect *structurally*
  cannot modify other content (§5.1). `full/architect.json` is kept alongside the
  `.md` as structured provenance (mirroring `reconciled.json`+`threshold_assessment.md`
  and `specialists/<id>.json`+`.md`); idempotent resume keys on `full/architect.md`,
  the spec-named checkpoint output. Reversible: nothing downstream reads the JSON
  shape yet (ASSEMBLY will), so the fields can still change.
- **`ARCHITECT` needed no new `run.py` machinery — it is the worked example of the
  "extend by table entry" design.** Unlike `FULL_DRAFTING` (which needed
  `_resolve_next` and `_PAUSE_SETUP` the first time a successor was runtime-
  conditional and a pause needed extra setup), `ARCHITECT` has a fixed successor
  (`REVIEW`) and no pause, so it slots in purely through the five stage→X maps.
  This confirms the driver's stage-agnosticism holds for a plain sequential stage;
  `FULL_REVISING`/`REVIEW` will reuse `_resolve_next`/`record_review_cycle` where
  they genuinely branch, not reinvent driver plumbing.
- **The specialist retrieval tool loop is a plain JSON action protocol, not
  native LLM function-calling (prior branch, `agents/specialist.py`).**
  TECH_SPEC §8.1 describes "the model calls two deterministic tools" without
  specifying the mechanism; `llm.py`'s seam (`Transport.generate(system, user)
  → text`) has no function-calling support and adding one would mean a second,
  provider-specific protocol on top of the already-working `complete_json`
  path. Instead each round the model returns one JSON object —
  `{"action":"fetch"|"search",...}` or `{"action":"draft",...}` — which the
  wrapper resolves and feeds back as history text. Simpler, provider-agnostic,
  and consistent with how the threshold agents already work (§10's "models
  argue, code computes" pattern extends naturally to "models request, code
  fetches"). Reversible: if Gemini function-calling is wanted later, only
  `agents/specialist.py`'s loop changes — the KB/index/prompt content does not.
- **A specialist's owned section must be either drafted or gapped — never
  both, never neither — enforced at the validation boundary
  (`agents/specialist.py::_parse_draft`).** TECH_SPEC §11.1's coverage rule
  ("every question id... substantively addressed... OR present in gaps.json")
  is stated as a reviewer-time check; applying the same either/or discipline
  at *draft* time (not just at review time) closes the gap earlier and gives
  the reviewer a clean invariant to build on rather than a free-for-all it has
  to reconstruct.
- **`yes_no_na` sections must open with "Yes"/"No"/"Not applicable"
  (`agents/specialist.py`), enforced by string-prefix check, not a separate
  structured field.** The instrument's own `response_types` note
  (`questions.json`) says these sections are "select one of Yes/No/Not
  applicable, plus an explanation" — CLAUDE.md's "citation quality and
  instrument fidelity are never traded for polish or speed" reads as covering
  this too: an unprefixed answer that reads as evasive fails the tool's own
  contract. Kept as a markdown-text convention rather than a
  `{answer, explanation}` structured field to stay consistent with the
  generalists' section format (free markdown, §5.1) and avoid a second
  section-content shape in the codebase.
- **The `questions.why` field sits once per specialist batch, not once per
  question item (`agents/specialist.py`, `stages/full.py`).** TECH_SPEC §6.4's
  worked example shows `why` at the per-specialist level in the *runtime*
  `status.json` questions payload; the specialist's own draft JSON schema
  mirrors that shape directly (`{"questions": {"why": "...", "items": [...]}}`)
  so `stages/full.py`'s payload assembly is a straight copy, not a
  restructuring — one shape, not two.
- **`FULL_DRAFTING`'s specialists run sequentially, not concurrently
  (`stages/full.py`), matching `threshold_drafting`'s existing precedent.**
  TECH_SPEC §5.4 describes "async fan-out... within a single Actions job" as
  the target, but the codebase's one existing multi-agent stage
  (`THRESHOLD_DRAFTING`'s two generalists) is already a plain sequential loop,
  not async — introducing concurrency only for the new six-specialist stage
  would leave two different concurrency models for the same kind of fan-out.
  Deferred as a genuine follow-up (not a silent shortfall): both stages are
  candidates for the same async treatment together, and neither's tests assume
  sequential execution.
- **`stages.full.SPECIALISTS` is a hardcoded tuple, asserted against
  `instrument/sections.json` by a test, not loaded from it at import time.**
  Follows the precedent already set by `stages/threshold.py`'s `_RISK_TITLES`
  and `_SECTION_TITLES` (hardcoded, not re-derived from `instrument/
  questions.json` at import time) — avoids file I/O as a module-import-time
  side effect, at the cost of one more place that must agree with the JSON
  source; closed by `test_specialists_tuple_matches_sections_json`.
- **`run.py` gained `_resolve_next()` (runtime-conditional next stage) and
  `_PAUSE_SETUP` (per-pause-stage entry hook) as general driver machinery, not
  `FULL_DRAFTING`-specific helpers.** Both were needed the first time a stage's
  successor depends on what the stage actually produced (`FULL_DRAFTING` →
  `FULL_CHECKPOINT` or `ARCHITECT`, depending on whether any specialist raised
  a question) and the first time a pause needs more than the generic
  "AWAITING_USER + overall_state=paused" treatment (`FULL_CHECKPOINT` also
  sets its node `waiting_user` and attaches the `questions` payload). Built as
  small stage→callable maps, the same shape as the existing `_HANDLERS`/
  `_STAGE_PHRASE` tables, so `REVIEW`'s internal cycles or `USER_REVISION`'s
  three-step resume (§5.5, §5.8) can reuse the same mechanism rather than
  inventing a third.
- **`StageContext` gained an optional `kb_root: Path | None` field** so tests
  can inject a fixture KB directory without monkeypatching a module-level
  path-resolution function. `None` (the production default) resolves the real
  repo `kb/` the same way every other `_repo_root()`-style helper in this
  codebase does (walk up from the calling module's file until a marker
  directory is found).
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
