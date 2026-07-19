# Build status

## Current stage

**This branch (`claude/reword-public-availability-warning-8137wz`): reworded the usage warning
to drop the "sensitivity ceiling is OFFICIAL" claim (PROJECT_BRIEF §3; TECH_SPEC §4/§12.2;
DESIGN_BRIEF §4.1; CLAUDE.md §2).** Tom asked for the pre-input warning to disclose public
availability and ask users to keep sensitive material out, **without** the system claiming any
particular sensitivity level it is accredited to handle. The old copy ("Keep it at OFFICIAL —
no OFFICIAL: Sensitive, nothing security classified…") asserted a ceiling Windtunnel has no basis
to claim; the new copy leads with the actual, verifiable fact (everything is public and
world-readable) and asks users to make their own judgement call ("don't put in anything you
wouldn't be comfortable seeing posted in the open"), still explicitly ruling out classified,
sensitive, and personal information. **This was a genuine document-and-code consistency fix, not
just a copy change (CLAUDE.md §2):** the same "at or below OFFICIAL" claim was baked into the
`run.json` `attestation` schema and rendered verbatim into every generated notebook/report's
provenance cell — rewording only the gate would have left the audit trail still asserting a
sensitivity ceiling the gate no longer claims. Fixed at the source:
- **`PROJECT_BRIEF.md` §3** — the "sensitivity ceiling is OFFICIAL" decision reworded to a
  public-disclosure-only warning; this revises a decision the brief had marked fixed, done here
  on Tom's explicit instruction (governs intent, so the correction lands here first).
- **`TECH_SPEC.md`** — the `run.json` `attestation` example dropped `sensitivity_ceiling`, now
  just `{"attested": true}`; §12.2's provenance-cell description reworded to match.
- **`DESIGN_BRIEF.md` §4.1** — the three-point gate content and ASCII mockup reordered (public
  disclosure leads) and reworded (no OFFICIAL claim); the "public repo" callout note updated.
- **`pipeline/statefile.py`** — `RunState.attestation` default and `RunState.new()` dropped the
  `sensitivity_ceiling` param/field entirely; attestation is now just `{"attested": bool}`.
- **`pipeline/stages/assembly.py`** / **`pipeline/assembly/notebook.py`** — stopped threading
  `sensitivity_ceiling` into the report data bundle; the rendered provenance sentence now reads
  "The submitting officer confirmed/did NOT confirm that these inputs contain no sensitive,
  classified, or personal information, appropriate for this public, world-readable repository" —
  no ceiling claim, same audit intent.
- **`frontend/src/components/UsageWarningGate.tsx`**, **`README.md`**, **`SYSTEM_OVERVIEW.ipynb`**
  — same reword applied to the live UI copy and the two narrative docs.
- **Historical `runs/*/run.json` and `runs/*/artefacts/*` left untouched** — they are the
  immutable record of what was actually attested/rendered for past runs, not live schema.

**Verified:** pipeline 213 tests green (2 updated: `test_new_run_defaults` attestation shape,
`test_assembly` report-data fixture), ruff clean. Backend 135 tests green (untouched — the
per-upload `acknowledge_no_sensitive` flow never named OFFICIAL, so no change needed there).
Frontend 55 tests green (1 updated: `App.test.tsx`'s gate-copy assertions now look for "this is
public" / "nothing sensitive" instead of "keep it at official"), build + strict typecheck + lint
(0 err, 1 pre-existing accepted warning) + format clean.

**Prior branch (`claude/concurrent-specialists-aqb0t9`, merged to main): the specialists — and now the two
threshold generalists — run concurrently — the §5.4 fan-out the tech spec always mandated,
replacing the serial one-after-another loops
(TECH_SPEC §5.4, §13, §14; CLAUDE.md §3 "one poll fully determines visible state").** Tom asked
for three specialists drafting at once. TECH_SPEC §5.4 already required exactly this
("FULL_DRAFTING/FULL_REVISING … run their agents concurrently … respecting the rate-limit budget
(§13)"), so this is spec-alignment, not a new design. The three specialist loops — `full_drafting`
(all six), `full_revising` (the questioners), and `_apply_amendments` (REVIEW + USER_REVISION
targets) — now build per-specialist `_SpecialistTask`s and fan them out through one shared runner
(`_run_specialist_tasks`, `pipeline/stages/full.py`) over a `ThreadPoolExecutor` bounded by
**`specialist_concurrency: 3` in `config/budgets.yml`** (a §13 rate knob, one owner; raise toward
6 as Gemini quota allows — design §7.2's "six bloom at once" is the unthrottled ideal). The
threading discipline is strict and structural: **workers compute and narrate only** (their own KB
connection, the shared thread-safe `StatusModel`, the shared budget-locked `LLMClient`); **every
file write and every commit stays on the coordinating thread** — each task's `finish` runs there
as its worker completes, so drafts are still written + pulse-committed one by one (per-draft §5.3
resume granularity preserved) and the §14 single-writer commit property holds by construction.
While workers run, `status.pulse` is swapped for a `_DeferredPulse` (workers' publish requests are
flags the coordinator drains every ≤2s and publishes through the driver's real pulse). Supporting
hardening: `StatusModel` gained one RLock making every mutation atomic — the §6.3 node+event
coupling can never tear and event ids (minted from log length) stay unique/monotonic under
concurrent narration; `CallBudget.charge` is now an atomic check-and-increment. Failure semantics:
first worker error cancels unstarted tasks (they stay `pending`, re-run on resume), running ones
finish and are kept (their committed drafts honoured by idempotent skip), then the error propagates
to the §5.6 calm-failure path. **Pipeline: 219 tests green (213 prior — two rewritten: the
specialist-failure driver test now asserts concurrent semantics, and two FIFO-scripted fixtures
became content-routed handlers since queue order is scheduling-dependent under the fan-out — plus 6
new: barrier-proven 3-wide overlap + bound + event-id monotonicity, single-writer commit-thread
proof, partial-resume skip keeping committed questions, atomic budget under 8 threads, two-specialist
concurrent amendment via REVIEW, budgets-knob read), 8 consecutive full-suite runs flake-free, ruff
format + check clean.** TECH_SPEC §5.4 extended with one sentence naming the knob and the
single-writer rule. Backend/frontend untouched — `status.json`'s whole-graph `nodes` map was built
for several actives at once (the Chamber animates it already). **Second commit: the generalists
too (Tom's follow-up).** The fan-out machinery was extracted to `pipeline/stages/fanout.py`
(`AgentTask`, `run_agent_tasks`, `DeferredPulse`, `fanout_width` — same knob; the pair of 2 sits
under the bound of 3 either way) and `threshold_drafting` now fans both assessors out, delivering
design §7.2's "Generalist A and Generalist B go active at the same time". One semantic note: the
two generalists are symmetric by construction (identical prompts — divergence is the signal), so
which model answer lands in slot a vs b is scheduling-dependent; that's meaningless in production
(higher-wins is commutative, `divergence.json` stays a faithful record of both inputs) but it means
test transports must not script the pair as an ordered FIFO. **Pipeline after both commits: 220
tests green (1 new: barrier-proven simultaneous generalists with assignment-agnostic outcome
checks; 2 rewritten: the failure-resume test's handler now counts under a lock and asserts
assignment-agnostically, and the mid-stage-pulse test now expects the §5.4 reality — the drafted
pair lands before the reconciler starts, rather than "A active while B pending" which encoded the
old serial order), 10 consecutive runs of the concurrency-sensitive files flake-free, ruff clean.**

**Prior branch (`claude/file-upload-not-found-4cgk43`): the "Not Found" file-upload bug — diagnosed
as a stale backend deploy, with a graceful-degradation frontend fix (TECH_SPEC §7; CLAUDE.md §9).**
Tom reported that attempting a Brainstorm file upload shows a red **"Not Found"** above the Upload
button. Diagnosis: **this is not a code bug in the request path.** The frontend POSTs
`/api/runs/{id}/brainstorm/upload` and the backend registers exactly that route — I booted the app
with a fake store and the exact URL + body the SPA sends returns **200** (CORS preflight 200 too),
and all 135 backend upload tests pass. The bare string **"Not Found"** is Starlette's *default* 404
detail, which fires only when **no route matches** — the backend's own 404s carry real text ("No
run found for code …"). `brainstorm_upload` landed in commit `f9f2b0d` (the file-upload PR, merged
as #31). So the **deployed Render backend is running a build older than that commit** and has no
`/brainstorm/upload` route: the file-upload PR redeployed the frontend (Pages workflow) but the
backend on Render was not redeployed — exactly the **CLAUDE.md §9 hazard** ("Render auto-deploy is
OFF or watch-path-scoped"). **The real fix is Tom redeploying the Render backend** (see *Blocked on
Tom*); merging a backend commit to `main` also fixes it *iff* Render's auto-deploy is watch-scoped
to `backend/**`. **The code change this branch makes** is the honest degradation the symptom
deserves: `frontend/src/routes/Brainstorm.tsx`'s `describe()` now translates a *bare* unmatched-route
404 ("Not Found") into "The server didn't recognise the request to … — it may be running an older
version that hasn't been updated yet. Please try again shortly, or type your idea into the chat
instead." Meaningful backend 404s ("No run found for code …") are passed through untouched (only the
naked framework default is rewritten), so the fix is targeted and applies to any endpoint a stale
backend is missing, not just upload. **Frontend: 55 tests green (54 prior + 1: bare-404 →
actionable message), build + strict typecheck + lint (0 err, 1 pre-existing accepted warning) +
format clean.** Backend/pipeline untouched. No document contradiction to fix.

**Prior branch (`claude/brainstorm-file-upload-ybgzdb`): file upload in Brainstorm — a public
servant can upload a file instead of chatting, in three formats (TECH_SPEC §7, §9.2, §12.3/§12.4;
CLAUDE.md §3).** A new `POST /api/runs/{id}/brainstorm/upload` endpoint (valid only at
`BRAINSTORM`, like the other brainstorm endpoints) accepts a decoded-text file with a `format` and
two acknowledgements, and dispatches on format:

1. **Plain text → seed material (the primary path).** Fed through the interviewer
   (`ingest_seed_material`, a thin sibling of `run_interviewer` sharing its prompt + `_parse`)
   **exactly as a long first message would be**, so it populates outline sections; committed like a
   normal turn (outline stays the single source of truth, CLAUDE.md §3; the upload recorded as a
   user turn, the interviewer's summary as the reply). The document is wrapped as untrusted content
   inside the agent (§9.2).
2. **Mermaid (`.mmd`) → the run's `flow-map.mmd`, framed as starting material.** Validated with the
   same `validate_mermaid` the generator uses (extracted to public), committed, and the source
   returned so the SPA does the existing client-render-then-post-SVG round-trip (CLAUDE.md §9). No
   LLM call. The additional starting-material acknowledgement gates this format.
3. **HTML → the run's `poc.html`.** Validated as an HTML document but with the §12.4
   limitations-banner requirement **relaxed for a user upload** (`validate_poc_html(...,
   require_banner=False)`) — a public servant supplying their own mock is exempt. Rendered in the
   existing `sandbox=""` iframe. No LLM call.

Both acknowledgements are enforced server-side (the authoritative check) **and** client-side (the
Upload button stays disabled until given): every upload confirms no sensitive information (the repo
is public, brief §3); a Mermaid upload additionally acknowledges starting-material treatment. The
licence gate (§8) never applies to a user submission — this is a user artefact, not a corpus
document. **Also (Tom's ask):** the flow-map panel now has an **Open in a new tab** button (the
in-canvas preview is small) — the client-rendered SVG is opened full-size via a blob URL.
**Frontend-visible surface:** a collapsible "Or upload a file instead" affordance under the
conversation (`FileUpload.tsx`), format auto-detected from the extension with a manual override,
routing the result to the surface that now holds it (outline / map tab / PoC tab). No pipeline,
contract-breaking, or integrity-invariant change. **Backend: 135 tests green (122 prior + 13
upload: validators ×3, plain-text ingest + untrusted-wrap ×2, Mermaid commit/ack/reject ×3, HTML
commit/reject ×2, shared ack/empty/stage-guard ×3), ruff clean. Frontend: 54 tests green (51 prior
+ 3 upload: plain-text seed, Mermaid double-ack + render, HTML→PoC), build + strict typecheck +
lint (0 err, 1 pre-existing warning) + format clean.** **No document contradiction to fix** — §7
did not enumerate an upload endpoint but the change sits squarely inside its brainstorm surface and
holds every §3 invariant. **What remains unchanged:** a first live Gemini run is still the only
untested seam (the plain-text ingest's live *judgement*; the whole path is unit-tested LLM-free).

**Prior branch (`claude/windtunnel-governance-nodes-h9q4bq`): the knowledge plane — the
specialists' knowledge bases are now depicted as nodes in the Chamber graph, closing the
biggest gap between the real governance page and the PoC (`frontend/windtunnel_agent_telemetry.html`)
(DESIGN §7.2; CLAUDE.md §3, §9).** Tom asked to bring the real governance node network closer
to the PoC, flagging the missing specialist **knowledge bases as nodes** as the most important
piece. Restored, plus the surrounding PoC structure. Frontend-only; no backend, pipeline,
contract, or data-shape change — the shelves are **presentational** and their state is derived
from the paired specialist + the run's retrieval events, so one poll still fully determines the
visible graph (CLAUDE.md §3). **51 frontend tests green (45 prior + 6: 5 knowledge-plane
topology, 1 Chamber KB-selection), build + strict typecheck + lint (0 errors, 1 pre-existing
accepted warning) + `format:check` clean.** Verified visually by driving the built app against a
mocked full-assessment run (Playwright screenshots of the graph with the six shelves lit
being-read/read/idle, and the KB detail drawer with its real served source). The pieces:

1. **`lib/topology.ts` — the knowledge plane, as data.** Added `KB_NODES` (six shelves, 1:1 with
   the drafting specialists per `instrument/sections.json` `kb_specialists` — the real
   `kb/<specialist>.sqlite` indexes, TECH_SPEC §8.3), `KB_EDGES` (each specialist → its shelf),
   and the `KbNode` type + `allKbNodes`/`kbNodeById`/`kbForSpecialist` helpers. Each shelf carries
   a lay `blurb`/`contains`/`explain` and a real `docCount` mirrored from
   `kb/<specialist>.manifest.json` (a by-hand mirror like the `status.py` node ids, documented as
   such). **The shelves are deliberately NOT in `allNodeIds()`** — that stays the pinned
   `status.py` mirror (`topology.test` still green), so they never enter `status.json` `nodes`.
   The layout grid widened (a KB column between the college and the checkpoint; `SPEC_PITCH`
   150) and `workspaceSize` now spans both planes; `SPEC_JOIN_X` is the x at which a specialist's
   onward wire turns past the shelves toward the checkpoint (the PoC's routing).
2. **`components/PipelineGraph.tsx` + `.css` — the shelves rendered.** Each specialist now shows
   its knowledge base to its lower-right, joined by a distinct dashed **retrieval wire** (the
   vapour tone, not a pipeline handoff). A shelf's state derives from its specialist — `serving`
   (lit, pulsing) while it reads, `read` once done, else `idle` — carried by a state word + strip
   + shape, never colour alone (§9). Added **node-kind icons** (agent/engine/checkpoint/database),
   faint **group frame + phase captions** ("The specialist college · knowledge plane", "Threshold
   assessment", "Full assessment"), and **chunk chips** flying off a serving shelf (CSS
   offset-path, gated on support + reduced motion — pure enhancement). Uses `--vapour`, not a new
   hue, so it stays inside the design system.
3. **`components/NodeDetail.tsx` + `.css` — the KB drawer.** Selecting a shelf opens the same
   drawer from the shelf's point of view: a "Knowledge base" chip, what body of authority it holds
   (`N official documents`, and what they cover), the citation guarantee, and **the real sources it
   has served this run** (the paired specialist's retrieval evidence — still one poll). Shared
   `DrawerShell`/`SourceList` between the node and KB variants.
4. **`routes/Chamber.tsx` — wired KB selection.** A selection is now a pipeline node *or* a shelf;
   a shelf borrows the paired specialist's state + retrieval evidence for the drawer.

**No document contradiction to fix** — the PoC is a direction, not a spec; the knowledge plane
realises DESIGN §7.2's "six specialists, each reading its own sources" as visible nodes. **Next:**
unchanged from the prior branch's ledger (a first live Gemini run remains the untested seam).


**Prior branch (`claude/windtunnel-chamber-redesign-guxzzt`): the Chamber redesign — the
governance surface is now a clickable node-graph canvas built for lay-audience
transparency, plus the Windtunnel brand assets (logo, favicon, sprite loading
animation) (DESIGN §7.2; CLAUDE.md §4, §9).** Tom asked to move the Chamber towards the
`frontend/windtunnel_agent_telemetry.html` PoC — a node interface that explains *how the
system technically works* in terms a non-engineer follows — and to place the new brand
assets he added under `frontend/src/img/`. Frontend-only; no backend, pipeline, contract,
or data-shape change (the redesign reads the same `status.json` one poll fully determines,
CLAUDE.md §3). **45 frontend tests green (41 prior + 4), build + strict typecheck + lint
(0 errors, 1 pre-existing accepted warning) + `format:check` clean.** Verified visually by
driving the built app against a mocked backend (Playwright screenshots of the running
graph, the detail drawer with real sources, the not-started warm-up, and the landing
logo). The pieces:

1. **`lib/topology.ts` — the layout + lay-audience metadata owner.** Kept the pinned
   id/friendly/kind mirror of `pipeline/status.py` `_node_specs()` (topology.test still
   green) and *added*, per node: a static workspace `pos` (no DOM measurement, so wires are
   deterministic in every env), an `engine` label (lay model tier from `config/models.yml` —
   "Fast drafting model" / "Deep-reasoning model" / "Fixed rules — no AI"), a one-line
   `blurb`, and a plain-language `explain` paragraph. Plus `EDGES` (the real pipeline
   handoffs, incl. the two parallel moments — two generalists → reconciler and the
   six-specialist bloom from the rating engine), and `allNodes`/`nodeById`/`workspaceSize`
   helpers. The explanatory copy is descriptive only — the machine-checkable
   specialist↔section map still has one owner (`instrument/sections.json`).
2. **`components/PipelineGraph.tsx` + `.css` — rebuilt as a node-graph canvas.** A
   pannable/zoomable stage (drag to pan, wheel + buttons to zoom, fit-to-view default;
   ResizeObserver-guarded for the headless test env) of positioned node cards joined by SVG
   wires. Wire state derives from the two nodes it joins (a live handoff flows with a
   travelling dash; a completed source lights; settled dims). State is carried by **label +
   shape + position** never colour alone (§9): each card names its state, keeps the "computed,
   not judged" cue on compute nodes, and shows its genuine current sub-activity when active.
   The activity log stays the accessibility/honesty backbone (§7.2.1).
3. **`components/NodeDetail.tsx` + `.css` — the transparency payload.** Selecting a stage
   opens a drawer that explains, in lay terms, what it is and what it's doing, and backs it
   with the *real* evidence from the status log — the sources it has read (doc + locator) and
   the questions it raised — all from the one poll. Compute nodes get the "no AI model here"
   callout (the visible face of "models argue, code computes", CLAUDE.md §3).
4. **Brand assets (`frontend/src/img/`).** The Windtunnel logo rides in the wordmark (a round
   tile that reads on both surfaces) and as the Landing hero (white ground melted into the
   paper via `mix-blend-mode`); `WindTunnelFavicon.png` is wired as the favicon (Vite
   rewrites the base path). `components/TunnelWarmup.tsx` flip-books the eleven pixel-art
   sprites into a "tunnel warming up" loader used in the cold-start note, the first Chamber
   load, and the not-started prompt (freezes on the grown frame under reduced motion; visible
   copy carries the meaning). The old CSS-pip warm-up indicators were removed in favour of it.
5. **`routes/Chamber.tsx` — wired the flagship.** RunningView now hosts the graph (with the
   detail drawer overlaid) above the activity log, owns node-selection state (Escape closes),
   and derives per-node evidence (`buildEvidence`) from the log alongside the existing
   sub-activity. **Fixed a real regression the taller graph exposed:** `ActivityLog` scrolled
   the *window* via `scrollIntoView` on load, dragging the flagship out of view — it now
   scrolls only its own feed.

**No document contradiction to fix** — the PoC is a direction, not a spec; the design brief's
§7.2 flagship (graph + activity log, label+shape+position, one-poll determinism) is honoured,
just realised as an interactive canvas. **Next:** unchanged from the prior branch's ledger
(the redesign is orthogonal to the pipeline recovery work below). A possible future polish:
the logo PNG is 853 kB — fine cached, but worth optimising if page weight matters.


**This branch (`claude/agent-error-legal-amendment-23lu5v`): WT-H2A8-H3 died again, further in —
at REVIEW cycle 1, on the first amend directive (`AgentError: legal: amendment touched
non-directed sections ['10.2', '12.1', '12.2', '9.1', '9.2']`). Root cause: the amendment
path handed the model a self-contradictory contract (TECH_SPEC §11.3 vs the shared specialist
prompt), then killed the run for obeying the wrong half.** The reviewer directed legal to amend
`11.1` alone, but `run_specialist_amendment` reused the *full* instrument context (all six owned
sections' question text) under a system prompt that commands "for **every** owned section, draft
it or gap it… every owned section id must appear in exactly one of `sections` or `gaps`". The
user-turn line "cover exactly the directed sections" lost to the system-level rule: the model
(Flash) returned all six owned sections — the five extras are exactly owned-minus-target — and
`_parse_amendment` hard-failed. Deterministic, not a flake: both attempts failed identically,
and privacy/it_security (the cycle's other directives, never reached) would have hit the same
wall. Fix = the same defense-in-depth shape as the sub-question-id incident:

1. **Prompt-side — the model's visible scope now IS the directive's scope.**
   `specialist_instrument_context` gained an `only=` param (validated subset of owned, raises
   on anything else); the amendment passes the directed sections, so the context lists *only*
   the directive's question text with an §11.3 scope preamble, and the shared prompt's "every
   owned section" rule now reads over exactly the directed set instead of fighting it. Fresh
   drafting (`run_specialist`) is unchanged; no prompt-file edit, so no version bump.
2. **Boundary-side — tolerate the echo, keep the invariant.** `_parse_amendment` now folds
   sub-question keys against the whole owned set, then **discards** owned-but-non-directed
   keys (`_discard_undirected`) from `sections`/`citations`/`gaps` before validation: an echo
   of settled work could never land anyway (the merge is target-scoped), so it must not kill
   the run. A key outside the owned set entirely is still rejected **loudly** (§9.3 preserved),
   and a directed section missing from the output still fails as before. This supersedes the
   ledger decision "any other key is rejected" (below) for the owned-but-undirected case only —
   the §11.3 guarantee ("a directive may only change the sections it named") is enforced by the
   discard + target-scoped merge, not by run death.

**Recovery for WT-H2A8-H3:** the run is FAILED at REVIEW, cycle 1; `reviewer/cycle_1.json`
(the ruling) is committed, no amendment landed. Merge this branch to `main`, then redispatch —
REVIEW re-enters at cycle 1, reuses the committed ruling, and re-runs the three amendments
(legal, privacy, it_security) with the scoped context. **Pipeline: 213 tests green (210 prior
+ 3: whole-owned-set echo rehearsal of the exact legal failure shape, non-owned key still
rejected loudly, scoped instrument context renders only the directed sections; the old
"rejects non-directed" test became "discards the echo, prior draft survives"), ruff clean.**
Backend and frontend untouched.

**Prior branch (`claude/wt-h2a8-h3-errors-vl5tu7`): two errors from Tom's live run WT-H2A8-H3 —
a specialist that failed the run on the instrument's own sub-question ids, and a threshold
download that 404'd because the proxy pointed at a phantom path (TECH_SPEC §9.3, §7, §2;
CLAUDE.md §3).** Both are seam/wiring bugs, LLM-free tested; no integrity invariant relaxed.

1. **`AgentError: legal: sections contain out-of-scope keys ['12.2.1', '12.2.2']`.** A handful of
   DTA sections carry numbered sub-questions in the instrument (`questions.json`): §12.2 'Legal
   advice' → 12.2.1/12.2.2, §8.4 → 8.4.1/8.4.2. The specialist prompt lists them, so the legal
   model keyed its answer by those sub-question ids instead of the owned parent `12.2` — and the
   flat write-scope validator (`_parse_draft`) rejected them as out-of-scope, killing the run. It
   was **non-deterministic**: the *same run's* ethics specialist keyed §8.4 correctly ("Yes.
   (8.4.1)… (8.4.2)…") in one prose answer. `12.2.1`/`12.2.2` are not a scope violation — they are
   children of a section legal *owns*. Fix = defense-in-depth, matching the JSON-seam precedent:
   (a) **prompt clarity** — `specialist_instrument_context` now says to key by the **section id**
   and address sub-questions *within that single answer*, never returning a sub-question number as
   a key; (b) **tolerant, lossless fold** — `agents/specialist.py` `_fold_subquestions` (applied in
   both `_parse_draft` and `_parse_amendment`, before the scope checks) folds instrument
   sub-question keys onto their owned parent: sub-answers concatenate in declared order (so a
   yes_no_na parent still opens with the Yes/No of its first sub-question), citations extend the
   parent's list, a sub-question gap becomes a parent gap. A key resolving to neither an owned
   section nor one of *its* sub-questions is still rejected **loudly** (§9.3 preserved). The
   parent↔sub-question map has one owner: `agents/prompting.owned_subquestions` (reads
   `questions.json`). Verified by driving the exact WT-H2A8-H3 legal failure shape through the real
   agent boundary → folds to a valid `12.2`.
2. **`threshold.md not yet produced for run WT-H2A8-H3`.** The threshold-review screen fetches the
   `threshold.md` artefact; the backend proxy `_ARTEFACTS` mapped it to `artefacts/threshold.md`
   (and `outline.md` → `artefacts/outline.md`) — paths **no code ever writes**. The pipeline's
   canonical files are `threshold/threshold_assessment.md` (written by THRESHOLD_RECONCILING) and
   `brainstorm/outline.md` (§7.1). Fix = point the proxy at the canonical files; the public artefact
   *names* (§7 contract) are unchanged, so the SPA needs no change. No duplicate `artefacts/` copy
   is produced — one owner per fact (CLAUDE.md §3). This was a genuine doc/impl contradiction
   (TECH_SPEC §2 listed phantom `artefacts/threshold.md`/`outline.md` and a `reconciled.md` that
   was renamed to `threshold_assessment.md` in the build); per CLAUDE.md §2 the losing document is
   fixed — the §2 run-directory tree now describes the real layout.

**Recovery for WT-H2A8-H3:** the run is FAILED at `full.specialist.legal`; ethics/it_security/
privacy are already committed (per-agent idempotent, checkpoint-skipped on resume), so a
redispatch (resume from FULL_DRAFTING) re-runs only legal/data_governance/solution_architect with
the fix in place. **Pipeline: 210 tests green (204 prior + 6: owned_subquestions map, draft fold,
citation fold, still-rejects-true-out-of-scope, amendment fold), ruff clean. Backend: 120 tests
green (119 prior + 1: outline proxy; the threshold proxy test re-pointed), ruff clean.** Frontend
untouched (the artefact name is stable). See Done.

**Prior branch (`claude/windtunnel-governance-json-error-c0kgvr`): the governance chamber's
first three live runs all died at the LLM seam — made the seam absorb transient failure,
and made a failed run actually recoverable (TECH_SPEC §13, §5.6, §5.3, §6.3; CLAUDE.md §3).**
Tom's live tests produced three failed runs, three different proximate causes, one seam:
`WT-H5M2-2Y` — `threshold_generalist` returned *almost*-JSON with one syntax slip at char
5005 (the reported bug); `WT-TR4C-DC` — the reconciler returned a **valid** object followed
by trailing prose ("Extra data"); `WT-PX5H-3D` — a transient Gemini **503** ("high demand,
try again later"). Every one was treated as instantly fatal, and — worse — the recovery
path the failure screen promises did not exist: `/redispatch` 409'd on `stage_status=failed`,
and even if re-kicked, a same-stage resume left `FAILED` in place so the driver flipped
status.json to "running" and exited without doing anything (a zombie run). Five fixes,
all LLM-free-tested, plus a rehearsal that drives the *actual stranded state* of
`WT-H5M2-2Y` through the new code to its THRESHOLD_REVIEW pause:
1. **`pipeline/llm.py` — the seam absorbs transient failure in two bounded layers.**
   `GeminiTransport` retries 429/5xx/network blips/timeouts (backoff 2s/5s/12s; permanent
   errors still fail immediately); `complete_json` parses tolerantly-but-losslessly (fence,
   prose preamble, trailing text after the object, raw control chars in strings — none
   change the content the model produced) and **re-asks the model** with a corrective note
   on a genuinely malformed/truncated/non-object answer (≤2 re-asks, each budget-charged;
   content is never guessed or repaired). `_extract_text` filters thinking-model `thought`
   parts and names `MAX_TOKENS` truncation (`LLMTruncated`) instead of surfacing it as a
   bewildering parse position. **The backend imports this same module, so the whole
   brainstorm side (interviewer/sufficiency/feasibility/PoC/map) inherits every layer.**
2. **`pipeline/run.py` — a same-stage resume clears `FAILED`.** A failed run's `stage`
   still points at the failing stage (§5.6), so its retry dispatch is always same-stage;
   `run_pipeline` now calls `advance_to` in that case too (clearing `last_error`), and
   `status.set_running` clears the stale failure payload (one poll never shows "running"
   *and* a failure, §6.1). Rebuild parity holds.
3. **`backend/app.py` — `/redispatch` accepts failed runs** (§5.6 "resume from the last
   checkpoint" now has an API), and `_REDISPATCH_RESUME_FROM` gains the mid-flight stages
   `ARCHITECT`/`REVIEW`/`ASSEMBLY` → themselves (a run that failed there must resume from
   exactly that stage — an earlier resume_from would fast-forward into a wrong re-pause).
4. **`frontend/FailureState` — a "Resume the run" button** wired to `redispatchRun`, so the
   failure screen's promise is one click, not a dead loop through resume-by-code back to
   the same screen. (The run-code path stays for cross-device resume.)
5. **`pipeline/status.py` + `run.py` — mid-stage status pulses (§6.3 cadence).** Node
   transitions commit `status.json` as they happen (sub-activity throttled to ≥15s), so
   the Chamber's flagship animation moves *during* a stage instead of freezing all-pending
   until the first checkpoint (~2 min in which the "waiting to start… Restart the run"
   prompt showed misleadingly mid-run, inviting duplicate dispatches). The pulse made
   partial-stage commits real, so: `threshold_drafting` and `full_drafting` became
   per-agent idempotent (a committed draft is never re-drafted on retry — its questions
   reload from the file), and `full/questions.json` is now **always** written (empty
   `specialists` when none) and is part of FULL_DRAFTING's checkpoint — without it, a
   death between the last pulsed draft and the questions write would let resume skip the
   stage and silently drop raised questions (`_resolve_next` reads the payload, not file
   existence).
Prompt hardening rides along: `threshold_generalist.v1.md` + `threshold_reconciler.v1.md`
gain explicit JSON-escaping guidance (guidance-only, no version bump — the interviewer
precedent). **Pipeline: 205 tests green (186 prior + 19 new: seam tolerances/re-ask/
transport retry ×17, failed-resume + pulse ×2), ruff clean. Backend: 119 green (117 + 2
failed-redispatch), ruff clean. Frontend: 41 green (40 + 1 failure-resume), build + lint
(1 pre-existing accepted warning) + format clean.** The recovery rehearsal script drove
`runs/WT-H5M2-2Y`'s committed failed state (copied to scratch) through
resume_from=THRESHOLD_DRAFTING with a malformed-then-good generalist and a
trailing-prose reconciler: failure cleared, 1 corrective re-ask, paused at
THRESHOLD_REVIEW with `threshold_assessment.md` rendered. **Next live step is Tom's
one click:** open each failed run in the Chamber and press "Resume the run" (or
`POST /api/runs/<code>/redispatch`).

**Prior branch (`claude/brainstorm-partner-ux-mgphjn`): Brainstorm partner UX tweaks from
Tom's use (DESIGN §5, §6).** Five interface/behaviour refinements to the Brainstorm phase,
no contract or pipeline change:
1. **Warm-up reads as "working", not "hung".** The cold-start liveness indicator
   (`ColdStartNote`) and the two Chamber waiting states ("Opening the tunnel…", the
   "waiting to start" prompt) now show a *moving* travelling-pips animation (air down the
   tunnel) instead of a single static pulse, with copy that says it hasn't stalled. Static
   but still visible under reduced motion.
2. **The interviewer writes its replies out gradually** — a typewriter reveal of the newest
   assistant turn in `Conversation` (detected by the `thinking` true→false transition, so
   restored history and reduced-motion users get the whole text at once).
3. **The interviewer infers more and moves faster** — `prompts/interviewer.v1.md` now drafts
   ahead by inference (fill multiple sections, flag assumptions), so a user can reach a
   submittable outline as fast as they like (Submit was already always-enabled).
4. **The interviewer is less passive** — it asks the sharp question, surfaces the nuance/design
   fork the user may have missed, softly provoking design choices rather than just collecting
   answers.
5. **The interviewer is less verbose** — replies are 1–2 sentences + one question.
6. **PoC and flow map are promoted to top tabs** (`BrainstormTabs`): the conversation, the
   proof of concept, and the flow map now sit as three selectable tabs above the canvas —
   equal, expressive ways to say what the end state should be — instead of a block at the
   foot of the page. `BrainstormSynthesis` split into `PocPanel`/`FlowMapPanel`; the unused
   `FocusTrack` removed. **Frontend: 40 tests green, build + lint + format clean.** Backend
   unchanged (23 brainstorm tests green; the prompt edit is content-only, LLM-free tests
   unaffected).

**Prior branch (`claude/governance-chamber-bugs-hygv1b`): the first-live-test bug fixes —
a stranded submit and a chamber that never animates (TECH_SPEC §5.7; CLAUDE.md §6).**
Tom's first end-to-end test surfaced two bugs, both rooted in the same cause: the
`workflow_dispatch` that starts Governance **fails** because the `WINDTUNNEL_PAT` carries
`contents:write` only, but the dispatch endpoint needs **`actions:write`** — so after Submit
the backend committed the `SUBMITTED` transition, then the dispatch 403'd and the endpoint
raised a 502, stranding the run (Bug 1: "had to refresh; resubmit said *not at BRAINSTORM
(currently SUBMITTED)*") with no Action behind it (Bug 2: "the chamber opened but nothing
happened"). Confirmed live: `governance.yml` has **0 runs**; `WT-TR4C-DC`'s `status.json` is
frozen at the initial state. **The root cause is Tom's to fix** (regenerate the PAT with
`actions:write` — see Blocked on Tom). **The code now fails gracefully and recoverably:**
(1) a dispatch failure is no longer a 502 — the four dispatching endpoints return
`{dispatched:false, dispatch_error}` and keep the committed transition (§5.7 — dispatch is
fire-and-forget, observed via `status.json`), so Submit resolves and the SPA navigates to the
Chamber instead of stranding on Brainstorm; (2) a new `POST /api/runs/{id}/redispatch` re-kicks
a run whose dispatch never took, resuming idempotently from its checkpoint (§5.3), serialised by
the workflow's per-run `concurrency` group; (3) the Chamber shows an honest "waiting for the run
to start… restart the run" affordance whenever a submitted run has no node progress, wired to
redispatch — replacing the silently frozen graph. **Backend: 117 tests green (111 prior + 6
dispatch/redispatch), ruff clean. Frontend: 40 tests green (38 prior + 2 Chamber), build +
lint + format clean.** Docs updated (CLAUDE.md §6, `dispatch.py`) so the PAT requirement is
recorded, not rediscovered. See Done + Blocked on Tom.


**This branch: the `threshold` `/revise` branch — the last unbuilt `/revise` value, and with
it the whole revision surface (TECH_SPEC §7, §5.1; PROJECT_BRIEF §7; CLAUDE.md §3 "models argue,
code computes").** `/revise` served `poc`/`flow_map`/`full`; it now also serves `threshold`.
`POST /revise {artefact:"threshold", instructions}` is valid **only while paused at
`THRESHOLD_REVIEW`** (409 otherwise — the review screen is where a user asks for a change),
enforces the ≤2 cap via `record_revision("threshold")`, commits
`threshold/revisions/rev_<N>/request.json` alongside the run **rewound to `THRESHOLD_RECONCILING`**
and dispatches Governance with `resume_from=THRESHOLD_RECONCILING` (a dispatching path, like
`full`/`answers` — *not* a Render-side brainstorm regenerate). The reconciler then re-runs with
the instructions **in context as untrusted data (§9.2)**: `run_reconciler` gained an optional
`revision_instructions` param, wrapped and framed so it steers the reconciled **narrative and
rationale** but never a tier or rating. **The integrity property is the point:** the two
generalist drafts stand untouched, so higher-wins resolution — and therefore the engine's
ratings — are provably unchanged by a user's revision (CLAUDE.md §3; §10 "no LLM ever emits a
rating"). Idempotency follows the `USER_REVISION` precedent: `THRESHOLD_RECONCILING`'s checkpoint
output is the standard four files on the initial pass (`revisions.threshold == 0`) but a
per-revision `rev_<N>/reconciled.json` marker once a revision is in flight, so a re-dispatch runs
rather than skipping on the first pass's outputs. After the re-run it returns to the
`THRESHOLD_REVIEW` pause with the amended `threshold_assessment.md`. **With this every `/revise`
value in TECH_SPEC §7 is built and the whole revision surface is complete.** No document
contradiction to fix — TECH_SPEC §7 already specified this branch; the build is to spec.
**What remains: a first live Gemini run** (the only untested seam is live LLM *judgement*; the
whole path is unit-tested LLM-free). **Backend: 111 tests green (106 prior + 5 threshold-revise),
ruff clean; pipeline: 186 tests green (184 prior + 2 threshold-revision), ruff clean.** See Done.

**Prior branch: the `/revise` brainstorm branches (`poc`/`flow_map`) — the last remaining
piece of the Brainstorm *backend* (TECH_SPEC §7; PROJECT_BRIEF §4/§7; CLAUDE.md §2).** The
`/revise` endpoint served only `full` (→ `USER_REVISION`); it now also serves the two
brainstorm artefacts. `POST /revise {artefact:"poc"|"flow_map", instructions}` is valid only
at `BRAINSTORM` and only once the artefact exists (a revision presupposes an initial
generation, brief §7); it **regenerates the artefact whole from the amended outline** with the
instructions in context — never a patch (brief §4) — via the same `generate_poc`/
`generate_flow_map` generators, now taking an optional `revision_instructions`, and commits the
regenerated artefact alongside the incremented `run.json` count (the cap's one owner, §7.1).
The ≤2 cap is enforced by `record_revision`; the `flow_map` branch returns the new Mermaid for
the SPA to re-render + re-post its SVG (the same round-trip as `/flow-map`). **The deferred
"open design question" is resolved by the brief, not deferred again:** the outline is *not* a
capped `/revise` artefact — the interview conversation is unbounded (brief §4) and the cap list
is map/PoC/threshold/full only (brief §7). That was a genuine document contradiction (the tech
spec §7 enum and `statefile.REVISION_ARTEFACTS` both listed `outline`); per CLAUDE.md §2 the
brief governs intent, so `outline` is removed from both and the tech spec is corrected to match.
**With this the Brainstorm backend is complete.** What remains: the `threshold` `/revise` branch
(its own `THRESHOLD_REVIEW` path, not a brainstorm artefact — the last unbuilt `/revise` value)
and a first live Gemini run. **Backend: 106 tests green (98 prior + 8 revise), ruff clean;
pipeline: 184 tests green (the `REVISION_ARTEFACTS` change is covered), ruff clean.** See Done.

**Prior branch: the Brainstorm PoC / flow-map canvas actions — the last remaining
*frontend* piece (DESIGN §6.2–6.4; CLAUDE.md §9).** The Brainstorm canvas could drive
the mandatory co-design loop (interview → sufficiency → submit) but not the two optional
focus-track stages. Now it can: a `BrainstormSynthesis` block under the outline offers
**"Build a proof of concept"** and **"Generate a flow map"**, honestly encouraged and
never nagged (§6.5). *Build a PoC* runs the backend feasibility gate; if a static mock
fits, the committed `poc.html` previews in a **`sandbox=""` iframe** (display only — it is
untrusted-user-derived, §9.2) with open-in-tab; if not, the honest **"not a fit — you'll
get a flow map instead"** conditional-stage note shows (§6.1) and the flow map is produced
instead. *Generate a flow map* returns Mermaid source, which the SPA **renders to SVG
in-browser with `mermaid.js` and posts back** for commit (CLAUDE.md §9 — Render can't run
headless Chromium). The focus track's stages 2/3 now light up from real state, and a
reload/resume **restores** a committed PoC + flow map (a new `GET /brainstorm` `artefacts`
block + the download proxy now serving `poc.html`/`flow-map.mmd`). With this, **every
DESIGN screen is built and driven** — a public servant can run the whole product in the
browser, brainstorm through PoC/map through governance to the report. `mermaid.js` is
**lazy-loaded** (a 635 kB chunk fetched only when the user draws a map — first paint stays
~210 kB). **`npm run build` (strict `tsc -b` + vite), `npm run lint` (0 errors, 1
pre-existing accepted warning), `npm run format:check` clean; 38 frontend tests green (34
prior + 4 synthesis). Backend: 98 tests green, ruff clean.** See Done. **What remains:**
the `/revise` brainstorm branches (backend, an open design question — see handoff step 1)
and a first live Gemini run.

**Prior branch: the Governance frontend — the flagship Chamber transparency animation
and every screen the run breaks out to (DESIGN §7, §8).** The `Chamber` route was an
honest shell; it is now the live poll host that renders the whole Governance phase in the
browser. One status poll fully determines the visible face (CLAUDE.md §3): the **pipeline
graph + activity log** (§7.2, the flagship) while running/created; the **threshold review**
(§7.4, computed risk chips + routing) and the **question checkpoint** (§7.3, batched by
specialist, answer-or-skip) on the Console when paused; the **report** (§8, the sandboxed
`assessment.html` + the ≤2-revision affordance) or the **concluded** view on completion;
and the **calm, resumable failure state** (§7.2.4) on error. The resume-by-code flow lands
here and the same state logic drops the user at the exact right face (§7.5). With this, a
public servant can drive a run **from creation through Brainstorm, submission, the whole
governance pipeline, the pauses, and the report — entirely in the browser.** LLM-free on the
SPA side; the SPA never holds a secret. **`npm run build` (strict `tsc -b` + vite), `npm run
lint` (0 errors), `npm run format:check` all clean; 34 frontend tests green (19 prior + 5
topology + 4 markdown + 6 Chamber state-routing).** Contract fix (CLAUDE.md §2): `types.ts`'s
`QuestionsPayload` had the wrong keys (`groups`/`prompt`) — corrected to the `specialists`/
`text` shape the pipeline actually writes and the backend reads. See Done. **Remaining
frontend:** the optional PoC/flow-map *canvas actions* on the Brainstorm screen (the
generators are built backend-side; the SPA needs the buttons + `mermaid.js`), the `/revise`
brainstorm branches (backend), and a first live Gemini run. See handoff notes.

**Prior branch: the Brainstorm co-design canvas — the frontend's first interactive screen
(DESIGN §6).** The `Brainstorm` route is now the real two-pane surface (conversation + live
outline canvas + sufficiency banner + click-to-edit + Submit), backed by a new
`GET /api/runs/{id}/brainstorm` load/resume endpoint. A public servant can now drive a run
from creation through the interview to submission *in the browser*. The optional PoC/flow-map
canvas actions, the Chamber animation, the pause screens, and the report view remain (handoff
step 2). See Done + handoff notes.

**Stage 3 — Full assessment** (PROJECT_BRIEF.md §9): **the full governance path runs
end-to-end to a `COMPLETE` run, the checkpoint-answer branch is wired, the ≤2
post-COMPLETE user-revision path (`USER_REVISION`, §5.8) is built, and — this branch —
the Brainstorm interview core (`POST /brainstorm/message` + `/edit-outline`) turns
`Stage.BRAINSTORM` into something a user actually drives.** Every governance stage exists
and is driven; the front half (Brainstorm) now has its interview loop, with PoC/flow-map
still to come.
**Built this branch: the frontend foundations — the app's front door and the design
system every later screen builds on (DESIGN §3, §4, §5, §7.5; CLAUDE.md §4, §9).** The
`frontend/` was just a `README.md` + `.gitkeep`; it is now a real Vite + React + TS app.
Landed: the scaffold + tooling (strict `tsc`, ESLint, Prettier, Vitest), the "Instrument"
design system as CSS custom properties (`src/styles/tokens.css` — the §3.2 palette, §3.3
type roles/scale, §3.6 motion), `src/config.ts` (the TS mirror of `backend/config.py`),
`src/lib/runCode.ts` (the one unavoidable TS copy of `pipeline/runcode.py`, pinned to the
Python owner by a test), the typed API client `src/lib/api.ts` (every §7 endpoint + the
honest Render cold-start warm-up, §5) with `src/lib/types.ts` (the status.json/§7.2.6 wire
shapes), the app shell (hash routing, the Console/Chamber surfaces §3.4, the standing
disclaimer §4.2, the run-code chip §7.5), the usage-warning gate (§4.1), the landing/empty
states (§5), and the resume-by-code flow (§7.5). The two big interactive pieces — the
Brainstorm canvas (§6.2) and the Chamber transparency animation (§7.2) — are the next
phase; their routes exist as honest shells that establish both surfaces. **Build + strict
typecheck + lint clean; 8 frontend tests green (run-code mirror + a jsdom render smoke of
the gate → landing → resume flow).** See Done below.

`FULL_DRAFTING → ARCHITECT → REVIEW → ASSEMBLY → COMPLETE` drives in one dispatch; when
a specialist raises a question the run pauses at `FULL_CHECKPOINT`, and a
`resume_from=FULL_REVISING` dispatch (from the new `POST /api/runs/{id}/answers`) resumes
into `FULL_REVISING → ARCHITECT → …`. **Built this branch: `FULL_REVISING`** (the
questioning specialists revise their own sections in light of the user's answers, a thin
orchestration over `run_specialist_amendment`; skipped questions become gaps) **and its
backend `POST /api/runs/{id}/answers` endpoint.** Prior branch added `REVIEW` (the
bounded reviewer loop — coverage + coherence + amend directives + residual §12.3/§12.4)
and `ASSEMBLY` (the nbformat notebook + nbconvert HTML report, §12). Stage 2 — Threshold
remains met in full (record preserved below); Stage 0 — Foundations remains met.

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

**Built this branch: `USER_REVISION` (§5.8) + `POST /api/runs/{id}/revise`** — the last
governance stage, closing the pipeline. A COMPLETE run can now be revised up to twice: the
reviewer triages the user's instructions into amend directives (declining rating-by-fiat
or out-of-scope asks), the targeted specialists amend their own sections, one reviewer
verify pass confirms + re-judges residual (engine recomputes), and ASSEMBLY rebuilds with a
"Revision N of 2" label after archiving the superseded report. See Done below.

**Built this branch: the rest of Brainstorm generation — the feasibility gate, the PoC, and
the flow map (§7, §12.3/§12.4).** `POST /poc` (feasibility gate first → PoC if it helps, else
the flow map, `{produced, reason}`), `POST /flow-map` (Mermaid source), and `POST
/flow-map/svg` (the SPA posts back its client-rendered SVG, CLAUDE.md §9). The PoC embed slot
in ASSEMBLY (§12.3) is no longer dormant-with-no-producer — `brainstorm/poc.html` now gets
written. See Done below.

**Not yet built:** the non-`full` `/revise` branches (outline/poc/flow_map regenerate from
the amended outline with the ≤2 cap — the generators built this branch are the reusable core
they'll call); the frontend entirely; and a first live Gemini run. With USER_REVISION done
**every governance stage in the §5.1 state machine is built and driven end-to-end**, the
**Brainstorm interview core** makes `Stage.BRAINSTORM` user-drivable, and — this branch — the
**PoC/flow-map generators** complete the Brainstorm *backend*. What remains is the `/revise`
brainstorm branches and the SPA. See handoff notes for the concrete next steps.

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

- **File-upload "Not Found" bug — diagnosed + graceful frontend degradation (TECH_SPEC §7;
  CLAUDE.md §9; this branch).** Root cause is a **stale Render backend deploy**, not a code bug:
  the `/api/runs/{id}/brainstorm/upload` route exists and returns 200 to the exact URL + body the
  SPA sends (verified by booting the app over a fake store; CORS preflight 200; 135 backend tests
  green), and the bare "Not Found" is Starlette's default 404 for an unmatched route — the endpoint
  landed in `f9f2b0d` (merged #31) but the deployed backend predates it. The **real fix is a Render
  redeploy** (see *Blocked on Tom*). Code change: `frontend/src/routes/Brainstorm.tsx` `describe()`
  now rewrites a *bare* unmatched-route 404 into an honest, actionable message ("…may be running an
  older version… try again shortly, or type your idea into the chat instead"), while passing the
  backend's own meaningful 404s ("No run found for code …") through untouched. **Frontend: 55 tests
  green (54 prior + 1: bare-404 → actionable message), build + strict typecheck + lint (0 err, 1
  pre-existing accepted warning) + format clean.** Backend/pipeline untouched.

- **Brainstorm file upload — upload a file instead of chatting, in three formats (TECH_SPEC §7,
  §9.2, §12.3/§12.4; CLAUDE.md §3; prior branch).** No pipeline/contract-breaking change; every
  invariant held (outline stays the single source of truth; uploads wrapped as untrusted; commits
  via the Contents API; the licence gate never applies to a user submission). **135 backend + 54
  frontend tests green.** The pieces:
  - **`backend/brainstorm/interviewer.py`** — `ingest_seed_material`: feeds an uploaded
    plain-text document through the interviewer prompt (shared `load_prompt`/`_parse`) so it
    populates outline sections *exactly as a long first message would*, framed as an uploaded
    document rather than a chat turn, wrapped as untrusted content (§9.2).
  - **`backend/brainstorm/mapgen.py` / `poc.py`** — extracted the validators to public:
    `validate_mermaid` (reused to gate an uploaded `.mmd`) and `validate_poc_html(*,
    require_banner)` (the §12.4 banner requirement is **relaxed for a user upload**; a
    model-generated PoC still requires it). One owner per fact — both paths share one check.
  - **`backend/app.py`** — `POST /api/runs/{id}/brainstorm/upload` (`UploadBody`): valid only at
    `BRAINSTORM`; enforces the no-sensitive-info acknowledgement for every upload and the
    starting-material acknowledgement for Mermaid; `text` → seed the outline (commit like a turn),
    `mermaid` → commit `flow-map.mmd` + return the source for the SPA's client-render round-trip,
    `html` → commit `poc.html`. Mermaid/HTML make no LLM call.
  - **`frontend`** — `FileUpload.tsx` (+ `.css`): a collapsible "Or upload a file instead"
    affordance under the conversation, format auto-detected from the extension with a manual
    override, the two acknowledgement checkboxes gating the Upload button. `Brainstorm.tsx` wires
    `uploadBrainstormFile` and routes the result to the conversation / map / PoC surface;
    `api.ts`/`types.ts` gained the typed client + `UploadResponse`. Plus **Open in a new tab** on
    the flow-map panel (`BrainstormSynthesis.tsx`) — the small preview opens full-size via a blob
    URL (Tom's ask).
  - **Tests** — `backend/tests/test_upload.py` (13: validators, plain-text ingest +
    untrusted-wrap, Mermaid commit/ack/reject, HTML commit/reject, ack/empty/stage-guard, all
    LLM-free) and three in `frontend/src/routes/Brainstorm.test.tsx` (plain-text seed, Mermaid
    double-ack + render, HTML→PoC).

- **The knowledge plane — specialists' knowledge bases depicted as nodes (DESIGN §7.2;
  CLAUDE.md §3, §9; prior branch).** The real governance graph now mirrors the PoC's most
  important missing element: each specialist paired 1:1 with the knowledge base it reads.
  Frontend-only; the shelves are presentational (derived from the paired specialist + retrieval
  events), so one poll still fully determines the graph (CLAUDE.md §3) and `status.json` `nodes`
  is unchanged. **51 frontend tests green (45 prior + 6: knowledge-plane topology ×5, Chamber
  KB-selection ×1), build + strict typecheck + lint (0 err, 1 pre-existing warning) + format
  clean.** The pieces:
  - **`lib/topology.ts`** — `KB_NODES` (6, 1:1 with the drafting specialists per `sections.json`
    `kb_specialists`; real `kb/<spec>.sqlite` indexes), `KB_EDGES`, the `KbNode` type +
    `allKbNodes`/`kbNodeById`/`kbForSpecialist`. Each shelf: lay `blurb`/`contains`/`explain` +
    real `docCount` mirrored from `kb/<spec>.manifest.json`. **Kept out of `allNodeIds()`** so the
    `status.py` mirror stays pinned (`topology.test`). Widened the grid (KB column, `SPEC_PITCH`
    150), `workspaceSize` spans both planes, `SPEC_JOIN_X` routes the onward wire past the shelves.
  - **`components/PipelineGraph.tsx` + `.css`** — shelves rendered lower-right of each specialist,
    joined by a dashed vapour-tone **retrieval wire**; shelf state (`serving`/`read`/`idle`)
    derived from the specialist, carried by word + strip + shape (§9). Added node-kind icons, a
    faint group frame + phase captions, and offset-path **chunk chips** (gated on support +
    reduced motion). Stays inside the design system (`--vapour`, no new hue).
  - **`components/NodeDetail.tsx` + `.css`** — a `KbDetail` variant: what the shelf holds
    (`N official documents` + coverage), the citation guarantee, and the real sources served this
    run (the specialist's retrieval evidence). Shared `DrawerShell`/`SourceList`.
  - **`routes/Chamber.tsx`** — a selection is a node or a shelf; a shelf borrows the paired
    specialist's state + evidence for the drawer.

- **Chamber redesign — a lay-audience node-graph canvas + Windtunnel brand assets
  (DESIGN §7.2; CLAUDE.md §4, §9; prior branch).** Frontend-only; reads the same one-poll
  `status.json` (CLAUDE.md §3). No backend/pipeline/contract change. **45 frontend tests
  green (41 prior + 4: topology layout/edges ×3, node-detail interaction ×1), build +
  strict typecheck + lint (0 err, 1 pre-existing warning) + format clean.** The pieces:
  - **`lib/topology.ts`** — kept the pinned id/friendly/kind mirror of `status.py`
    `_node_specs()`; added per-node `pos` (static, deterministic wires), lay `engine`/`blurb`/
    `explain`, an `EDGES` handoff list (both parallel moments), and `allNodes`/`nodeById`/
    `workspaceSize`. Descriptive copy only — `instrument/sections.json` stays the one owner
    of the specialist↔section map.
  - **`components/PipelineGraph.tsx` + `.css`** — rewritten from a banded list into a
    pannable/zoomable node canvas (drag/wheel/fit; ResizeObserver-guarded) with SVG wires
    whose state (flow/ready/done/pending) derives from the two nodes they join, a travelling
    dash on live handoffs, and cards that carry state by label+shape+position (§9), the
    "computed, not judged" cue, and genuine sub-activity when active.
  - **`components/NodeDetail.tsx` + `.css`** — new: selecting a stage opens a drawer that
    explains it in plain terms and shows the real sources it read (doc + locator) and
    questions it raised, all from the poll; compute nodes get the "no AI model here" callout.
  - **Brand assets** — logo in the wordmark (round tile) + Landing hero (`mix-blend-mode`
    melts the white ground); `WindTunnelFavicon.png` wired as favicon; `TunnelWarmup.tsx`
    flip-books the 11 pixel-art sprites for the cold-start / first-load / not-started waits
    (freezes under reduced motion). Replaced the old CSS-pip warm-up indicators.
  - **`routes/Chamber.tsx`** — RunningView hosts the graph (detail drawer overlaid) above the
    activity log, owns selection state (Escape closes), and derives per-node evidence from the
    log. Fixed `ActivityLog` scrolling the *window* on load (now scrolls only its own feed) —
    a regression the taller graph exposed.

- **WT-H2A8-H3 two-error fix — sub-question write-scope + the threshold download path
  (TECH_SPEC §9.3, §7, §2; CLAUDE.md §2, §3; this branch).** Two errors from Tom's live run,
  both seam/wiring, neither relaxing an integrity invariant. LLM-free tested (§15); ruff clean.
  **210 pipeline + 120 backend tests green.** The pieces:
  - **`pipeline/agents/prompting.py` — `owned_subquestions()` + clearer instrument context.**
    New helper maps each owned section to its instrument-defined nested sub-question ids
    (`12.2` → `('12.2.1','12.2.2')`, `8.4` → `('8.4.1','8.4.2')`; read once from `questions.json`,
    one owner per fact). `specialist_instrument_context` now instructs: key every entry by the
    **section id**, address a section's listed sub-questions *within its single answer*, never
    return a sub-question number as a key (guidance-only; the context is code-generated, no prompt
    version bump — the interviewer precedent).
  - **`pipeline/agents/specialist.py` — `_fold_subquestions` (lossless, before scope checks).**
    Folds any sub-question-keyed `sections`/`citations`/`gaps` onto the owned parent section:
    sub-answers concatenate in the instrument's declared order (a yes_no_na parent still opens with
    its first sub-question's Yes/No), citations extend the parent list, a sub-question gap becomes a
    parent gap. Applied in `_parse_draft` (owned) and `_parse_amendment` (directed targets). A key
    resolving to neither an allowed section nor one of its sub-questions passes through untouched, so
    the out-of-scope guard still rejects a true §9.3 violation loudly. Returns the payload unchanged
    when nothing is sub-keyed (fast path). This mirrors the LLM-seam philosophy: harden the prompt
    **and** absorb the reasonable output shape tolerantly, never fail the run on it.
  - **`backend/app.py` — the artefact proxy points at the canonical files.** `_ARTEFACTS`
    `"threshold.md"` → `threshold/threshold_assessment.md` (was the never-written
    `artefacts/threshold.md`) and `"outline.md"` → `brainstorm/outline.md` (was
    `artefacts/outline.md`). The public artefact names (§7) are stable, so the SPA is unchanged; no
    duplicate copy is produced (one owner per fact). The other two names (`assessment.ipynb/.html`)
    are genuinely under `artefacts/` and untouched.
  - **`TECH_SPEC.md` §2 — the run-directory tree corrected (CLAUDE.md §2, losing doc fixed).**
    Renamed the phantom `threshold/reconciled.md` to the built `threshold_assessment.md`, dropped the
    never-produced `artefacts/threshold.md`/`artefacts/outline.md` rows, and added a note that the
    downloadable `threshold.md`/`outline.md` artefact names are served from their canonical files.
  - **7 new/updated tests.** `test_full_drafting.py` (5): `owned_subquestions` maps only nested
    sections; the reported 12.2.1/12.2.2 draft folds to a valid `12.2`; sub-question citations fold;
    a true out-of-scope key (`7.1.1`, privacy's territory) is still rejected. `test_review.py` (1):
    an amendment on `12.2` keyed by sub-questions folds onto the directed parent. `test_app.py`:
    the threshold-download test re-pointed to `threshold/threshold_assessment.md` + a new
    `outline.md` proxy test. Verified end-to-end by driving the exact WT-H2A8-H3 legal failure shape
    through `run_specialist` → folds cleanly, no AgentError.

- **Governance-chamber first-live-run fixes — the LLM seam absorbs failure, and a failed
  run is actually recoverable (TECH_SPEC §13, §5.6, §5.3, §6.3; CLAUDE.md §3; prior
  branch).** Three live runs failed at the seam three different ways (malformed JSON /
  trailing text after a valid object / transient 503), and the promised recovery path
  didn't exist (redispatch 409'd on failed; same-stage resume kept FAILED — a zombie).
  All LLM-free tested (§15); ruff + eslint + prettier clean. **205 pipeline + 119
  backend + 41 frontend tests green.** The pieces:
  - **`pipeline/llm.py` — two bounded failure-absorption layers.** `GeminiTransport`
    retries transient HTTP (429/5xx/URLError/timeout; 2s/5s/12s backoff, permanent errors
    immediate); `complete_json` parses tolerantly-but-losslessly (`_parse_json_object`:
    fence, prose preamble, trailing text via `raw_decode`, raw control chars via
    `strict=False` — content never altered) and re-asks the model with a corrective note
    on malformed/truncated/non-object answers (≤`JSON_REASKS`=2, budget-charged).
    `_extract_text` skips `thought` parts and raises `LLMTruncated` on MAX_TOKENS.
    The backend's brainstorm agents import this same module and inherit everything.
  - **`pipeline/run.py` + `status.py` — the failed-run resume actually resumes.**
    Same-stage `resume_from` on a FAILED run clears the marker via `advance_to`
    (previously `_drive` bailed on the FAILED guard *after* the handshake had flipped
    status.json to "running"); `set_running` clears the stale failure payload (§6.1
    one-poll rule; rebuild parity preserved).
  - **`backend/app.py` — `/redispatch` is the §5.6 retry.** Gate widened to
    `stage_status ∈ {in_progress, failed}`; `_REDISPATCH_RESUME_FROM` +=
    ARCHITECT/REVIEW/ASSEMBLY → themselves (fail-only dispatch targets; an earlier
    resume_from would re-pause wrongly at a checkpoint already answered).
  - **`frontend/src/components/FailureState.tsx` — "Resume the run".** The failure
    screen's primary action calls `redispatchRun` (same states/copy family as the
    NotStartedPrompt restart); run-code path retained for cross-device resume.
  - **`pipeline/status.py` + `run.py` — mid-stage status pulses (§6.3 ~20s cadence).**
    A driver-installed `pulse` on `StatusModel` saves + commits status.json on every
    node transition (urgent) and on drafting/retrieval sub-activity throttled to
    `PULSE_MIN_INTERVAL_S`=15s — the Chamber animation now moves during a stage, and
    the "waiting to start" prompt stops showing misleadingly mid-run. Consequences
    closed: `threshold_drafting`/`full_drafting` are per-agent idempotent (committed
    drafts skipped on retry; questions reloaded from the file), and
    `full/questions.json` is **always written** (empty ⇒ no pause) + added to
    FULL_DRAFTING's checkpoint outputs, with `_resolve_next` reading the payload —
    closing the drop-raised-questions window a partial-stage commit would open.
  - **Prompts** `threshold_generalist.v1.md` / `threshold_reconciler.v1.md`: explicit
    escape-quotes-and-newlines / nothing-outside-the-object guidance (guidance-only,
    no version bump — interviewer precedent).
  - **19 new pipeline tests** (`test_llm.py` ×17: tolerances, re-ask loop incl. budget
    interaction, transport retry/permanent/give-up/network-blip, thought-part skip,
    MAX_TOKENS; `test_threshold_pipeline.py` ×2: failed-run same-stage resume with
    per-generalist skip proof, mid-stage pulse visibility), **2 backend**
    (failed-run redispatch at THRESHOLD_DRAFTING; failed mid-flight REVIEW → itself),
    **1 frontend** (failure-state resume click → redispatch). Existing
    `test_full_drafting.py` no-questions assertions updated for the always-written file.
  - **Recovery rehearsal on the real stranded state:** `runs/WT-H5M2-2Y` (failed with
    the reported error) copied to scratch and driven with resume_from=THRESHOLD_DRAFTING,
    a malformed-then-good generalist and a trailing-prose reconciler: failure cleared,
    one corrective re-ask observed, 4 model calls, paused at THRESHOLD_REVIEW with the
    assessment rendered.

- **Brainstorm partner UX tweaks (DESIGN §5, §6; this branch).** Five refinements from Tom's
  use of the Brainstorm phase; no data-contract, pipeline, or endpoint change. Frontend build +
  strict typecheck + lint (0 errors, 1 pre-existing warning) + `format:check` clean; **40
  frontend tests green**; backend `test_brainstorm.py` 23 green (prompt edit is content-only).
  The pieces:
  - **Warm-up shows motion, not a hang.** `ColdStartNote.css` and `Chamber.css` gained a
    travelling-pips indicator (two pips sweeping a short track, "air down the tunnel") replacing
    the single breathing pulse that could read as stalled; wired into `ColdStartNote`, the
    Chamber "Opening the tunnel…" notice, and the `NotStartedPrompt` "waiting to start" lead,
    each with copy that it hasn't stalled. Neutralised-but-visible under reduced motion (the
    global `prefers-reduced-motion` guard in `base.css`).
  - **Gradual reply reveal (`Conversation.tsx`).** The newest interviewer turn types itself out
    (2 chars / 18 ms) with a blinking caret. Only a *freshly arrived* reply animates — detected
    by the `thinking` true→false transition — so restored transcript and reduced-motion /
    no-`matchMedia` environments render the full text at once. The interval is torn down on
    unmount and on the next reply.
  - **Interviewer prompt (`prompts/interviewer.v1.md`) — infer more, less passive, less verbose.**
    Rewrote the framing + per-turn guidance: draft ahead by inference (write every reasonably
    inferable section, flag real assumptions in one phrase so the user can wave them through or
    fix them), push the user's thinking (ask the sharp question / surface the missed nuance or
    design fork), and keep replies to 1–2 sentences + one question. Same strict-JSON output
    contract (no version bump — guidance refinement, `assistant_message`/`section_updates`/
    `title`/`summary` unchanged). Submit was already always-enabled, so "progress as fast as the
    user desires" needed no UI change.
  - **PoC + flow map as top tabs (`BrainstormTabs.tsx` + `.css`).** A new accessible tablist
    (arrow-key nav, `role=tab`/`tabpanel`, per-tab state glyph — check when produced, ◇ when a
    PoC wasn't a fit, never colour alone §9) sits above the canvas: **Conversation | Proof of
    concept | Flow map**. `Brainstorm.tsx` switches the left working surface by tab while the
    outline canvas stays put on the right; the sufficiency banner + Submit stay in the footer.
    `BrainstormSynthesis.tsx` split into presentational `PocPanel` / `FlowMapPanel` (each framed
    as a more expressive way to say what the end state should be, not an artefact of the
    outline); a not-a-fit PoC keeps its honest note on the PoC tab and lights the Flow map tab's
    glyph rather than auto-navigating. The now-unused `FocusTrack.tsx`/`.css` removed.
  - **Tests.** `Brainstorm.test.tsx` synthesis cases updated to open the relevant tab before
    acting (PoC/map are tabs now, not a footer block); the four scoping/interview cases are
    unchanged and still green (the send case exercises the typewriter via `findByText`).

- **First-live-test bug fixes — graceful, recoverable governance dispatch (TECH_SPEC §5.7;
  CLAUDE.md §6; prior branch).** Tom's first end-to-end test hit two bugs, one root cause: a
  `workflow_dispatch` that fails after the state transition is committed. Diagnosed to the PAT
  scope (`contents:write` without `actions:write`; confirmed live — `governance.yml` has 0 runs)
  and made non-fatal + recoverable in code. LLM-free tested; ruff + eslint + prettier clean.
  **117 backend + 40 frontend tests green.** The pieces:
  - **`backend/app.py` — dispatch failures no longer strand a run.** `_dispatch` now returns
    the error string (or `None`) instead of raising a 502; the four dispatching endpoints
    (`/submit`, `/threshold/route` full, `/answers`, `/revise` threshold+full) return a shared
    `{dispatched, dispatch_error?}` tail via `_dispatch_result`. On success the response is
    unchanged (`{"dispatched": true}`, no error key — existing contracts hold). The committed
    state transition stands (the run is durably submitted/advanced), matching §5.7's
    fire-and-forget model where the SPA learns the run started by watching `status.json`.
  - **`backend/app.py` — `POST /api/runs/{id}/redispatch`.** The §5.7 "hasn't started yet"
    re-dispatch: re-fires Governance for a non-paused, non-terminal dispatched stage
    (`_REDISPATCH_RESUME_FROM` maps `SUBMITTED→THRESHOLD_DRAFTING`, others to themselves).
    Idempotent (the pipeline resumes from its checkpoint, §5.3) and safe to repeat (the
    workflow's per-run `concurrency` group serialises dispatches). A 409 if the run isn't
    awaiting a dispatch (e.g. still at BRAINSTORM, or paused for the user).
  - **`frontend/src/routes/Chamber.tsx` + `.css` — the "waiting to start / restart" affordance.**
    When a submitted run shows no node progress (`allPending`), a calm `NotStartedPrompt` explains
    the run is waiting for its Action to spin up and offers a "Restart the run" button
    (`redispatchRun`) — replacing the silently frozen graph a failed dispatch used to leave.
    Because Submit now resolves even when the dispatch fails, the SPA navigates to the Chamber
    (no more manual refresh / resubmit-409). `redispatchRun` added to `api.ts`; `submitRun`'s
    type carries the optional `dispatch_error`.
  - **Docs.** CLAUDE.md §6 + `backend/dispatch.py` now state the PAT needs `contents:write` **and**
    `actions:write`, and why a contents-only token produces exactly this "submitted run never
    starts" symptom. Recorded in Blocked on Tom as the one remaining action (regenerate the PAT).
  - **8 new tests.** `backend/tests/test_app.py` (6): submit with a failing dispatcher →
    200 + `dispatched:false` + reason, run stays `SUBMITTED`; redispatch re-fires a submitted run
    (resume_from THRESHOLD_DRAFTING) and a FULL_REVISING run (→ itself); redispatch 409s at
    BRAINSTORM and while paused; redispatch reports a dispatch failure. `frontend/.../Chamber.test.tsx`
    (2): not-started → restart prompt calls `redispatchRun` and confirms; a run with an active node
    shows no prompt.

- **`threshold` `/revise` branch — the last `/revise` value, completing the revision surface
  (TECH_SPEC §7, §5.1; PROJECT_BRIEF §7; CLAUDE.md §3; this branch).** A threshold assessment
  can now be revised up to twice while the review screen is open, by re-running the reconciler —
  never by moving a rating. LLM-free tested (§15); ruff clean. **111 backend + 186 pipeline tests
  green.** The pieces:
  - **`backend/app.py` — the `threshold` branch of `POST /revise`.** `ReviseBody.artefact`
    widened to `Literal["poc","flow_map","threshold","full"]` (`outline` → 422; the outline is
    unbounded, brief §4/§7). A new `_revise_threshold` helper: valid **only** while paused at
    `THRESHOLD_REVIEW`+`awaiting_user` (409 otherwise), enforces the ≤2 cap via
    `record_revision("threshold")` (409 at cap), and commits `threshold/revisions/rev_<N>/
    request.json` alongside the run **rewound to `THRESHOLD_RECONCILING`** + `status.json` running
    as **one atomic commit**, then dispatches `resume_from=THRESHOLD_RECONCILING`. It is a
    *dispatching* path (Governance runs in Actions), so it lives with `/answers` and `/revise
    full`, not the Render-side brainstorm regenerate — mirrors both exactly.
  - **`pipeline/agents/threshold.py::run_reconciler` — an optional `revision_instructions`.**
    When present, the user's instructions are added as an **untrusted-wrapped block (§9.2)** with
    trusted framing that they steer the *narrative and rationale only* — never a consequence tier,
    likelihood tier, or rating (those are computed by code from the two generalists' unchanged
    inputs, §10). `None` on the initial pass (prompt unchanged, existing tests untouched). The
    `threshold_reconciler.v1.md` prompt gained a matching "If a revision has been requested"
    section (additive guidance, identical output contract — no version bump; see Decisions).
  - **`pipeline/stages/threshold.py::threshold_reconciling` — the same stage, revision-aware.**
    Reads `revisions.threshold` from `run.json`; when `> 0` it loads the staged request, narrates
    a `revision` event on the reconciler node, threads the instructions into `run_reconciler`, and
    writes a per-revision `rev_<N>/reconciled.json` marker. The generalist drafts are **not**
    re-read/re-drafted (drafting is checkpoint-skipped), so the resolved tiers and the engine's
    ratings are identical — the audit-critical invariant. New relpath helpers
    `revision_request_relpath`/`revision_reconciled_relpath`.
  - **`pipeline/run.py` — the idempotency fix.** `_checkpoint_outputs(run, stage)` now resolves
    `THRESHOLD_RECONCILING`'s checkpoint to the per-revision `rev_<N>/reconciled.json` when
    `revisions.threshold > 0` (the standard four files when `== 0`), the same run-state-dependent
    checkpoint technique `USER_REVISION` already uses. Without this a revision re-dispatch would
    idempotently skip on the initial pass's committed outputs and never re-run the reconciler.
  - **7 new tests.** `backend/tests/test_app.py` (5): commit+rewind+dispatch, second-revision
    increments, cap→409 (nothing dispatched), refuse-when-not-paused→409, empty→400; the stale
    `test_revise_rejects_threshold_artefact` became `test_revise_rejects_outline_artefact`
    (threshold is valid now; only `outline` is a 422). `pipeline/tests/test_threshold_pipeline.py`
    (2): the revision re-runs the reconciler with the instructions reaching its prompt while the
    ratings stay `_EXPECTED_*` (generalists not re-called), and the per-revision checkpoint makes
    a re-dispatch idempotent (a Boom transport proves the model isn't re-called). LLM-free (§15);
    ruff clean.

- **`/revise` brainstorm branches (`poc`/`flow_map`) — the Brainstorm backend, completed
  (TECH_SPEC §7; PROJECT_BRIEF §4/§7; CLAUDE.md §2; Stage 1; prior branch).** The last
  Brainstorm backend piece, plus the document-contradiction fix it surfaced. LLM-free tested
  (§15); ruff clean. **106 backend + 184 pipeline tests green.** The pieces:
  - **Contradiction resolved: the outline is not a capped `/revise` artefact (CLAUDE.md §2).**
    The brief settles it — "The interview conversation itself is unbounded" (§4) and the ≤2
    cap applies only to "the information-flow map, the PoC, the threshold assessment and the
    full impact assessment" (§7); the outline is conspicuously absent. But `statefile.REVISION_
    ARTEFACTS` and TECH_SPEC §7's `/revise` enum both listed `outline` — a genuine contradiction.
    Per §2 the brief governs intent, so `outline` is **removed** from `REVISION_ARTEFACTS`
    (now `("poc", "flow_map", "threshold", "full")`) and both TECH_SPEC §7 rows (the `/revise`
    enum and the `run.json.revisions` example) are corrected to match. Back-compat is safe:
    `RunState.from_dict` reads only keys in `REVISION_ARTEFACTS`, so any legacy `run.json` with
    `revisions.outline` still loads (the extra key is ignored). This resolves the "open design
    question" the prior handoff deferred ("is an outline revision a distinct capped path?") — the
    answer, from the brief, is that there is no outline revision path at all; the outline is
    refined unboundedly through `/brainstorm/message` + `/brainstorm/edit-outline`.
  - **`backend/brainstorm/poc.py` + `mapgen.py` — an optional `revision_instructions`.**
    `generate_poc`/`generate_flow_map` gained an optional `revision_instructions` param. When
    present, the user's instructions are added as an **untrusted-wrapped** block (§9.2 — they
    steer the build but never license dropping the PoC limitations banner or reaching the
    network) and the task framing switches to "rebuild whole from the outline, applying the
    changes — do not patch a previous version" (brief §4 "regenerate not patch"). No behaviour
    change on the initial-generation path (the param defaults to `None`).
  - **`backend/app.py` — the `poc`/`flow_map` branches of `POST /revise`.** `ReviseBody.artefact`
    widened to `Literal["poc", "flow_map", "full"]` (`threshold`/`outline` → 422). A new
    `_revise_brainstorm_artefact` helper: valid only at `BRAINSTORM` (409 after submission — the
    outline is frozen), requires the artefact to already exist (409 otherwise — a revision
    presupposes an initial generation, and this avoids consuming a cap on nothing), enforces the
    ≤2 cap via `record_revision` (409 at cap), regenerates from the current outline with the
    instructions, and commits the artefact **alongside the incremented `run.json`** (a new commit
    shape for Brainstorm — normally brainstorm commits don't touch `run.json`, but the cap
    counter lives there, §7.1). No dispatch (Brainstorm runs on Render). The `flow_map` branch
    returns the new Mermaid so the SPA re-renders + re-posts the SVG via `/flow-map/svg` (the
    committed `.svg` goes momentarily stale, healed by the re-post — the same round-trip as the
    initial `/flow-map`). The module docstring's "not in this slice" note is updated.
  - **8 new tests** (`backend/tests/test_poc_map.py`): the two generators carry
    `revision_instructions` into the prompt with the regenerate-whole framing (2); the endpoint
    regenerates + increments the `poc` count and commits the new HTML (1); caps `poc` at 2 with a
    409 on the third (1); refuses a `poc` revise with no PoC yet, cap untouched (1); regenerates
    the `flow_map` and returns the new source (1); refuses after submission (1) and on empty
    instructions (1). The stale `test_revise_rejects_non_full_artefact` is now
    `test_revise_rejects_threshold_artefact` (both `threshold` and `outline` → 422). LLM-free.

- **Brainstorm PoC / flow-map canvas actions — the last remaining *frontend* piece
  (DESIGN §6.2–6.4; CLAUDE.md §9; Stage 1; this branch).** The optional focus-track stages
  2/3, driven end-to-end. LLM-free on the SPA (the backend generators do the thinking, built
  a prior branch). The pieces:
  - **`frontend/src/components/BrainstormSynthesis.tsx` + `.css` — the presentational block.**
    The two "enrich the assessment — optional" actions (§6.2), the honest §6.5 encouragement
    (outline alone is enough; a PoC/map just gives the specialists more), the §6.1 conditional-
    stage "not a fit" note (amber-marked aside, not an error — never colour alone, §9), and the
    two produced artefacts each in a **`sandbox=""` iframe** (display only; the artefacts derive
    from untrusted user text, §9.2): the PoC via `src=` the download proxy (like `ReportView`),
    the flow map via `srcDoc` of the client-rendered SVG (no `innerHTML` for untrusted-derived
    markup). All state lives in the route; the component is pure.
  - **`frontend/src/lib/mermaid.ts` — the one place `mermaid.js` is touched.** `renderMermaid`
    renders Mermaid source to an SVG string with `securityLevel: "strict"` (scripts/click-
    handlers stripped, labels escaped — the source is untrusted-derived, §9.2). **Lazy-imported**
    from the route (`await import("../lib/mermaid")`) so the 635 kB engine is a separate chunk
    fetched only when the user actually draws a map — the first-paint bundle stays ~210 kB
    (67 kB gzip). `mermaid@^11` added to `package.json`.
  - **`frontend/src/routes/Brainstorm.tsx` — wired in.** `buildPoc` (`POST /poc` → gate; feasible
    → preview `poc.html`; not-a-fit → render + post the map the backend produced instead),
    `generateMap` (`POST /flow-map` → `renderMermaid` → `POST /flow-map/svg`), the focus-track
    stages 2/3 lit from real state (`done`/`unavailable`+note/`upcoming`), and a **resume restore**
    (a committed PoC re-previews, a committed map re-renders from its `.mmd`; the SVG is re-posted
    only if it was never committed — an interrupted post is healed).
  - **API + types.** `generatePoc`/`generateFlowMap`/`postFlowMapSvg` added to `api.ts`;
    `PocResponse`/`FlowMapResponse`/`FlowMapSvgResponse`/`FeasibilityVerdict`/`BrainstormArtefacts`
    added and `BrainstormState` extended with the optional `artefacts` block.
  - **Backend gap-fixes (CLAUDE.md §2 — the frontend surfaced them).** The download proxy
    (`_ARTEFACTS`) now serves `poc.html` (`text/html`) and `flow-map.mmd` (`text/plain`) so the
    SPA can preview the PoC and re-render the map on resume; `GET /brainstorm` gained an
    `artefacts` block (`{poc, flow_map, flow_map_svg, feasibility}`) so a reload restores the
    focus track + re-displays the optional artefacts (existence checks + the feasibility verdict;
    a malformed `feasibility.json` reports absent, not raised — it's a display hint).
  - **9 new tests.** `Brainstorm.test.tsx` (4: build-a-PoC-and-preview-sandboxed, not-a-fit→
    honest-note+map-drawn-and-posted, generate-a-map→render+commit, resume-restores-both-without-
    re-posting — `mermaid.js` mocked, jsdom can't lay out an SVG), `test_app.py` (2: the proxy
    serves poc.html + flow-map.mmd), `test_brainstorm.py` (3: the `artefacts` block — none on a
    fresh run, a generated PoC + verdict, a rendered flow map). `npm run build`/`lint`/
    `format:check` clean; **38 frontend + 98 backend tests green; ruff clean.**

- **Governance frontend — the flagship Chamber animation + every screen the run breaks out
  to, driven end-to-end (DESIGN §7, §8; TECH_SPEC §6, §7; Stage 3; this branch).** The
  `Chamber` route was a shell; it is now the poll host that renders the whole Governance phase
  from `status.json`, one poll fully determining the visible face (CLAUDE.md §3). LLM-free on
  the SPA side; the SPA never holds a secret. **`npm run build` (strict `tsc -b` + vite), `npm
  run lint` (0 errors, 1 pre-existing accepted warning), `npm run format:check` all clean; 34
  frontend tests green.** The pieces:
  - **`src/lib/topology.ts` + `topology.test.ts` — the fixed pipeline topology (§7.2.6).** The
    node ids + friendly names + graph layout (two-generalist parallel + reconciler + rating
    engine; the six-specialist bloom + checkpoint + architect + reviewer + assembly),
    **mirrored by hand from `pipeline/status.py` `_node_specs()`** exactly as `runCode.ts`
    mirrors `runcode.py`. 5 tests pin the id set/order to that owner so it can't drift silently,
    plus the parallel-cluster captions, the friendly-name lookup+fallback, and the
    compute/pause/llm kinds.
  - **`src/hooks/useStatusPoll.ts` — the ETag-aware poll.** Holds the latest whole-graph doc
    (nothing to accumulate — one poll determines all), threads `If-None-Match` for cheap 304s,
    tracks seconds-since-last-change (the honest-staleness backbone, §7.2.5), rides out a
    network blip (keeps the last good doc, flags `offline`) vs a hard `ApiError` (stops), and
    stops polling once terminal (`complete`/`failed`).
  - **`src/components/PipelineGraph.tsx` + `.css` — the graph (§7.2.1), the spectacle.** The
    fixed topology lit by the `nodes` map: state carried by **label + shape + position, never
    colour alone** (§9 — the dot is a circle/square/triangle per state, the state word is always
    printed), active LLM nodes pulse with a genuine sub-activity line (the document being read
    now, from real `retrieval`/`drafting` events, §7.2.5), and the compute nodes (rating engine,
    assembly) read "computed, not judged" — the quiet "models argue, code computes" cue.
  - **`src/components/ActivityLog.tsx` + `.css` — the accessibility + honesty backbone
    (§7.2.1).** An ARIA live region: the same events as words, timestamped, agent-attributed
    (node id → friendly), heartbeats filtered to liveness only, and the "still working — last
    update Ns ago" / "reconnecting" honest-staleness line. It alone tells the whole story under
    reduced motion or a washed-out projector.
  - **`src/lib/markdown.tsx` + `markdown.test.tsx` — a minimal *safe* renderer.** Builds React
    elements (never `dangerouslySetInnerHTML`, so artefact text derived from untrusted user
    content can't inject markup, §9.2): ATX headings, pipe tables, lists, hr, paragraphs, and
    inline bold/italic/code — exactly the subset `threshold.md` uses. Risk-rating table cells
    become the §3.2 chip (colour + label + shape). 4 tests incl. the raw-`<script>`-stays-text
    safety case.
  - **`src/components/ThresholdReview.tsx` + `.css` (§7.4).** Fetches + renders `threshold.md`
    (the risk table with computed chips + the reconciler's divergence notes — divergence
    surfaced, not buried), the routing decision (`POST /threshold/route` conclude|full following
    the tool's own logic), the markdown download, and the honest "rating is calculated, not a
    model's opinion" framing.
  - **`src/components/Checkpoint.tsx` + `.css` (§7.3).** The batched questions grouped by
    specialist with attribution + the one-line *why* (the trust moment), MC + free-text escape
    mirroring the interview, an explicit "Skip this — note it as a gap" per question, a live
    answered/skipped tally, and one "Resume the run" → `POST /answers`. A standard
    keyboard-navigable form; nothing depends on the amber colour (§9).
  - **`src/components/FailureState.tsx` + `.css` (§7.2.4).** Calm, never blaring: progress
    saved, the run code surfaced prominently with resume instructions (a paused and a failed run
    resume identically, §7.5), and the technical detail behind a "Show technical detail"
    disclosure, collapsed by default.
  - **`src/components/ReportView.tsx` + `.css` (§8).** The self-contained `assessment.html` in a
    **`sandbox=""` iframe** (scripts + same-origin denied — it can only display), open-in-tab +
    notebook download, and the ≤2-revision affordance (`POST /revise`, server-enforced cap).
  - **`src/routes/Chamber.tsx` (rewritten) + `Chamber.css`.** The state machine: `overall_state`
    + `phase` + `questions` pick the face (running/created → graph+log on the dark Chamber;
    paused+no-questions → threshold review; paused+questions → checkpoint; complete+full →
    report; complete+threshold → concluded view; failed → failure state), the Console pauses/
    report on the light surface and the run watch/failure on the dark one, the run-code chip
    grown prominent on pause/failure (§7.5), and honest connecting/cold-start + hard-error
    notices.
  - **API + types.** `submitAnswers`, `reviseRun`, `fetchArtefactText` added to `api.ts`;
    `AnswerItem`/`AnswersResponse`/`ReviseResponse` added and — the CLAUDE.md §2 contract fix —
    `QuestionsPayload`/`CheckpointQuestion` corrected from the wrong `groups`/`prompt` keys to
    the `specialists`/`text` shape the pipeline writes (`stages/full.py`) and the backend reads
    (`app.py`), plus `expected_ranges` typed as the per-phase `[low, high]` it actually is.
  - **15 new tests.** `topology.test.ts` (5), `markdown.test.tsx` (4), `Chamber.test.tsx` (6:
    running → graph+log with the event mirrored in both; paused → threshold review with a
    computed chip; paused+questions → checkpoint grouped by specialist; failed → calm resumable
    failure with collapsed technical detail; complete+full → report + revision affordance;
    complete+threshold → concluded, not the full report). LLM-free, network-free (mocked
    `getStatus`/`fetchArtefactText`). The old `PhasePlaceholder.css` (only the Chamber shell
    used it) was removed.
- **Brainstorm co-design canvas — the first interactive screen, driven end-to-end (DESIGN §6,
  §6.2, §3.6, §3.7; TECH_SPEC §7, §7.1; Stage 1; prior branch).** The `Brainstorm` route was a
  shell; it is now the real two-pane co-design surface a public servant drives from a fresh run
  to Submit. LLM-free on the SPA side (the backend does the thinking); the SPA never holds a
  secret. **`npm run build` (strict `tsc -b` + vite), `npm run lint`, `npm run format:check` all
  clean; 19 frontend tests green (8 prior + 7 parser + 4 canvas). Backend: 93 tests green, ruff
  clean.** The pieces:
  - **`GET /api/runs/{id}/brainstorm` (backend, `app.py`) — the load/resume endpoint the canvas
    needed and the family lacked.** Returns `{outline_md, transcript, sufficiency, stage}` by
    re-reading the committed outline + transcript (the stateless backend holds nothing, CLAUDE.md
    §3); read-only, no commit. `sufficiency` is computed only while the run is at `BRAINSTORM`
    (a submitted run's outline is frozen), and the returned `stage` lets the SPA redirect a stale
    link on to the Chamber. 3 new tests (`backend/tests/test_brainstorm.py`): outline+transcript+
    sufficiency, empty-transcript-on-fresh-run, post-submission-reports-stage-and-skips-the-judge.
  - **`frontend/src/lib/outline.ts` + `outline.test.ts` — the outline parser.** Parses
    `outline_md` into `{title, summary, resolved[], sections[{id, n, title, body, resolved}]}`.
    `SECTION_REGISTRY` is the frontend copy of `backend/outline.py`'s registry (the one
    hand-mirrored fact, like `runCode.ts` mirrors `runcode.py`); `resolved` is read from the
    front-matter — the single deterministic completeness record (§7.1), never inferred from body
    text. Tolerant of both the canonical rendered form (front-matter values are JSON — what the
    backend always serves) and the raw template form, and of a missing anchor (that section falls
    back to empty/unresolved rather than vanishing). 7 tests pin the parse, the resolved gating,
    id sanitisation, the template-form fallback, and the 9-section registry order.
  - **The canvas components (`src/components/`, `src/routes/Brainstorm.tsx`).** `Conversation`
    (the left pane — dialogue bubbles, a warm empty-state invitation on a fresh run, a
    thinking indicator, Enter-to-send composer); `OutlineCanvas` (the right pane — the nine
    sections, each resolved-with-the-user's-words or open-with-ghosted-guidance, a settle
    highlight on newly-resolved/amended sections §3.6, click-to-edit with an inline editor and
    the `you` provenance tag §3.7, a live `n/9` resolved count); `SufficiencyBanner` (the §6.2
    unlocking-not-gate — encouraging when ready, a gentle "these would sharpen it" checklist
    otherwise, never blocking). `Brainstorm.tsx` orchestrates: loads via `getBrainstorm`
    (redirecting a non-`BRAINSTORM` run to the Chamber), sends turns via `brainstormMessage`,
    saves canvas edits via `editOutline`, and Submits via `submitRun` → the Chamber. Submit is
    always enabled (the backend gates only on stage, §6.2), emphasised (primary) when ready.
  - **API client + types.** `getBrainstorm` added to `src/lib/api.ts`; `BrainstormState` +
    `TranscriptTurn` added to `src/lib/types.ts`.
  - **4 canvas tests** (`src/routes/Brainstorm.test.tsx`, jsdom, mocked api): load-and-render
    (resolved bodies + restored transcript + banner), send-a-turn (reply + newly-resolved
    section fold into the canvas), submit-hands-off-to-the-Chamber, and redirect-a-submitted-run.
- **Frontend foundations — the app's front door + the design system (DESIGN §3–§5, §7.5;
  CLAUDE.md §4, §9; this branch).** The first executable frontend: everything the two big
  interactive phases (Brainstorm canvas, Chamber animation) will build on. LLM-free; the SPA
  never holds a secret (CLAUDE.md §6). **`npm run build` (strict `tsc -b` + vite), `npm run
  lint`, `npm run format:check` all clean; 8 tests green (`npm test`).** The pieces:
  - **Scaffold + tooling.** `package.json`/`tsconfig*.json`/`vite.config.ts`/`index.html`,
    ESLint (flat config, typescript-eslint + react-hooks), Prettier, Vitest. Vite `base` is
    `/wind-tunnel/` and routing is hash-based (CLAUDE.md §9 — Pages has no rewrites). Pinned
    to **Vite 5** to share one vite with Vitest 2 (a dual-vite install broke the plugin types
    — see Decisions). Node 22.
  - **The "Instrument" design system as CSS custom properties (§3).** `src/styles/tokens.css`
    is the single owner of the §3.2 palette (cool neutrals, the one `focus` teal accent, the
    risk scale with shape+label redundancy), the §3.3 type roles (Archivo / IBM Plex
    Sans·Serif·Mono, loaded from Google Fonts with system fallbacks) + 1.25 scale, spacing,
    and §3.6 motion tokens; `base.css` carries the reset, the shared buttons/panels, visible
    keyboard focus (§9), and a global `prefers-reduced-motion` guard (§3.6). No CSS framework
    (CLAUDE.md §4); components read tokens, never hard-code a hex/family.
  - **`src/config.ts` — the TS owner of deployment identity (CLAUDE.md §6),** mirrored by hand
    from `backend/config.py` (no Python↔TS codegen — see Decisions), kept in sync with Vite
    `base`. Nothing secret; `VITE_BACKEND_URL` selects the backend at build time.
  - **`src/lib/runCode.ts` — the one unavoidable TS copy of `pipeline/runcode.py`** (CLAUDE.md
    §6): the `WT-XXXX-XX` format over the confusable-free alphabet, `normalize`/`isValid`/
    `validate`. `runCode.test.ts` pins the shape (4 tests) so it can't drift from the Python
    owner — the resume path (§7.5) relies on them agreeing.
  - **`src/lib/api.ts` + `types.ts` — the typed §7 client.** Every backend endpoint
    (create/resume/status-poll-with-ETag/brainstorm/threshold/route/artefact), an `ApiError`
    vs `NetworkError` split, and `warmUp` — the honest Render cold-start (§5): pings
    `/api/health` with backoff, fires `onSlow` at ~45s so the copy adds "still warming up".
    `types.ts` is the frontend's read of the status.json/§7.2.6 wire shapes (node states, the
    controlled event vocabulary, questions/failure payloads, sufficiency, outline delta).
  - **The app shell + shared components.** `App.tsx` (the once-per-session gate + hash
    routes + the permanent standing disclaimer), the Console/Chamber surfaces (§3.4), the
    `BackendStatus` context (warm state shared so any screen shows the cold start honestly),
    and the reusable `Wordmark` / `StandingDisclaimer` (§4.2) / `RunCodeChip` (§3.7, §7.5 —
    one-tap copy, "it's a locator not a secret" tooltip) / `FocusTrack` (§6.1) pieces.
  - **The screens built.** `UsageWarningGate` (§4.1 — the three points, focus-marked, focus
    lands on the heading, keyboard-operable, shown once before any input); `Landing` (§5 —
    Start a new idea / quiet Resume a run, empty state as invitation, cold-start note);
    `ResumeScreen` (§7.5 — mono input, local validation first, plain error on a bad/unknown
    code, drops the user back at the right screen via `routeForStage`). `Brainstorm` (§6) and
    `Chamber` (§7) are honest shells that establish both surfaces + the run-code chip for the
    next phase to fill in.
  - **`.github/workflows/pages.yml`** — the path-filtered (`frontend/**`) Pages deploy
    (CLAUDE.md §9), actioning a pinned deploy reminder now that the SPA exists. Builds with
    `VITE_BACKEND_URL` from the `WINDTUNNEL_BACKEND_URL` repo variable.
  - **8 tests** — `runCode.test.ts` (4: accepts well-formed, normalises, rejects the excluded
    glyphs + wrong shapes) and `App.test.tsx` (4, jsdom: the gate shows before anything, the
    gate passes once to the landing, the ack persists for the session, a malformed code is
    rejected locally on the resume screen). fetch is stubbed so the render smoke never touches
    the network.
- **PoC / flow-map / feasibility — the rest of the Brainstorm backend (TECH_SPEC §7,
  §12.3/§12.4; PROJECT_BRIEF §4; DESIGN §6.3/§6.4; Stage 1; this branch).** Completes the
  Brainstorm *backend*: the optional PoC and flow-map artefacts a user can produce before
  submitting. LLM-free (§15); ruff clean. **90 backend + 184 pipeline tests green.** The pieces:
  - **`backend/brainstorm/feasibility.py` — the feasibility gate (Flash-Lite).**
    `assess_feasibility(client, *, ux_ui, happy_path)` reads the two outline sections §7 names,
    both untrusted-wrapped (§9.2), and returns `{feasible, reason}` — the `reason` is the honest
    "not a fit; you'll get a flow map instead" line shown to the user (DESIGN conditional-stage
    rule). A malformed verdict (no boolean `feasible` / no `reason`) is a loud `FeasibilityError`.
  - **`backend/brainstorm/poc.py` — the PoC generator (Flash).** `generate_poc(client, *,
    outline_md)` produces one **self-contained** HTML document. Validation is the "reject, don't
    repair" discipline the governance agents use: the output must be an HTML document **carrying
    the §12.4 limitations banner** (validated via the `poc-limitations` marker class the prompt
    mandates) — a PoC without the banner violates a first-class design requirement (DESIGN §6.3)
    and is rejected loudly (`PocError`), never committed. Strips a stray ```` ```html ```` fence.
  - **`backend/brainstorm/mapgen.py` — the flow-map generator (Flash).** `generate_flow_map(
    client, *, outline_md, poc_html=None)` returns **Mermaid flowchart source** (node/flow
    grammar, DESIGN §3.5) — validated as `flowchart`/`graph`, tolerating leading `%%` comments;
    prose is rejected (`MapError`). The map is **not** rasterised on the backend (Render can't run
    headless Chromium): the SPA renders the SVG client-side and posts it back (CLAUDE.md §9). A
    small `synthesis.py` holds the shared code-fence stripper.
  - **`backend/app.py` — three endpoints.** `POST /poc` runs the gate, then commits either
    `brainstorm/poc.html` (feasible) or `brainstorm/flow-map.mmd` (not — with the map source
    returned for the SPA), always alongside `brainstorm/feasibility.json`; returns `{produced:
    "poc"|"map", reason}`. `POST /flow-map` generates + commits the `.mmd` directly (informed by
    `poc.html` if present) and returns the source. `POST /flow-map/svg` accepts the SPA's rendered
    SVG (validated SVG, `<script>`-free, requires the `.mmd` first) and commits `flow-map.svg`.
    All three are valid only at `BRAINSTORM` (409 after submission), touch no run.json/status.json
    (Brainstorm runs on Render, not Actions), and share one call budget per request (§13).
  - **Prompts `feasibility_gate.v1.md`, `poc_gen.v1.md`, `map_gen.v1.md`** — registered in
    `prompts/manifest.yml` under their model roles (Flash-Lite / Flash / Flash per
    `config/models.yml`); each untrusted-wraps the user-derived outline text (§9.2).
  - **27 new tests** (`backend/tests/test_poc_map.py`): the three agents in isolation (verdict
    parse + rejections; PoC fence-strip / non-HTML / missing-banner / empty rejections; map
    fence-strip / leading-comment / prose-reject / PoC-reaches-prompt) and the three endpoints
    end-to-end (feasible→PoC, not-feasible→map, missing-banner→502, 409-after-brainstorm;
    map commit + PoC-informs-map; SVG commit, requires-mmd→409, non-SVG/`<script>`→400,
    off-brainstorm→409).
- **Brainstorm interview core — the co-design loop that fills the outline (TECH_SPEC §7,
  §7.1; PROJECT_BRIEF §4; Stage 1; this branch).** Turns `Stage.BRAINSTORM` from a seeded
  template into something a user drives. The pieces:
  - **`backend/outline.py` — the `Outline` document model (§7.1), the single owner of the
    outline format.** Parses the YAML front-matter + the nine anchored sections, replaces
    **whole section bodies between anchors** (regeneration at section granularity, never a
    text patch), maintains `resolved`/`updated_at`/`title`/`summary` in the same write, and
    computes the `outline_delta` (`{updated, newly_resolved, title_changed}`) the canvas
    animates. `resolved` is the single deterministic completeness record (no text heuristic);
    `SECTION_REGISTRY` is the fixed id→heading contract, asserted against the template. Round-
    trips (`parse(text).render()` reproduces an equivalent document; front-matter re-emitted
    canonically). `render_initial_outline` (the create-run write) is unchanged.
  - **`backend/brainstorm/` — the two Flash-Lite agents + the transcript.** `interviewer.py`
    (`run_interviewer`): one conversational turn — reply + write whatever sections the
    conversation now supports + set title/summary once known; write-scope is the nine registry
    ids (a stray id is dropped, not failed — the surface is conversational and re-promptable).
    `sufficiency.py` (`assess_sufficiency`): the §7.1 rubric — the **deterministic gate** (all
    nine resolved, computed) plus the **judged checks** (contradictions + happy-path
    narratability, Flash-Lite), returning `{ready, missing:[{section_id, reason}]}` with
    unresolved sections first; the judge is skipped when nothing is resolved yet (a pure
    saving — `ready` is already false). `transcript.py`: the append-only `transcript.jsonl`
    the stateless backend re-reads each turn. Prompts `interviewer.v1.md` + `sufficiency.v1.md`
    (registered, Flash-Lite), both untrusted-wrapping the user text (§9.2).
  - **`backend/app.py` — `POST /brainstorm/message` + `/brainstorm/edit-outline`.** `message`
    runs the interviewer, applies the section updates, appends both turns to the transcript,
    runs sufficiency, and commits the outline (when it changed) + transcript as one commit;
    returns `{assistant_message, outline_md, outline_delta, sufficiency, stage}`. `edit-outline`
    applies a **per-section patch** (never raw markdown, so a user can't break the anchors/
    front-matter), re-runs sufficiency, commits. Both are valid only at `BRAINSTORM` (409
    after submission). `create_app` gained an injectable `make_llm` factory (called once per
    request → a fresh call budget per turn; tests inject a scripted client).
  - **30 new tests** (`backend/tests/test_outline.py` (13): parse/render/delta, registry-vs-
    template, refine-vs-newly-resolved, registry-ordering, unknown-id reject, summary-only
    commit, round-trip, sanitisation; `test_brainstorm.py` (17): the interviewer parse/filter/
    require-message, the sufficiency gate + judged-issue + skip-when-empty + ignore-unresolved-
    judge, and the two endpoints end-to-end — resolve-and-commit, pure-question turn, prior-
    dialogue-reaches-the-model, empty→400, off-brainstorm→409, edit set/unknown/empty). LLM-
    free (§15); ruff clean. **63 backend + 184 pipeline tests green.**
- **`USER_REVISION` + `POST /api/runs/{id}/revise` — the ≤2 post-COMPLETE full-assessment
  revision path (TECH_SPEC §5.1 USER_REVISION, §5.8, §7; Stage 3; this branch).** The last
  governance stage; with it, every §5.1 stage is built. The pieces:
  - **`pipeline/agents/reviewer.py` — two new Pro passes, boundary-validated like the
    existing reviewer.** `run_revision_triage` reads the user's revision instructions
    (untrusted-wrapped, §9.2) against the completed assessment and returns
    `{amend_directives, declined}` — directives in the §11.3 format (validated for write
    scope by the *same* `_parse_directives` the review loop uses; a directive out of a
    specialist's ownership is rejected) and declined instructions each with a plain reason
    (`_parse_declined`). `run_revision_verification` is one pass (never the ≤2 loop): it
    returns a `ReviewerResult` with `amend_directives` **always empty** (a revision is one
    triage, one amendment, one verify), plus coherence findings, unresolved points for any
    unmet directive, and post-mitigation residual tiers — no asserted rating (the engine
    rates). Prompts `prompts/revision_triage.v1.md` + `revision_verify.v1.md`, both
    registered under model role `reviewer` (Pro).
  - **`pipeline/stages/full.py::user_revision` — the three §5.8 steps.** (1) triage →
    `full/revisions/rev_<N>/directives.json`; (2) targeted specialists amend their own
    directed sections via `run_specialist_amendment` (the reviewer-directive framing is
    apt — the reviewer *did* issue directives — so `_apply_amendments` is reused, now
    parameterised with a `detail` narration builder so REVIEW and USER_REVISION share it);
    (3) verify + deterministic residual recompute → `full/reviewer/ratings_residual.json`,
    with the verify pass's unresolved set written to (or clearing) `unresolved.json` and a
    `rev_<N>/verification.json` record. The whole stage re-runs from step 1 on resume
    (checkpoint = `rev_<N>/verification.json`), the same whole-stage idempotence REVIEW
    relies on; `N` is `run.json`'s `revisions.full`, incremented by `/revise` before dispatch.
  - **Archiving the superseded report (§5.8) is done at the USER_REVISION boundary, not
    inside ASSEMBLY** (`stages/assembly.py::archive_superseded`): the outgoing
    `assessment.ipynb/.html` are **moved** to `artefacts/superseded/rev_<N>/` before the
    rebuild. Doing the move here (rather than in ASSEMBLY, as §5.8's prose reads) keeps
    ASSEMBLY's idempotent-skip honest — see Decisions. ASSEMBLY otherwise unchanged except
    `gather_inputs` now sets the `revision_label` the notebook title block already renders
    ("Revision N of 2", design §8).
  - **`pipeline/run.py` — table entries + a dynamic checkpoint.** `USER_REVISION` slots
    into `_HANDLERS`/`_NEXT` (→ `ASSEMBLY`)/`_STAGE_FAIL_NODE` (`full.reviewer`)/
    `_STAGE_PHRASE`; its checkpoint output carries the revision number, so
    `_checkpoint_outputs(run, stage)` resolves `rev_<N>/verification.json` from `run.json`
    (the first stage whose checkpoint path is run-state-dependent). `StageNotImplemented`
    is no longer reachable for any §5.1 stage.
  - **`backend/app.py::POST /api/runs/{id}/revise`.** Body `{artefact:"full", instructions}`;
    valid only at `COMPLETE` (409 otherwise), empty instructions → 400, non-`full` artefact
    → 422 (the other artefacts revise on their own paths, §7). Enforces the ≤2 cap via
    `record_revision("full")` (raises at the cap → 409), commits `rev_<N>/request.json`
    alongside the advanced `run.json`/`status.json` as one atomic commit, dispatches
    `resume_from=USER_REVISION`. Mirrors `/answers`.
  - **20 new tests** (`pipeline/tests/test_user_revision.py` (12): triage returns/rejects
    (write-scope, missing-reason, untrusted-wrap), verification residual + never-directs +
    no-asserted-rating, the handler (triage→amend→verify→recompute, archive-the-outgoing,
    no-directives-still-recomputes, write-and-clear-unresolved), and the driver end-to-end
    — COMPLETE → `resume_from=USER_REVISION` → COMPLETE with the "Revision 1 of 2" label +
    the archived report, and idempotent-skip-on-resume; `test_assembly.py` (2):
    revision-label + `archive_superseded` move/idempotence; `backend/tests/test_app.py`
    (6): commit+dispatch, second-revision-increments, cap→409, off-COMPLETE→409,
    empty→400, non-full→422). LLM-free (§15); ruff clean. **184 pipeline + 33 backend
    tests green.**
- **`FULL_REVISING` + `POST /api/runs/{id}/answers` — the checkpoint-answer branch,
  driven end-to-end (TECH_SPEC §5.1 FULL_REVISING, §5.8, §7; Stage 3; this branch).**
  The path a `FULL_CHECKPOINT` pause takes once the user answers. The pieces:
  - **`pipeline/stages/full.py::full_revising` — the stage handler.** Reads
    `full/questions.json` (who asked what) and `full/answers.json` (the user's answers +
    skips). For each specialist that raised a question it re-drafts that specialist's
    **whole owned set** via `run_specialist_amendment` (a question is not tied to one
    section, so the specialist re-works its slice with the new facts in hand), with the
    Q&A as the directive. A skipped/unanswered question is rendered as an unavailable fact,
    so a section the specialist still cannot ground becomes a gap (§5.1 "skipped questions
    → gaps"). Specialists that raised no question are untouched. Writes updated
    `full/specialists/*` and `full/revised.json` (the checkpoint marker + a record of which
    specialists revised and the answered/skipped counts).
  - **`pipeline/agents/specialist.py` — the amendment framing is now parameterised.**
    `run_specialist_amendment` gained `directive_heading`/`directive_intro` (defaults =
    the reviewer-ruling wording, unchanged; `{targets}` filled with the directed ids), so
    FULL_REVISING frames the same machinery as *answered checkpoint questions* rather than
    a reviewer directive. `_build_amendment_user` takes the heading/intro through — no
    behaviour change on the REVIEW path (its tests are untouched and green).
  - **`pipeline/run.py` — table entries only.** `FULL_REVISING` slots into `_HANDLERS`,
    `_NEXT` (→ `ARCHITECT`), `_CHECKPOINT_OUTPUTS` (`full/revised.json` — so a re-dispatch
    after it committed skips it and resumes at ARCHITECT, §5.3), `_STAGE_FAIL_NODE`, and
    `_STAGE_PHRASE`. No new driver machinery: a `resume_from=FULL_REVISING` dispatch jumps
    straight past the `FULL_CHECKPOINT` pause via the existing resume block (see Decisions
    — no `_NEXT[FULL_CHECKPOINT]` is needed because a pause stage always returns before
    `_NEXT` is consulted).
  - **`backend/app.py::POST /api/runs/{id}/answers`.** Valid only while paused at
    `FULL_CHECKPOINT`+`awaiting_user` (409 otherwise). Validates every submitted id against
    `full/questions.json` (unknown id → 400; an id both answered and skipped → 400;
    duplicates → 400); partial coverage is allowed (an unaddressed question is treated as a
    skip downstream). Commits `full/answers.json` alongside the advanced
    `run.json`/`status.json` as **one** atomic commit, then dispatches
    `resume_from=FULL_REVISING`. `AnswersBody`/`AnswerItem` pydantic models.
  - **ASSEMBLY dormant slot activated.** `gather_inputs` now populates `skipped_questions`
    from `full/answers.json` × `full/questions.json`, so unanswered questions surface in the
    report's "Recommended next steps" appendix (the notebook's `_next_steps` already
    rendered them; it was fed nothing until now).
  - **17 new tests.** `pipeline/tests/test_full_revising.py` (10): `_specialist_from_node`
    round-trip + rejects, the answered/skipped directive counts, seed terms, the handler
    (revises only the questioner, skip→gap, multiple specialists, the answer text actually
    reaching the amendment prompt with the checkpoint-answer framing), the driver
    end-to-end (`resume_from=FULL_REVISING` from a paused checkpoint → COMPLETE), and
    idempotent-skip-on-resume. `backend/tests/test_app.py` (6): commit+dispatch, refuse
    off-checkpoint, unknown-id, answer-and-skip conflict, partial coverage, missing
    questions.json. `test_assembly.py` (1): skipped questions surface. LLM-free (§15);
    ruff clean. **170 pipeline + 27 backend tests green.**
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

**From the governance-fixes branch — two small known consequences, deliberate:**
- **`full_revising` is not per-specialist idempotent** (unlike drafting, now). Pulse
  commits can land partially-amended specialist files; a crash mid-revising then re-amends
  already-amended sections on retry. Low harm (narrative-only, reviewer-verified after,
  answers applied once) and rare; if it bites, give amendments the same
  per-specialist-marker treatment drafting got.
- **Live-run confirmation outstanding:** the seam fixes are proven against the recorded
  failure shapes (incl. a rehearsal over `WT-H5M2-2Y`'s real stranded state) but a live
  Gemini run hasn't happened since. Tom pressing "Resume the run" on the three failed runs
  is both the recovery and the live test.

The whole **governance half** of the pipeline is complete and driven end-to-end, and — this
branch — the **Brainstorm interview core** is built: the interviewer, the sufficiency judge,
the `Outline` document model, and `POST /brainstorm/message` + `/edit-outline`. A user can
now drive `Stage.BRAINSTORM` (converse, watch the outline resolve, see the sufficiency
banner) up to `/submit`. What remains is the rest of Brainstorm (PoC / flow-map) and the
**frontend**. Next concrete steps, in rough dependency order:

1. **The `/revise` brainstorm branches — DONE (this branch): `poc`/`flow_map` regenerate from
   the amended outline with the ≤2 cap.** The Brainstorm *backend* is now complete. The prior
   "open design question" (is an `outline` revision a distinct capped path?) is **resolved by the
   brief, not deferred:** the outline is unbounded (brief §4) and is not in the cap list (brief
   §7), so it has no `/revise` branch — the contradiction with `REVISION_ARTEFACTS`/TECH_SPEC §7
   was fixed per CLAUDE.md §2 (see Done + Decisions). **The `threshold` branch — DONE (this
   branch).** Valid only while paused at `THRESHOLD_REVIEW`, it commits the request + rewinds to
   `THRESHOLD_RECONCILING` and dispatches `resume_from=THRESHOLD_RECONCILING`; the reconciler
   re-runs with the instructions as untrusted context (`run_reconciler`'s new optional
   `revision_instructions`), steering the narrative while the untouched generalist drafts keep the
   ratings provably fixed; a per-revision `rev_<N>/reconciled.json` checkpoint keeps the
   re-dispatch from idempotently skipping. **With this every `/revise` value in TECH_SPEC §7 is
   built.** See Done + Decisions.
2. **Frontend — foundations DONE (this branch); the interactive screens remain.** The
   scaffold, the "Instrument" design system, `src/config.ts`, the run-code mirror, the typed
   API client (with cold-start), the usage-warning gate (§4), the landing/empty states (§5),
   and the resume-by-code screen (§7.5) are built, verified, and clean (see Done). What
   remains — in rough dependency order, each now standing on real foundations:
   - **The Brainstorm co-design canvas + conversation (design §6.2) — DONE (this branch).**
     The `Brainstorm` route is now the real two-pane canvas: the conversation, the live outline
     canvas (parses `outline_md`, animates `outline_delta`), the sufficiency banner (§6.2
     unlocking-not-gate), click-to-edit sections with the `you` provenance tag (§3.7), and
     Submit → Chamber. Backed by a new `GET /api/runs/{id}/brainstorm` so a page load / resume
     restores the state. See Done. **The optional PoC/flow-map actions — DONE (this branch):**
     the `BrainstormSynthesis` block, the sandboxed PoC preview, `mermaid.js` (lazy-loaded)
     rendering the map SVG client-side and posting it back (CLAUDE.md §9), the honest §6.1
     conditional-stage note, and resume-restore of both. See Done.
   - **The Chamber transparency animation (design §7.2) — the flagship — DONE (this branch).**
     The `Chamber` route now polls `getStatus` (via the new `useStatusPoll` hook, ETag-aware),
     renders the fixed node topology (`lib/topology.ts`, mirrored from `status.py`) as the
     node/flow graph + the append-only activity log (the accessibility backbone), driven by the
     whole-graph `nodes` map + the controlled event vocabulary, honouring reduced motion. One
     poll fully determines the visible state. See Done.
   - **The two Console pause screens the run breaks out to — DONE (this branch).** The threshold
     review/route screen (§7.4 — computed risk chips, divergence surfaced, `POST /threshold/
     route`) and the question checkpoint (§7.3 — batched questions from the `questions` payload,
     answer-or-skip, `POST /answers`) are built and driven by the Chamber's state machine
     directly (the Chamber renders the right face from `overall_state`+`phase`+`questions`, so
     `routeForStage` didn't need extending — everything post-Brainstorm lands on `/chamber` and
     the Chamber sub-routes internally). See Done.
   - **The report view (design §8) — DONE (this branch).** Renders `assessment.html` in a
     sandboxed iframe, open-in-tab + notebook download, and the in-app ≤2 revision affordance
     (`POST /revise`). See Done. **Deferred (a small backend follow-up):** the *exact*
     revisions-used count is not in `status.json` (it lives in `run.json`, which the SPA can't
     read), so the report states the cap ("up to 2 rounds") and the server enforces it (a spent
     cap surfaces as a plain 409 message) rather than showing "(N used.)" as §8 ideally wants.
     Adding `revisions` to the `status.json` projection (a small `status.py` change, set from
     `run.state.revisions`) would let the count show live — the "one poll determines visible
     state" way. Left for whoever next touches the status schema.
   - **The optional PoC/flow-map actions — DONE (this branch).** The `BrainstormSynthesis`
     block, the sandboxed PoC preview, lazy-loaded `mermaid.js` rendering the map SVG client-side
     and posting it back (CLAUDE.md §9), the honest §6.1 conditional-stage note, focus-track
     stages 2/3 lit from real state, and resume-restore. **With this the frontend is complete —
     every DESIGN screen is built and driven.** See Done.
3. **A first live Gemini run** to eval real generalist/reconciler/specialist/reviewer
   judgement (the LLM seam is mockable and unit-tested end-to-end, now across the whole
   governance path including revision; live quality is untested). Exercisable now via
   `POST /api/runs` → `/submit` with `WINDTUNNEL_PAT` + `GEMINI_API_KEY` set, then
   `/threshold/route {full}` and, once COMPLETE, `/revise` — no frontend required to smoke
   test with a raw HTTP client.

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

- **The §5.4 fan-out is thread-based, width 3, owned by `config/budgets.yml`
  (`claude/concurrent-specialists-aqb0t9` branch).** §5.4 says "async fan-out" without naming a
  mechanism or width. Decided: `ThreadPoolExecutor` (the transport is blocking `urllib`; the work
  is I/O-bound, so threads deliver the fan-out with no async rewrite of the seam), width from a
  new `specialist_concurrency` budgets key — Tom asked for 3, and it leaves Gemini rate headroom
  (§13). Design §7.2's "six bloom at once" is read as the unthrottled ideal; the knob reaches it
  when quota does. Corollary decided at the same time: workers never write files or commit — all
  writes/commits stay on the coordinating thread, which is how §5.4's "no repo-commit race" and
  §14's single-writer property survive per-draft progress commits. Extended to the threshold
  generalists (shared runner, `stages/fanout.py`, same knob): because the pair is symmetric by
  design, a→slot-a assignment is scheduling-dependent and deliberately left so — pinning it would
  add coordination for a distinction that carries no meaning (higher-wins is commutative).
- **A specialist owns a section *and everything under it*; sub-question keys fold, not fail
  (WT-H2A8-H3 branch).** The docs define write-scope (§9.3) at subsection granularity (`12.2`),
  but `questions.json` nests real sub-questions (`12.2.1`/`12.2.2`, `8.4.1`/`8.4.2`) under some
  sections, and the prompt shows them — an ambiguity the model resolves non-deterministically
  (the same run keyed §8.4 by the section id but §12.2 by its sub-questions). Decided: a
  sub-question id resolves to its single owned parent and is folded there losslessly; it is
  **not** a scope violation. This keeps write-scope at section granularity everywhere downstream
  (coverage, ownership 1:1, assembly, rating) — no sub-question granularity leaks — while a key
  that resolves outside the owned sections is still rejected loudly. The alternative (make the
  model always key by section id via the prompt alone) was rejected as insufficient on its own:
  LLMs are imperfect, so defense-in-depth (prompt clarity **and** a tolerant fold) matches the
  established LLM-seam precedent.
- **The downloadable `threshold.md`/`outline.md` are served from their canonical files, not
  copied into `artefacts/` (WT-H2A8-H3 branch).** TECH_SPEC §2 pictured `artefacts/threshold.md`
  and `artefacts/outline.md` copies, but nothing produced them and the build's canonical files are
  `threshold/threshold_assessment.md` and `brainstorm/outline.md`. Producing duplicates would give
  the same content two owners that can drift (violates §3). Decided: the artefact *name* is the
  stable public contract (§7); it resolves to the canonical file. `artefacts/` holds only the
  assembly-stage deliverables. TECH_SPEC §2 corrected to match (CLAUDE.md §2).
- **Artefact downloads are forced with `Content-Disposition`, not the anchor `download`
  attribute (jupyter-download-formatting branch).** The SPA is served cross-origin from the
  backend (Pages → Render), and browsers silently ignore an anchor's `download` attribute on a
  cross-origin link — so the "Download notebook" / "Download (Markdown)" links just opened the
  raw `.ipynb`/`.md` inline as text in a new tab (the WT-H2A8-H3 report bug). Decided: the
  artefact proxy (`GET …/artefact/{name}`) takes an opt-in `?download=1` query flag and, when
  set, sends `Content-Disposition: attachment; filename="<name>"`, which the browser honours
  regardless of origin. The flag is per-request rather than pinned to the artefact name because
  the same names are also served inline (iframe `src` for `assessment.html`/`poc.html`,
  `fetchArtefactText` for in-app markdown rendering); `artefactUrl(code, name, { download: true })`
  opts the three save-to-disk links in.
- **The LLM seam retries; the agent layer does not (governance-fixes branch).** The
  documents are silent on failure handling below §5.6's calm-failure rule. Decided: transient
  HTTP retries live in the transport, malformed-JSON corrective re-asks live in
  `complete_json` (both bounded, budget-charged, content never repaired — a re-ask is a fresh
  model answer, so "models argue, code computes" is untouched) — while an `AgentError`
  (valid JSON, wrong shape: missing section, off-vocabulary tier, forbidden rating key)
  still fails loudly with no retry. Shape violations are contract breaches worth a human
  look, and none has occurred live; if they start recurring, a shape-level re-ask can reuse
  the same mechanism.
- **Tolerant JSON parsing is bounded to lossless tolerances (governance-fixes branch).**
  Accepted: code fence, prose preamble before the object, trailing text after a complete
  object (`raw_decode`), raw control characters inside strings (`strict=False`). Each leaves
  the parsed content exactly what the model wrote. Rejected: any repair that guesses (quote
  fixing, comma insertion, bracket balancing) — those change content and are re-asks instead.
- **Status pulses commit per node transition, throttled for sub-activity — not a
  background-thread heartbeat (governance-fixes branch).** §6.3's "~20s" heartbeat is
  honoured by publishing at transitions (always) and drafting/retrieval events (≥15s apart).
  A true wall-clock heartbeat during one long LLM call would need a committing thread racing
  the driver's own git operations; not worth it — the SPA's honest-staleness line covers the
  bounded (≤120s per-call timeout) quiet stretch. Accepted consequence, recorded: during a
  single long Pro call the committed status can go quiet up to ~2 min; the ActivityLog says
  so honestly ("still working — last update Ns ago").
- **Prompt escaping guidance without a version bump (governance-fixes branch).** The
  JSON-escaping lines added to the two threshold prompts change no output contract —
  guidance refinement, per the interviewer/reconciler precedent recorded below.
- **A threshold revision changes the narrative, never a rating — and so the generalist drafts
  are left untouched (this branch).** TECH_SPEC §7 says the `threshold` `/revise` "re-runs
  `THRESHOLD_RECONCILING` with the instructions in context — the two generalist drafts stand
  untouched, preserving their independence, and the engine recomputes." The documents don't spell
  out the consequence, so recording it: because the drafts stand and higher-wins resolution is
  deterministic, the recomputed ratings are **identical** to the pre-revision ones. A threshold
  revision therefore steers only the reconciled *narrative and rationale*; a user cannot move a
  rating by asking (CLAUDE.md §3 "models argue, code computes"). The reconciler prompt is told to
  honour only the narrative part of any "make this lower/higher" request. This is the right
  reading of the invariant, not a limitation to apologise for.
- **The `threshold_reconciler.v1.md` prompt was extended, not version-bumped (this branch).**
  §9.1 versions prompts, but the revision-handling section is *additive* guidance for a new
  optional input block and leaves the JSON output contract byte-for-byte identical; the initial
  reconciliation path sends the exact same prompt+user it always did (the revision block only
  appears when `revision_instructions` is present). Bumping to `.v2` would fork a prompt whose
  contract didn't change. If a future change alters the reconciler's *output* shape, that is the
  moment to bump.
- **`THRESHOLD_RECONCILING` gets a per-revision checkpoint output, mirroring `USER_REVISION`
  (this branch).** A revision re-dispatch must actually re-run the reconciler, but the stage's
  standard outputs (`reconciled.json` etc.) already exist from the initial pass, so the §5.3
  idempotent-skip would wrongly short-circuit it. Following the `USER_REVISION` precedent,
  `run.py::_checkpoint_outputs` resolves the stage's checkpoint to `rev_<N>/reconciled.json` when
  `revisions.threshold > 0` (run-state-dependent, from `run.json`), and the stage writes that
  marker on a revision. The initial pass (`== 0`) is unchanged.
- **The outline is not a capped `/revise` artefact — contradiction resolved in the brief's
  favour (this branch, CLAUDE.md §2).** `statefile.REVISION_ARTEFACTS` and TECH_SPEC §7 both
  listed `outline` among the ≤2-cap revisable artefacts, but PROJECT_BRIEF §4 ("the interview
  conversation itself is unbounded") and §7 (the cap list is map/PoC/threshold/full only) say
  otherwise. This was a genuine document contradiction, not silence, so §2 applies: the brief
  governs intent and the losing documents are fixed. `outline` is removed from
  `REVISION_ARTEFACTS` and both TECH_SPEC §7 rows; the outline is refined unboundedly via
  `/brainstorm/message` + `/brainstorm/edit-outline`. This also answers the prior handoff's
  deferred question (distinct capped outline path, or same as a brainstorm turn?) — neither:
  there is no capped outline path.
- **A brainstorm `/revise` requires the artefact to already exist, and skips the feasibility
  gate (this branch).** `/revise {poc}` / `{flow_map}` 409 if the artefact was never generated
  — a revision presupposes an initial generation (brief §7), and refusing early avoids consuming
  a cap on nothing. And unlike `POST /poc` (which runs the feasibility gate and may produce a map
  *instead* of a PoC), `/revise {poc}` regenerates the **PoC** directly with no gate: the user
  asked to revise the PoC, so silently switching them to a flow map would be surprising. Each
  `/revise {artefact}` revises exactly that artefact. The initial-generation endpoints (`/poc`,
  `/flow-map`) stay uncapped (they *are* the initial generation, brief §7 "after initial
  generation"); the cap governs directed, instruction-driven revisions through `/revise`.

- **`mermaid.js` is lazy-loaded, not in the first-paint bundle (this branch).** CLAUDE.md §9
  mandates in-browser Mermaid rendering, but the engine is ~635 kB — statically importing it put
  it in the main chunk (844 kB). The flow map is optional and reached only mid-session, so the
  route dynamic-imports the wrapper (`await import("../lib/mermaid")`); mermaid becomes its own
  chunk fetched on first use and first paint drops to ~210 kB (67 kB gzip). No behaviour change,
  just deferral.
- **Both optional artefacts display in a `sandbox=""` iframe; the flow map via `srcDoc`, not
  `innerHTML` (this branch).** The PoC and flow map both derive from untrusted user text (§9.2),
  so both are displayed sandboxed (scripts + same-origin denied — display only), matching
  `ReportView`. The PoC points `src=` at the download proxy (a committed file); the client-
  rendered flow-map SVG goes in via `srcDoc` — never `innerHTML`, so untrusted-derived SVG markup
  is never injected into the app DOM (the same discipline as `lib/markdown.tsx`). `mermaid`'s
  `securityLevel: "strict"` and the backend's `<script>` refusal are the belt-and-braces around it.
- **The download proxy serves `poc.html`/`flow-map.mmd`; `GET /brainstorm` reports optional-
  artefact existence — resolving a frontend-surfaced gap (this branch, CLAUDE.md §2).** `POST /poc`
  returns only `{produced, reason}` (not the HTML), and the proxy allow-list omitted the brainstorm
  artefacts, so the SPA had no way to *display* a generated PoC or restore either artefact on
  reload. Both were genuine gaps the frontend surfaced, so filling them was part of the task:
  `_ARTEFACTS` now serves `poc.html`/`flow-map.mmd`, and `GET /brainstorm` grew an `artefacts`
  block (existence + the feasibility verdict) so a resume re-lights the focus track and re-shows
  the artefacts. Existence is read only on the load endpoint (not on every message turn — those
  don't change PoC/map state), keeping the hot path cheap.
- **On resume the flow map is re-rendered from its committed `.mmd`, not fetched as SVG (this
  branch).** The `.svg` is committed for the report; the SPA could fetch it, but re-rendering from
  the `.mmd` gives one display path (always `renderMermaid` → `srcDoc`) and heals a map whose SVG
  post was interrupted (the `flow_map_svg` flag says whether we still owe the backend one). Costs
  one extra client render on resume; avoids a second allow-list entry and a two-path display.
- **The Chamber is a state machine, not a router hand-off (prior branch).** The design (§7.2–8)
  describes the run "breaking out to the Console" for the threshold review / checkpoint and
  "settling into" the report. Rather than add routes and extend `routeForStage` to send paused
  runs to separate screens, the `Chamber` route is a single poll host that renders the right
  face inline from `overall_state`+`phase`+`questions` (graph/log, threshold review, checkpoint,
  report, concluded, failure). Why: one poll already fully determines the visible state
  (CLAUDE.md §3), so a run's face is a pure function of its status doc — a `<Navigate>` on top
  would just re-derive the same thing from the same poll, and resume-by-code already lands every
  post-Brainstorm run on `/chamber`. It also keeps the run-code chip and surface transition in
  one place. `routeForStage` therefore stayed as-is (Brainstorm vs everything-else).
- **A hand-rolled *safe* markdown renderer (`lib/markdown.tsx`), not a markdown dependency
  (this branch).** The threshold review (§7.4) renders `threshold.md`. Rather than add `marked`/
  `react-markdown` (and their sanitiser surface) for a document whose text derives from
  untrusted user content (§9.2), a ~160-line renderer builds React elements directly — raw HTML
  in the source is structurally impossible to inject (there is no `dangerouslySetInnerHTML`),
  and it covers exactly the subset the artefact uses. Risk-rating cells become the §3.2 chip.
  Revisit only if a later artefact needs a wider markdown subset than the pipeline emits.
- **The report's revision count is stated as a cap, not a live "(N used.)" (this branch).** §8
  wants the used-count visible up front, but the count lives in `run.json` (not the proxied
  `status.json`), so the SPA can't cheaply know it without a schema change. Rather than fabricate
  "(0 used.)", the report states the ≤2 cap and lets the server's honest 409 enforce it; adding
  `revisions` to the `status.json` projection is the clean fix, deferred to whoever next touches
  the status schema (noted in handoff). Honesty over a fabricated precise number.
- **Added `GET /api/runs/{id}/brainstorm` for canvas load/resume (prior branch).** §7 names
  `POST /brainstorm/message` + `/edit-outline` but no *read* endpoint; without one the SPA
  could not restore the outline + transcript on a page reload or a resume-by-code (§7.5) — a
  genuine gap the frontend surfaced, so filling it was part of the task (CLAUDE.md §2, "fixing
  the contradiction is part of your task"). It re-reads committed state only and makes no
  commit; it reuses the existing `_brainstorm_response` tail so the sufficiency shape matches
  the POST endpoints exactly.
- **The `you` provenance tag marks sections *edited via the canvas this session*, tracked
  client-side (this branch).** `outline.md` records completeness (`resolved`) but not *who*
  wrote each section (interviewer vs. user), so the wire can't distinguish provenance. Rather
  than invent a backend field, the canvas tags a section `you` when the user saves an edit to
  it in the current session — an honest "you touched this", the affordance §3.7 asks for,
  without a new persisted contract. Revisit if per-section provenance ever needs to survive a
  reload.
- **PoC/flow-map deferred to a follow-up, not bundled into the canvas commit (this branch).**
  The mandatory co-design loop (interview → sufficiency → submit) is a complete, testable
  vertical; the optional PoC/flow-map (focus-track stages 2/3) need `mermaid.js` (a new
  dependency) and a sandboxed PoC preview, enough surface to warrant their own coherent commit
  (CLAUDE.md §4 "small, coherent commits"). The focus track already shows them as optional and
  upcoming, so the deferral reads honestly on screen.
- **Frontend router: `react-router-dom` with `HashRouter` (this branch).** CLAUDE.md §9
  mandates hash routing (Pages has no rewrites) but names no library. Chose react-router over
  a hand-rolled router — the app will grow many routes (Brainstorm, Chamber, threshold,
  checkpoint, report) and react-router is the maintained, idiomatic choice; `HashRouter`
  satisfies the constraint with zero server config.
- **Vite pinned to 5, not 6 (this branch).** Vitest 2 pulls its own nested Vite 5; with the
  app on Vite 6 the two vite copies' plugin types conflict at `tsc` build time. Aligning on a
  single Vite 5 removes the dual install. Revisit when Vitest ships a Vite-6-native line.
- **The usage-warning gate is acknowledged once per *session* (`sessionStorage`), not
  persisted (this branch).** Design §4.1: "shown once per session before input; not nagged
  thereafter." A new tab / new session re-shows it — the honest reading of "per session", and
  it means the public-repo warning is never permanently dismissed-and-forgotten.
- **Resume routing keys on the run.json `Stage` value, not `phase` (this branch).**
  `BRAINSTORM`'s phase is `threshold` (statefile `_STAGE_PHASE`), so phase can't distinguish
  "still in Brainstorm" from "in the threshold pipeline". `routeForStage` therefore branches on
  the stage string (`BRAINSTORM` → the canvas; everything else → the Chamber), which the
  next-phase pause screens extend.
- **`src/config.ts` mirrors `backend/config.py` by hand; no Python↔TS codegen (this branch,
  confirming the prior handoff's note).** Two deployment-identity facts (owner/repo/branch,
  the run-code alphabet) live in both languages because neither runtime can import the other.
  Each file names itself the owner-to-copy-from; a change touches both in one commit. A
  generator would be more machinery than two rarely-changing constants justify.
- **The flow-map SVG is rendered client-side and posted back, not rasterised at generation
  time — resolving a §7 ↔ CLAUDE.md §9 contradiction (this branch).** TECH_SPEC §7's row read
  "Mermaid → SVG at generation time; both committed", but CLAUDE.md §9 (which governs deploy
  decisions, §2 precedence) pins that the SPA renders Mermaid with `mermaid.js` and posts the
  SVG back, because Render's free tier can't run headless Chromium. Resolved in favour of
  CLAUDE.md §9: `POST /flow-map` commits `flow-map.mmd` and returns the source; a new `POST
  /flow-map/svg` accepts the SPA's rendered SVG and commits `flow-map.svg`. The losing document
  was fixed — TECH_SPEC §7 now describes the two-step flow and cites CLAUDE.md §9. (The
  pipeline's *report* diagrams, run in Actions where Chromium is available, may still use the
  Mermaid CLI — a different context, no contradiction.)
- **The PoC limitations banner is validated as present (reject if absent), not injected by the
  backend (this branch, `backend/brainstorm/poc.py`).** DESIGN §6.3/§12.4 require the banner to
  be a first-class element *authored into* `poc.html`, "not chrome the app wraps around it". So
  the backend does not add it; it requires the model to, and validates via the `poc-limitations`
  marker class the prompt mandates — a PoC missing the banner is a loud `PocError` (→ 502, the
  user regenerates), not a silently-shipped artefact. This is the "reject, don't repair"
  discipline the governance agents use, applied where a design invariant is at stake (unlike the
  interviewer, which *drops* stray ids because nothing integrity-critical rides on a re-prompt).
- **`/poc` and `/flow-map` regenerate freely; the ≤2 cap is a `/revise`-path concern, not
  enforced here (this branch).** Calling `/poc` or `/flow-map` again overwrites the prior
  artefact — the honest behaviour for brainstorm artefacts, which "regenerate from the amended
  outline" (§7). The per-artefact revision cap (`run.json.revisions.poc`/`.flow_map`) is consumed
  by the `/revise` branches (deferred, handoff step 1), which will call these same generators.
  Keeping generation uncapped and revision capped mirrors how governance artefacts work (initial
  generation in the pipeline is uncapped; changes go through `/revise`).
- **A canvas edit (`/brainstorm/edit-outline`) is a per-section patch, not raw markdown
  (this branch, `backend/app.py::EditOutlineBody`).** §7 says the endpoint "accepts a patch
  to outline.md"; the shape is left open. Chosen: `{sections:{id:body}, title?, summary?}`,
  applied through the same `Outline.apply_updates` the interviewer uses. This keeps the
  outline the single source of truth and makes it structurally impossible for a user edit to
  break the section anchors or front-matter (a raw-markdown PUT could). To *un-resolve* a
  section is out of scope (an empty body is ignored, never clears a section).
- **A stray section id from the interviewer is dropped, not failed (this branch,
  `brainstorm/interviewer.py`).** The governance agents reject out-of-scope keys loudly
  (§9.3) because a bad key there corrupts an integrity artefact. The Brainstorm surface is
  conversational and fully user-revisable, so a hallucinated id costs a re-prompt, not a
  lost run — the interviewer filters unknown ids and keeps the turn alive; the one hard
  requirement is a non-empty `assistant_message`.
- **The sufficiency judge (Flash-Lite) is skipped when no section is resolved yet (this
  branch, `brainstorm/sufficiency.py`).** The deterministic gate already makes `ready` false
  while any section is unresolved, and there is nothing for the judge to contradict, so the
  call is a pure saving with an identical result. It runs from the first resolved section on,
  so contradictions surface during refinement, not only at the end.
- **The outline front-matter is canonicalised on the first amendment (this branch,
  `backend/outline.py::Outline.render`).** `render_initial_outline` keeps the template's
  inline guidance comments verbatim (§7.1 "copies it verbatim"); the first interviewer/canvas
  write re-emits the front-matter in canonical key order (via `json.dumps`, valid YAML) and
  drops those comments. The file is backend-owned machine state after creation, so this is a
  one-time cosmetic normalisation, not a contract change — the keys and values round-trip.
- **The superseded report is archived at the USER_REVISION boundary, not inside ASSEMBLY
  (this branch, `stages/full.py::user_revision` → `stages/assembly.py::archive_superseded`).**
  §5.8's prose reads "advances to ASSEMBLY, which first archives the outgoing
  `assessment.ipynb/.html`". But ASSEMBLY's idempotent-skip (§5.3) keys on the existence of
  those very files, so if ASSEMBLY archived them, the driver would first check "assessment.*
  exist? → skip ASSEMBLY" and the archive+rebuild would never run on a revision (the old
  report always exists). Resolved by **moving** the outgoing files to
  `artefacts/superseded/rev_<N>/` as USER_REVISION's first action: ASSEMBLY's checkpoint
  files are then absent for a revision, so the driver rebuilds. The observable §5.8 contract
  (outgoing archived, then rebuilt with the "Revision N of 2" label) is preserved exactly;
  only *which stage does the move* differs, and it is committed atomically with the rest of
  USER_REVISION's checkpoint so the move and the marker never drift.
- **USER_REVISION's verification `unresolved.json` replaces, rather than appends to, any
  prior `unresolved.json` (this branch).** The verify pass re-reads the whole amended
  assessment, so its unresolved set is the authoritative post-revision picture; keeping a
  stale pre-revision list beside it (or accreting across revisions) would misreport the
  report's "Points of unresolved disagreement". A genuinely persisting disagreement is still
  visible to the verify reviewer (same drafts) and re-recorded. One owner for the report's
  unresolved list; a clean verification removes the file.
- **USER_REVISION's checkpoint path is resolved from `run.json` at check time, not a static
  `_CHECKPOINT_OUTPUTS` table entry (this branch, `run.py::_checkpoint_outputs`).** It is
  `full/revisions/rev_<N>/verification.json`, and `N` is `revisions.full` — the first stage
  whose idempotence marker depends on run state. Every other stage keeps its static tuple;
  only USER_REVISION routes through the resolver. (The whole stage re-runs from step 1 on
  resume, like REVIEW — on a fresh Actions disk an uncommitted partial left nothing, so
  re-running triage→amend→verify is clean.)
- **FULL_REVISING re-drafts each questioning specialist's *whole* owned set, not a
  question-scoped subset (this branch, `stages/full.py::full_revising`).** A checkpoint
  `question_id` is `<specialist>-N` (specialist.v1.md) and is **not** tied to a specific
  section — the tool doesn't record which owned section a question bears on. So the honest
  target is the specialist's whole owned set (§5.1 "revises **its own sections**"), passed
  to `run_specialist_amendment`; the specialist re-works its slice with the answers in
  hand and gaps whatever a skip left ungroundable. Specialists that raised no question are
  untouched. Cheaper question→section scoping would need the specialists to tag questions
  with a section id — a future prompt/schema change, not assumed now.
- **No `_NEXT[FULL_CHECKPOINT]` entry; the checkpoint resumes into FULL_REVISING via the
  `resume_from` dispatch, not a `_NEXT` edge (this branch, `run.py`).** A pause stage
  always `return`s from `_drive` before `_NEXT`/`_resolve_next` is consulted, so an edge
  out of `FULL_CHECKPOINT` would be dead config. The backend's `/answers` dispatch sets
  `resume_from=FULL_REVISING`, and `run_pipeline`'s resume block advances straight there —
  the same mechanism the threshold pause already uses. (The prior handoff suggested adding
  the edge; it's genuinely unreachable, so it's deliberately omitted with this note.)
- **FULL_REVISING's durable checkpoint marker is `full/revised.json`, not the updated
  specialist files (this branch).** The specialist JSONs already exist from FULL_DRAFTING,
  so their existence can't gate idempotent resume (§5.3). `full/revised.json` (which
  specialists revised + answered/skipped counts) is the one new artefact whose presence
  proves the stage completed, so it is FULL_REVISING's `_CHECKPOINT_OUTPUTS` entry. It
  also doubles as the FULL_REVISING half of the `gaps.json`-style record the tree envisions
  (the aggregated gap register itself is still computed at ASSEMBLY from the specialist
  drafts — one owner for that fact).
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
  and gap untouched. *(Amended by `claude/agent-error-legal-amendment-23lu5v` after run
  WT-H2A8-H3: an owned-but-non-directed key is now discarded as an echo rather than
  rejected — the target-scoped merge means it could never land — while a non-owned key
  is still rejected loudly. See Current stage.)* So an amendment cannot silently drop or rewrite a specialist's other
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
  heartbeat and failure handling are stage-agnostic. Only `USER_REVISION` remains
  unimplemented; routing to it raises `StageNotImplemented`, which the §5.6 handler
  surfaces as a calm failure.
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

- **Redeploy the Render backend so it carries the `/brainstorm/upload` route (and any
  endpoint newer than the last deploy) — the actual fix for the "Not Found" upload bug.**
  The file-upload endpoint landed in commit `f9f2b0d` (merged as #31); the deployed backend
  is running an older build, so the SPA's upload POST hits a route the server doesn't have and
  gets a bare 404. **Trigger a manual deploy in the Render dashboard** (Manual Deploy → Deploy
  latest commit), or, if Render's auto-deploy is watch-path-scoped to `backend/**` (CLAUDE.md §9),
  merging any backend change to `main` will redeploy it. Verify by watching the deploy pick up a
  commit at/after `f9f2b0d`. This is the deploy-discipline hazard pinned in CLAUDE.md §9 biting for
  real. The frontend now degrades gracefully in the meantime (an honest "server may be running an
  older version" message instead of "Not Found"), but the upload only *works* once the backend is
  redeployed.

- **~~The `WINDTUNNEL_PAT` needs `actions:write` added~~ — RESOLVED (July 2026).**
  Evidenced in the repo history: `governance.yml` now runs on submit (runs `WT-TR4C-DC`,
  `WT-PX5H-3D` and `WT-H5M2-2Y` all show pipeline heartbeat/checkpoint/failure commits
  from Actions), so the regenerated PAT carries **actions:write** and dispatch works.
  Those three runs then failed *inside* the chamber at the LLM seam — fixed on the
  governance-fixes branch (see Current stage / Done). **The one manual step left: open
  each failed run in the Chamber and press "Resume the run"** (or
  `POST /api/runs/<code>/redispatch`) — each resumes idempotently from its last
  checkpoint (`WT-PX5H-3D` will skip its committed drafting and go straight to the
  reconciler).

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
OFF or watch-scoped to `backend/**`; backend commits via the GitHub Contents/Git-Data
API, not `git push`.

- **SPA path-awareness + `pages.yml` — DONE (this branch).** Vite `base` is
  `/wind-tunnel/`, routing is hash-based, and `.github/workflows/pages.yml` deploys
  `frontend/**` to Pages. Two things Tom still needs to do for the deploy to work end to
  end: (1) set **Pages → Build and deployment → Source = GitHub Actions** in repo settings;
  (2) set the **`WINDTUNNEL_BACKEND_URL` repo variable** to the Render backend URL so the
  built SPA points at it (falls back to `http://localhost:8000` for local dev). The backend
  `cors_origins` already allow the Pages origin (`backend/config.py`).
