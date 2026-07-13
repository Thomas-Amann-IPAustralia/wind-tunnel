# Design Brief — Windtunnel (working title)

**Version:** 1.0 · **Date:** 11 July 2026 · **Author:** Drafted with Claude from `PROJECT_BRIEF.md` (v1.0).

**Purpose of this document:** This is the design source of truth for Windtunnel. It owns the things the project brief handed to design — canvas layout, stage telegraphing, warning treatments, the transparency animation storyboard, and report styling — and resolves them into decisions a developer can build against in Claude Code. Where the project brief has already decided something, this brief inherits it and does not re-open it. Where design has made a call, it is recorded as made. Where a decision is genuinely Tom's, or needs to be coordinated with the tech-spec instance, it is flagged as such. Companion files: `PROJECT_BRIEF.md`, `TECH_SPEC.md`.

---

## 0. How to read this document

Three kinds of statement appear here, and they are marked so the reader always knows which is which:

- **Decided (design).** A design call this brief makes and expects the build to follow. Most of the document.
- **For the tech spec.** Something the animation or UI needs from the pipeline — chiefly the `status.json` event vocabulary in §7.2.6. Design defines the *need*; the tech-spec instance defines the exact payload. These are the coordination points.
- **For Tom.** A genuine open choice (the name, final risk-label wording, font substitutions). Collected in §11.

The register throughout matches the two source documents: plain, direct, Australian. Reasoning is written as prose; specifications are structured where structure earns its place. Trust is the job of this design, so the brief tries to model the honesty it asks the product to have.

---

## 1. Naming

**For Tom.** The brief calls the name a placeholder and invites alternatives, so here is a considered view rather than a silent default.

**Recommendation: keep Windtunnel.** The metaphor is doing real work — *test the design under load before you build the aircraft* — and the whole product experience can hang off it honestly: the brainstorm phase builds the model, the governance phase runs it through the tunnel, and the report is the test data you hand to the engineers. It is concrete, memorable, and not overused in gov-tech. One word (`Windtunnel`) reads as a product; two words (`Wind Tunnel`) reads as the facility. The one-word form is preferred for a product name.

If a change is wanted, the shortlist below keeps the "prove it before you commit" idea and avoids anything that implies approval:

| Name | Why it works | Watch-out |
| --- | --- | --- |
| **Preflight** | Aviation pre-check; a disciplined checklist run *before* you fly, never a clearance to fly. Sits beautifully next to "draft, not approval." | Slightly softer than the wind-tunnel image. |
| **Proving Ground** | Where you test something hard before it goes into service. Serious, plain, Australian-plausible. | Two words; a touch generic. |
| **Shakedown** | A shakedown run tests a new vessel or aircraft under real conditions and finds the faults. Honest about the point being to surface problems. | Informal register; the criminal sense exists. |

Everything downstream in this brief is name-agnostic; swapping the wordmark is a one-token change. The rest of the document says *Windtunnel* for concreteness.

---

## 2. Design principles

**The experience in one line.** A lens coming into focus: the user starts with something blurry, watches it sharpen through their own decisions, then watches a visible, comprehensible machinery of experts stress-test it — and ends holding a document they'd be proud to hand to a subject matter expert.

Six principles form the spine. Every later decision should be traceable to one of them; if a proposed screen can't be, it is probably decoration and should be cut.

**1. Trust is the design's only real deliverable.** This is a governance instrument shown to public servants and, at the demo, to a room of them. Everything else — polish, motion, cleverness — is in service of one outcome: a non-expert finishes a run *believing* the assessment was thorough, and a subject-matter expert opens the report and *finds* that it was. Where trust and flourish conflict, trust wins without discussion.

**2. Honesty in every state.** The system waits, sleeps, pauses, and sometimes fails. Each of those is designed as a first-class, plainly-worded state, not an apology or a fake spinner. A ~60-second cold start is named as a ~60-second cold start. A ten-minute stage says it usually takes ten minutes. A failure hands back the run code and says what to do. Honest waiting is more trustworthy than a progress bar that lies.

**3. The lens is made of resolution, not blur.** The "coming into focus" metaphor is expressed as things *resolving* — a ghosted outline filling in section by section, an inactive node settling into a live one — never as literal blur on content (which fails legibility and annoys). Focus is a state the user *drives*, and they should see their decisions do it.

**4. One visual language for the machinery.** The flow map, the pipeline animation, and the report's diagrams all speak the same node-and-edge grammar. Learn it once, read it everywhere. This suits the subject (a pipeline of experts) and the user's own taste for structured, node-based thinking, and it makes the "visible, comprehensible machinery" requirement literal.

**5. Drafts, never approvals — in the language, not just the fine print.** Nothing in the visual system may imply the tool authorises, clears, or approves an AI use case. Outputs are consistently framed as *well-evidenced drafts for expert review*. The disclaimer is not a wall to click past; it is a stance the whole interface holds.

**6. Accessible and projector-proof by construction.** WCAG 2.1 AA is a floor, not a finish line. Every information channel carried by colour or motion has a redundant channel (label, shape, text). This is the same discipline that makes the product survive a washed-out projector in a competition room, so accessibility and demo-robustness are the same work done once.

---

## 3. The design language

### 3.1 Aesthetic direction — "Instrument"

The product's world is a wind tunnel control room, an optical bench, an aircraft instrument panel, a well-made scientific measuring device: precise, calm, legible, quietly confident, built to be read correctly under pressure. That is the aesthetic — **Instrument**. Not a startup landing page, not a government masthead, not a document template. A trustworthy tool with gauges you can read.

This direction is chosen partly to *avoid* the looks that currently signal "generated": the warm-cream-and-terracotta serif, the near-black-with-one-acid-accent, and the hairline-broadsheet. Windtunnel is none of those. It is cool, engineered, and spends its one bold move on the flagship animation (§2, principle: spend boldness in one place).

### 3.2 Colour

A restrained palette: cool neutrals, one signal accent, and a disciplined risk scale. Values are starting points tuned to hit AA; the build should verify contrast and may nudge lightness.

| Token | Hex | Role |
| --- | --- | --- |
| `ink` | `#161A1D` | Primary text. Graphite, not pure black — reads calmer, still AA-strong on `paper`. |
| `paper` | `#F6F7F8` | App ground (the "console"). Deliberately cool off-white — *not* cream — to sit in the instrument world and steer clear of the cream cluster. |
| `slate` | `#5B6670` | Secondary text, borders, inactive structure, ghosted-outline placeholders. |
| `chamber` | `#0F151A` | The deep surface of the governance animation (the "test chamber" / instrument panel). Blue-cast charcoal, distinct from generic near-black. |
| `focus` | `#0E7C74` | The single accent: active, live, resolved, "in focus." Deep teal-cyan — optical/technical, unmistakably not gov.au blue and not an AI-cluster accent. Text-safe on `paper`. |
| `focus-glow` | `#39C9BC` | Brighter sibling of `focus`, used *only* for glows, pulses and airflow on the dark `chamber` surface where the deep teal would be too quiet. |
| `vapour` | `#8FB9C4` | Airflow/flow-line colour in the animation only — the wind-tunnel smoke streams. Never used for text. |

**Risk-rating scale.** The DTA tool's Table 2 produces a rating per risk category; the exact labels are the tool's, so the design accommodates a 4–5 step scale without hard-coding wording. Each step is a **chip** carrying colour **and** label **and** a weight/shape cue, so it never depends on colour alone.

| Step | Hex | Redundant cue |
| --- | --- | --- |
| Low | `#2E7D5B` | thin ring, lightest fill |
| Medium | `#B7791F` | medium ring |
| High | `#C05621` | heavy ring |
| Very High / Extreme | `#9B2C2C` | filled solid + a small ▲ mark |

`amber` (`#B7791F`) also carries **waiting/pause** states, and a muted clay (`#9B2C2C` at reduced saturation) carries **failure** — calm, never a blaring alert red. Success/completion uses `focus`.

### 3.3 Typography

The type system is one engineered superfamily plus one signage face. It is chosen because it *means* something here, not because it is available.

- **Display & labels — Archivo (Expanded for large moments).** An expanded technical grotesque that reads like facility signage and instrument-panel labelling. Used with restraint: headings, stage labels, node names, the wordmark.
- **App body & UI — IBM Plex Sans.** Plex was drawn as a technology company's instrument-like identity; it is precise but humane, and it is not the Inter default. This carries the interface.
- **Report body — IBM Plex Serif.** The final report must read as a *document* a director takes seriously. The serif from the same superfamily gives gravitas while staying cohesive with the app.
- **Data, run codes, citations, timestamps, provenance — IBM Plex Mono.** Mono makes `WT-7K3D-Q2` unambiguous, sets page-cited references cleanly, and ties the whole thing to the "machinery" feel.

Using the Plex superfamily across app, report and code gives cohesion for free (§ principle 4): the same voice, three registers. **For Tom:** these are all free and GitHub-Pages-friendly, and any of them can be substituted — the system depends on the *roles* (a signage display, a UI sans, a document serif, a data mono), not the specific families.

**Type scale (starting point, 1.25 ratio):** 12 / 14 / 16 (base) / 20 / 25 / 31 / 39 px. Body text no smaller than 16px; captions and data no smaller than 12px and never carrying meaning that isn't repeated in body copy.

### 3.4 The two surfaces — Console and Chamber

The product has a spatial arc, and it is the one justified aesthetic risk in this design:

```
  BRIGHT WORKSHOP            THE TEST CHAMBER              BACK IN THE LIGHT
  ┌───────────────┐         ┌───────────────┐            ┌───────────────┐
  │  Console       │   →     │  Chamber       │     →      │  Report        │
  │  (paper, light)│         │  (chamber,dark)│            │  (paper, light)│
  │  you build     │         │  you watch     │            │  you hold      │
  └───────────────┘         └───────────────┘            └───────────────┘
     Brainstorm               Governance run                Final artefact
```

- **Console (light, `paper`).** Everything the user *does*: the warning gate, the brainstorm conversation and canvas, the PoC, the threshold review, the question checkpoint. Calm, legible, document-adjacent.
- **Chamber (dark, `chamber`).** The one place the user *watches*: the transparency animation. Entering governance is a deliberate moment — the surface deepens, the machinery lights up, and the user shifts from author to witness. This is justified because the brief itself frames governance as the heart, a different mode of engagement, and the animation as the flagship "much more interesting loading screen." The dim chamber makes the glowing pipeline the hero and reads, correctly, as *the test facility running*.

The transition between them (§7.1) is one of only two orchestrated motion moments in the product; everything else is quiet.

### 3.5 The node/flow visual grammar

One grammar, used by the flow map (Stage 3), the pipeline animation (§7.2), and the report's diagrams:

- **Node** = an actor, system, data store, or agent. A rounded rectangle. Carries a label (Archivo), an optional type glyph, and a state.
- **Edge** = a flow of information or an artefact. A directed connector. Can carry an ambient flow animation in the Chamber.
- **Node states** (shared vocabulary): `pending` (slate outline, low emphasis) · `active` (focus ring + slow pulse) · `waiting-on-you` (amber, expectant) · `complete` (settled, small check) · `failed` (muted clay, calm).

Because it is one grammar, a user who has seen their own flow map in the brainstorm phase already knows how to read the pipeline animation. Familiarity is a trust device.

### 3.6 Motion language

Motion is deliberate and scarce. Four named behaviours, each with a reduced-motion equivalent that loses no information (the activity log always carries the full story in text, so nothing is motion-dependent):

| Behaviour | Full motion | `prefers-reduced-motion` |
| --- | --- | --- |
| **Resolve** (outline section fills, node goes live) | brief sharpen: opacity 0→1 + 2% scale settle, ~250ms. Never blur. | instant state change |
| **Settle** (stage/node completes) | soft focus-coloured flash fading ~1.2s, then check | check appears, no flash |
| **Pulse** (active node/agent) | slow 2s breathing ring in `focus-glow` | static "active" ring |
| **Airflow** (active edges in Chamber) | slow continuous `vapour` streams along edges — the "alive, not frozen" signal during long waits | static directional ticks |

Two orchestrated moments only: entering the Chamber (§7.1) and the report's arrival. Everywhere else, restraint.

### 3.7 Iconography, chips and the run-code element

Line icons at a single weight, geometric, instrument-like; only where they aid scanning, never decorative. Three recurring components deserve naming because they appear across screens:

- **Risk chip** — colour + label + shape (§3.2). Appears in threshold review and the report.
- **Provenance tag** — a small mono tag marking who authored a span: `agent` vs `you` (user edits). Honest attribution is a trust device and feeds the report's provenance.
- **Run-code chip** — the persistent `WT-7K3D-Q2` element (§7.5), mono, with a one-tap copy affordance.

### 3.8 Voice and copy rules

Copy is design material. Rules, applied everywhere:

- **Plain and active.** Buttons say what happens: *Submit to assessment*, not *Proceed*. The same action keeps its name through the flow (a *Submit* button leads to a *Submitted* state).
- **Name things from the user's side.** *Your outline*, *the specialists' questions*, *your run code* — not *the pipeline state object*.
- **Failure and emptiness give direction, not mood.** No apologies, no vagueness. *"The run stopped at the threshold stage. Your progress is saved. Paste your run code to pick up where it left off."*
- **Never imply approval.** Say *draft assessment for expert review*. Never *approved*, *cleared*, *compliant*, *passed*.
- **Disclaimers inform, they don't perform.** Written like a helpful colleague setting expectations, not a legal department covering itself.

---

## 4. The gate before anything — usage warning & standing disclaimer

### 4.1 The pre-input warning

Shown **before any input is accepted**, on first arrival, on the Console surface. It must be genuinely prominent and plainly worded without reading as a legal wall — the difference is achieved by treating it as *orientation the user needs* rather than *terms they must survive*.

**Content, in plain language, three points the user actually has to hold:**

1. **Keep it at OFFICIAL.** *Don't enter anything above OFFICIAL. No OFFICIAL: Sensitive, nothing security classified, and no personal information about identifiable people.*
2. **This is public.** *Everything you type or generate here is saved to a public GitHub repository. Anyone on the internet can read it. Treat this like posting in the open.*
3. **This is a draft tool.** *What you get back is a draft to give your subject-matter experts. It isn't an approval, and it isn't legal advice.*

**Treatment.**

```
┌──────────────────────────────────────────────────────────┐
│  Before you start                                        │  ← Archivo, calm not shouty
│                                                          │
│  ◆ Keep it at OFFICIAL — no sensitive, classified or     │  ← three points,
│    personal information.                                 │     each with its own
│  ◆ This is public — everything you enter is saved to a   │     line and a quiet
│    world-readable GitHub repo.                           │     focus-coloured mark
│  ◆ Draft only — for your SMEs to review. Not an          │
│    approval. Not legal advice.                           │
│                                                          │
│  [ I understand — continue ]                             │  ← single explicit action
└──────────────────────────────────────────────────────────┘
```

- Prominence comes from **space, position and a single clear focus mark**, not from red borders or all-caps. It occupies the screen on first contact; it is not a dismissible corner toast.
- The "public repo" point is the one users will underestimate, so it gets the plainest, most concrete wording ("*anyone on the internet can read it*").
- Acknowledgement is one explicit action (*I understand — continue*). The gate is shown once per session before input; it is not nagged thereafter (the standing disclaimer, below, carries the reminder quietly).
- **Accessibility:** this is the first thing a screen reader meets — it is a labelled region announced on load, fully keyboard-operable, focus lands on the heading, and the continue action is reachable by tab immediately.

### 4.2 The standing disclaimer

After the gate, the *draft-not-approval* stance never fully leaves the screen — but it recedes to a persistent, quiet line rather than repeating the whole warning:

- A slim, permanent footer strip (Console and Chamber both): *"Windtunnel produces drafts for SME review — not approvals, and not legal advice."* Low emphasis, always legible, never dismissible.
- Every generated artefact (outline, threshold assessment, report) carries the same line in its own header (§8), so it travels with the document when downloaded or printed.

---

## 5. First contact — cold start & empty states

The Render backend sleeps when idle; the first request can take ~60 seconds. This is designed as an honest, on-brand *warm-up*, not a hidden delay:

- **Wake state.** When the SPA's first call finds the backend cold, show a calm Console panel: *"Warming up the tunnel — this can take up to a minute the first time."* Genuine, not a fake spinner implying imminence. A slow `focus` progress indication that is honest about being indeterminate. If it crosses ~45s, add: *"Still warming up — nearly there."*
- The metaphor earns a light touch here (*warming up the tunnel*) but the information (up to a minute, first time only) is the point.
- **Empty states, written as invitations, not blanks:**
  - *No run yet (landing):* a single clear path in — *Start a new idea* — and a quiet secondary *Resume a run* (paste a run code, §7.5).
  - *Outline before any answers:* the **ghosted template** — every outline section present as a low-emphasis heading with a one-line placeholder of what will go there. This is the lens's starting point: the whole shape visible but unresolved, waiting for the user's decisions to bring it into focus.
  - *Governance not yet started:* the Chamber shown as the full pipeline map in `pending` state before the first event — *"Ready to run. Here's every stage your idea will go through."* The user sees the entire machinery before it starts, which is itself reassuring.

---

## 6. Brainstorm phase

### 6.1 Stage telegraphing — the focus track

Three stages: **1 · Scoping interview** (mandatory) → **2 · Proof of concept** (optional, conditional) → **3 · Flow map** (optional). The user must always know which stage they are in, what it is for, and what it produces.

The device is a **focus track** — a persistent horizontal progression at the top of the Console. It uses real numbering because these stages *are* a real sequence (§ frontend principle: number only when order carries meaning):

```
  ●━━━━━━━━━━━━━━━━━━━━━━━━━━○─────────────────────○
  1 · Scoping interview      2 · Proof of concept    3 · Flow map
  in focus                   optional · not yet      optional · not yet
  → a structured outline     → an HTML preview        → an architecture map
```

- The **current stage is crisp and forward** (full `ink`, `focus` marker, a one-line "what this produces"). Upcoming stages are present but quiet (`slate`), clearly labelled **optional** where they are — never hidden, so the user sees the whole journey, but never so faint they fail contrast (they sit at AA against `paper`; "quiet" is emphasis, not illegibility).
- The lens metaphor lives in the **transition, not a permanent gimmick**: when a stage completes, it *settles* (§3.6) and the next stage *resolves* forward into focus. That is the whole "coming into focus" idea, expressed once per stage change, legibly.
- Each stage node states its **artefact** ("→ a structured outline"), so telegraphing covers all three required things — where you are, what it's for, what it produces — in one glance.
- Conditional stages are honest: Stage 2 only becomes available if the feasibility gate says a PoC would help; if not, the track shows *"Proof of concept — not a fit for this idea; you'll get a flow map instead"* with a one-line why, exactly as the brief requires.

### 6.2 The console — conversation + live outline canvas

Stage 1 is the product's co-design heart: a conversation on the left, a live-updating outline document on the right. The canvas is the hero; the chat serves it.

```
┌───────────────── focus track (§6.1) ─────────────────┐
├──────────────────────────┬───────────────────────────┤
│  CONVERSATION            │  YOUR OUTLINE  [download ⤓]│
│                          │                            │
│  interviewer: multiple-  │  1. Problem      ▓▓▓ ✓     │  ← resolved section
│  choice + free-text      │  2. Users        ▓▓░       │  ← just updated (settling)
│  ...                     │  3. Data         ░░░       │  ← ghosted, not yet
│                          │  4. Happy path   ░░░       │
│  [ your reply ]          │  5. Constraints  ░░░       │
│                          │  ...                       │
├──────────────────────────┴───────────────────────────┤
│  Windtunnel produces drafts for SME review …  (§4.2)  │
└───────────────────────────────────────────────────────┘
```

**How outline changes draw the eye.** The user must *see* their answers land — authorship is the emotional core of the brainstorm.

- The outline begins fully **ghosted** (every section present as a `slate` heading + placeholder — the blurry whole). As the interview progresses, sections **resolve** (§3.6): the newly-written text fades in, the section briefly **settles** with a `focus` flash, and an *"updated just now"* mono tag appears and then fades.
- If the changed section is off-screen, the canvas **auto-scrolls** it into view (reduced-motion → jumps, no animation).
- The chat and canvas are visibly coupled: when the interviewer's turn produces an outline change, a hairline `focus` connector briefly links the message to the section it wrote. The user learns, wordlessly, *"what I say lands there."*

**User edits to the canvas.** The outline is the single source of truth (§ project brief: amendments regenerate downstream artefacts), so user editing is first-class, not an afterthought:

- Any section is **click-to-edit** inline. Saved edits are marked with a **`you` provenance tag** (§3.7), visually distinct from `agent`-authored text — honest about who wrote what, and this attribution flows through to the report's provenance.
- On a user edit, the interviewer **acknowledges in chat** (*"You've updated the Data section — I'll work with that"*), closing the loop so edits feel heard, not swallowed.
- If an edit introduces a contradiction, the sufficiency check (below) surfaces it gently rather than blocking — *"Heads up: section 3 now says X but section 6 says Y — want to reconcile?"*

**The sufficiency moment.** When the sufficiency judge passes (every section populated, no contradictions, happy path narratable end-to-end), the product says so — as an **unlocking, not a gate**, and without interrupting:

```
┌───────────────────────────────────────────────────────┐
│  ✓ Your outline is ready.                             │  ← appears in-canvas,
│  It covers everything an assessment needs.            │     non-modal, focus-toned
│                                                        │
│  What next?                                            │
│   [ Build a proof of concept ]   (if feasible)        │
│   [ Generate a flow map ]                             │
│   [ Submit to assessment → ]                          │
│                                                        │
│  Not done yet? Keep chatting — the outline keeps       │  ← keep-refining path
│  improving, and this stays available.                 │     always present
└───────────────────────────────────────────────────────┘
```

- It presents **both paths honestly**: proceed early (optional stages or straight to submission) **and** keep refining. "Keep refining" is never removed — the conversation is unbounded (§ project brief §4), and the sufficiency banner reappears/stays available rather than pressuring.
- It is **not a modal**. It resolves into the canvas so the user stays in flow. Nothing about it implies the outline is "approved" — only that it is *ready to assess* (§ principle 5).

### 6.3 The proof of concept and its limitations banner

When the feasibility gate says a static single-file HTML PoC would genuinely help, the user can generate one. The design requirement here is specific: **every PoC carries an explicit statement of what it does NOT do, as a first-class element inside the artefact itself** — not chrome the app wraps around it.

- The banner is authored **into `poc.html`** so it travels with the file wherever it goes (downloaded, committed to the public repo, embedded in the report). It cannot be separated from the thing it qualifies.
- It sits at the **top of the PoC, visually distinct** (a bounded `amber`-marked panel, clearly not part of the mocked interface), and it **enumerates the real bounds up front**: no real data, no real integrations, simulated logic, illustrative only. Concrete, not generic — the specific things *this* PoC fakes.
- Wording is plain and non-defensive: *"This is a visual mock-up to show the idea. It uses made-up data, isn't connected to anything, and the logic is simulated. It's here to picture the solution, not to work."*
- The banner is part of the PoC's own accessibility: it is real text at the top of the document, first in reading order, announced before the mock UI.

### 6.4 The flow map

Generated from the outline (and PoC if present): actors, systems, data stores, flows — authored as Mermaid, rendered to SVG. It uses the **node/flow grammar** (§3.5) directly, so it looks like a quieter, static cousin of the pipeline animation the user will soon watch. This is deliberate: the flow map is where the user first learns the grammar they will read in the Chamber. A user who built a PoC can still request the map; the two coexist, both shown as produced artefacts on the submission screen.

### 6.5 The submission gate

The user explicitly submits to governance. The outline is required; PoC and flow map are encouraged but optional, and the screen **encourages them honestly** rather than nagging:

- Shows the three artefacts as cards with clear present/absent state.
- Honest encouragement on the optional ones: *"The assessment is richer with a flow map — the specialists can see how data moves. Add one? (~2 min) or submit without it."* — a true statement of benefit and a real skip, not a dark pattern.
- The submit action is unambiguous and single: **Submit to assessment**. The next screen is the Chamber.

---

## 7. Governance phase

### 7.1 Entering the chamber

The transition from Console to Chamber is one of the two orchestrated motion moments (§3.6). On submit, the light Console **deepens into the dark Chamber** over ~600ms (reduced-motion → a clean cut), the full pipeline map resolves in `pending` state, and the run-code chip settles into its persistent position (§7.5). The user has shifted from *building* to *watching the machinery run*. A one-line orientation appears: *"Your idea is going through the tunnel. Here's every stage — watch it work."*

### 7.2 The transparency animation — the flagship

This is the signature element (§2). It is where the design spends its boldness, and it carries the project's central promise: a non-expert should finish a run *confident every element was comprehensively considered*. It is a trust instrument, not decoration, and it is explicitly "a much more interesting and useful loading screen" for runs that take tens of minutes.

It is **pre-scripted against the known pipeline topology** and driven by a small polled event vocabulary from `status.json` (polled every few seconds; near-real-time, no true streaming). The animation already knows the whole map; events light it up.

#### 7.2.1 What is on screen — graph plus log

Two coupled panels on the Chamber surface:

```
┌──────────────────────────────────────────────┬─────────────────────┐
│  THE PIPELINE  (node/flow grammar, §3.5)      │  ACTIVITY           │
│                                                │                     │
│   [Threshold]                                  │  14:02  Privacy     │
│     ├─ Generalist A ●pulse                     │   reading OAIC PIA  │
│     ├─ Generalist B ●pulse                     │   guidance, p.14    │
│     └─ Reconciler ○                            │  14:02  IT Security │
│          → Rating engine ○                     │   drafting §7.3     │
│   [Full assessment]                            │  14:01  Ethics      │
│     ├─ 6 specialists (fan) ○ ○ ○ ○ ○ ○         │   reading AI Ethics │
│     ├─ Question checkpoint ○                   │   Principles, p.6   │
│     ├─ Architect ○                             │  …                  │
│     ├─ Reviewer (loop ×2) ○                    │                     │
│     └─ Assembly ○                              │  still working —    │
│                                                │  last update 3s ago │
│  run WT-7K3D-Q2  [copy]     ~5–10 min this stage                     │
└──────────────────────────────────────────────┴─────────────────────┘
```

- **The graph** is the spectacle: the machinery, lit as it works. It carries the emotional weight.
- **The activity log** is the substance and the fallback: a scrolling, timestamped, plain-language feed of the same events. It is screen-reader-friendly (a live region), projector-legible, and it is what makes the whole thing accessible and demo-robust. If motion is reduced or the projector washes out the glow, the log alone still tells the complete story. **The log is not optional; it is the accessibility and honesty backbone of the flagship.**

Both are driven by the same `status.json`. Design rule: **no event may exist only in the graph.** Everything the graph shows, the log states in words.

#### 7.2.2 Happy-path storyboard

Beat by beat, mapped to the real topology (§ project brief §5):

1. **Ready.** Full map in `pending`. *"Ready to run."*
2. **Threshold — parallel drafting.** Generalist A and Generalist B go `active` **at the same time** (two nodes pulsing) — the user sees two independent assessors working in parallel. Log: *"Two assessors are independently drafting your threshold assessment."* Retrievals surface as ephemeral labels on each node and lines in the log.
3. **Reconciler.** The two generalists settle; the reconciler goes active, drawing the two drafts together. Log names what it does: *"Comparing the two assessments and resolving any differences (taking the higher rating where they disagree)."* This previews the divergence the user will see in §7.4 — the honesty starts here.
4. **Rating engine.** A distinct, briefly-active node computes the ratings deterministically. Log: *"Calculating risk ratings from the assessment matrix."* Showing this as its *own* node quietly communicates the "models argue, code computes" integrity move — the ratings aren't a model's opinion.
5. **Threshold complete → user review.** The pipeline pauses for the threshold review screen (§7.4). This is a designed hand-off to the Console, not a dead stop.
6. **Full assessment — the specialist college (the peak).** If routed to full, **six specialist nodes bloom active in a fan, all at once.** This is the emotional high point — a college of experts simultaneously scrutinising the idea, each reading its own sources. Retrievals pour into the log with real citations (*"Privacy — reading OAIC PIA guidance, p.14"*). This single moment does more for trust than any copy could: the user *sees* the breadth of expertise brought to bear.
7. **Question checkpoint** (if any). The pipeline visibly holds; hand-off to the checkpoint UI (§7.3). If zero questions (the happy path), the run flows straight through and the log notes *"The specialists had everything they needed — no questions."*
8. **Specialist revision.** After answers, specialists briefly re-activate to revise their own sections once.
9. **Architect.** A single node reads the whole draft and writes the implementation appendix. Log ties it back: *"Writing an implementation plan that answers the risks the specialists raised."*
10. **Reviewer loop.** The reviewer node runs, checking coverage and coherence. If it directs a revision, the edge back to a specialist animates and the loop counter shows *"review pass 1 of up to 2"* — **framed as diligence, not error** (§7.2.5). Unresolved-after-two is recorded honestly, previewing the report's disagreement block.
11. **Assembly.** The notebook and HTML are built. Log: *"Assembling your report."*
12. **Done.** The pipeline settles whole; the second orchestrated moment — the **report arrives** and the surface returns toward the light. *"Your draft assessment is ready."* → the report (§8).

#### 7.2.3 The pause state (specialists have questions)

The run is *expectant*, not stopped:

- The checkpoint node goes **`waiting-on-you`** (amber); nodes downstream shown as *paused, will resume*; upstream stays `complete`. The machinery visibly holds its place.
- A clear call to action surfaces: *"3 specialists have questions before they continue."* → opens the checkpoint UI (§7.3).
- The **run-code chip becomes prominent** here (§7.5) — the user may leave and return, and the design says so: *"You can close this and come back later with your run code."*
- Tone is anticipation, not alarm. Amber, not red. Nothing is wrong; the experts want input.

#### 7.2.4 The failure state

Runs are dozens of LLM calls over tens of minutes; failures happen. The state is **calm and actionable** (§ principle 2):

- The failed node goes **`failed`** (muted clay, never blaring red). Completed work stays visibly `complete` — the user sees that progress was saved, not lost.
- Plain explanation, in the interface's voice: *"The run stopped at the specialist stage. Your progress up to here is saved."*
- **The run code is surfaced prominently with resume instructions:** *"Paste your run code — `WT-7K3D-Q2` — to pick up from the last saved point."* (§7.5). Copy affordance right there.
- **The run code / technical detail is presented calmly.** The actual run/error code is available but not thrown at the user — a *"Show technical detail"* disclosure reveals the underlying error for Tom or a curious user, collapsed by default. The default view is reassurance + the one action that matters.
- A paused run and a failed run **resume identically** (§ project brief §7), so the resume affordance is the same element in both states — one thing to learn.

#### 7.2.5 Long-wait states and honest waiting

The screen's whole reason to exist is making tens of minutes tolerable and trustworthy. It must never look frozen and never lie:

- **Ambient airflow** (§3.6) runs continuously along active edges — the screen is always visibly *alive*.
- **Honest, ranged expectations**, never fake precise countdowns: *"This stage usually takes 5–10 minutes."* Ranges, drawn from the tech spec's per-stage budgets.
- **Genuine sub-activity.** The active node shows *what it is actually doing right now* — which document it is reading — sourced from real retrieval events, not invented filler. This is the difference between a trust instrument and a decorative spinner.
- **Honest staleness.** If polling returns no change for a while, the log shows *"still working — last update 12s ago"* rather than pretending. Silence is disclosed, not hidden.
- **Leave-and-return, stated plainly.** For long runs: *"This can take a while. You can safely close the tab and come back with your run code."* The run code makes walking away safe, and the design tells the user that.
- A quiet **"what's happening now / what's next"** explainer helps the non-expert read the machinery: one plain sentence on the current stage's purpose. This is what converts *watching a loading screen* into *understanding that my idea is being thoroughly assessed*.

#### 7.2.6 What the animation needs from `status.json`

**For the tech spec.** Design defines the *information the animation must be able to render*; the tech-spec instance defines exact field names, types and cadence. The animation is pre-scripted to the topology, so a single poll must be enough to set the entire graph state and append new log lines. The needs:

- **Run identity & overall state** — enough to show the run-code chip and pick happy/pause/failure/complete framing: `run_id`, `run_code`, `phase` (`threshold` | `full`), `overall_state` (`running` | `paused` | `failed` | `complete`), `updated_at`.
- **Whole-graph node states** — a map of `node_id → state` over the known topology, where state ∈ `pending` | `active` | `waiting_user` | `complete` | `failed`. This lets one payload set the entire graph, including several nodes `active` at once (the two generalists; the six-specialist bloom). Node ids are fixed and shared with the tech spec, e.g. `threshold.generalist_a`, `threshold.generalist_b`, `threshold.reconciler`, `threshold.rating_engine`, `full.specialist.privacy` (…×6), `full.checkpoint`, `full.architect`, `full.reviewer`, `full.assembly`.
- **An append-only event log** — the substance feed. Each event needs: `ts`, `agent` (a node id or its friendly name), `type` from a **small controlled vocabulary**, a plain-text `detail`, and an optional structured `ref`. Proposed `type` set — this is the vocabulary the animation is built to understand, and the coordination point with the tech spec:

  | `type` | Renders as | `detail` / `ref` example |
  | --- | --- | --- |
  | `stage_started` | node → active, log line | "Threshold assessment started" |
  | `retrieval` | ephemeral label on node + log line | detail: "reading OAIC PIA guidance"; ref: `{doc, page}` |
  | `drafting` | node sub-activity | "drafting §7.3" |
  | `question_raised` | feeds the pause count | ref: `{specialist, question_id}` |
  | `revision` | edge re-animates, loop counter | "review pass 1 of 2" |
  | `review_finding` | log line | "Checking coherence across sections" |
  | `stage_complete` | node → settle/complete | "Threshold assessment complete" |
  | `heartbeat` | drives "still working — last update Ns ago" | (empty) — liveness ping |
  | `error` | node → failed, failure state | detail: plain message; technical detail carried separately |

- **Batched questions, when paused** — for the checkpoint UI (§7.3): a list grouped by specialist, each question with an id, the asking specialist, a one-line *why*, and (optionally) MC options with a free-text escape.
- **Failure payload, when failed** — `stage` (a node id), a plain-language `message`, the `run_code`, and an optional `technical` string surfaced only behind "Show technical detail."
- **Per-stage expected duration hints** — optional `expected_range` per stage so the wait copy ("usually 5–10 min") is honest and data-driven, not hard-coded in the frontend.

The controlling design constraints the tech spec should honour: **one poll fully determines the visible state** (no reliance on having seen prior polls to render correctly — the frontend may miss polls); the **event log is append-only with stable ids** (so the frontend can dedupe and only animate genuinely new events); and a **`heartbeat` exists** so honest-staleness messaging has something to count from.

### 7.3 The question checkpoint UI

Up to three questions per specialist, all specialists batched into **one** pause. The design goals: make the *attribution* visible (which specialist, and why they're asking — this is the machinery reasoning in the open), and make *skipping* an honest, consequence-clear choice.

```
┌───────────────────────────────────────────────────────┐
│  The specialists have a few questions        run …-Q2 │
│  Answer what you can. Skipping is fine — it just       │
│  becomes a noted gap in your assessment.               │
│  ─────────────────────────────────────────────────    │
│  PRIVACY SPECIALIST                                    │  ← attribution, Archivo
│  Asking so the privacy risk rests on fact, not         │  ← the "why", plain
│  assumption.                                           │
│                                                        │
│   Q. Does the solution store personal information,     │
│      and if so, where?                                 │
│      ( ) It doesn't  ( ) On-prem  ( ) Cloud  ( ) …     │  ← MC + free-text escape
│      [ free text …                                  ]  │
│      [ Skip this — note it as a gap ]                 │
│  ─────────────────────────────────────────────────    │
│  IT SECURITY SPECIALIST                                │
│  …                                                     │
│  ─────────────────────────────────────────────────    │
│  2 of 5 answered · 1 skipped        [ Resume the run ]│
└───────────────────────────────────────────────────────┘
```

- **Grouped by specialist**, with attribution and a **one-line *why*** for each. Seeing *why* a domain expert needs to know something is a strong trust moment — the user watches the reasoning, not just the request.
- **Answer input mirrors the interview**: Claude-style multiple choice with a free-text escape, so the checkpoint feels continuous with the brainstorm the user already learned.
- **Skip is explicit and honest**: *"Skip this — note it as a gap."* The consequence is stated at the point of choice, not buried. Skipped questions convert to **flagged gaps** that appear in the report's next-steps register (§8), so the user's choice has a visible, honest downstream.
- **A running tally** (*"2 of 5 answered · 1 skipped"*) and a single **Resume the run** action. On resume, the pipeline (§7.2) picks up and each specialist revises its own sections once.
- **Accessibility:** the whole checkpoint is a standard keyboard-navigable form; each specialist group is a labelled region; skip and answer are equally reachable; nothing depends on the amber pause colour to be understood.

### 7.4 The threshold review screen

The completed threshold assessment (DTA sections 1–4), presented on the Console for the user to review and comment, before routing. The design job is to make the **risk reasoning legible** and the **assessor divergence visible rather than buried** — divergence is signal, and showing it is the honesty the whole product trades on.

- **The eight inherent-risk categories (3.1–3.8)**, each as a row: the category, the chosen **consequence** and **likelihood** (with the specialist's written rationale expandable), and the **computed risk chip** (§3.2). The chip is visibly *computed* — a small note *"rating calculated from consequence × likelihood"* reinforces "code computes," so the user trusts the number isn't an opinion.
- **The overall 3.9 rating**, shown as computed **highest-wins**, with the driving category named: *"Overall: High — driven by 3.5 Privacy."*
- **Assessor divergence, surfaced not hidden.** Where the two independent generalists disagreed, a clearly-marked **divergence note** shows both positions and the reconciler's resolution and reason: *"Assessor A rated consequence Moderate; Assessor B rated Major. Resolved to Major — the tool's guidance resolves disagreement to the higher rating."* Framed as *rigour*: two independent experts, honestly reconciled. This is a feature to show off, not a wart to hide.
- **The routing outcome**, following the tool's own logic, stated plainly with the path made obvious:
  - all-low → *"You can conclude here. This threshold assessment is ready for an approving officer to consider."* (never "approved" — ready to be *considered*.)
  - any medium/high → *"A full assessment is required."*
  - and always → *"You can choose a full assessment anyway."*
- **Markdown download** of the threshold artefact, carrying the standing disclaimer header.
- **The two-revision-cycle affordance**, with the count visible and honest: *"You can ask for up to 2 rounds of revisions. (0 used.)"* — so the cap is known up front, not discovered by hitting it.

### 7.5 Run codes — the ticket back in

A short, human-copyable code (e.g. `WT-7K3D-Q2`) is the user's ticket back into a paused or failed run.

- **Format.** `WT-` prefix + two short groups, mono (IBM Plex Mono). **For the tech spec / Tom:** draw the code from an unambiguous character set — exclude easily-confused glyphs (`0/O`, `1/I/L`, `U/V`) so the code survives being read aloud across a demo room or retyped from a notepad. Groups separated by hyphens for chunked legibility.
- **Persistent placement.** From the moment a run is created, the **run-code chip** sits in a fixed, quiet position (Chamber: bottom-left of the pipeline; Console review screens: header). Always present during a run, one-tap **copy** with a *"copied"* confirmation.
- **It is a locator, not a secret — said honestly.** Because the whole repo is world-readable (§4), the run code isn't a password; it points to a run anyone could already find. The copy tooltip is honest about this rather than implying secrecy: *"Your ticket back to this run. (Everything here is public, remember.)"*
- **Prominence on pause/failure.** In the `waiting-on-you` and `failed` states (§7.2.3–7.2.4) the chip grows into the primary element with explicit instructions.
- **The resume-entry flow.** From the landing screen, *Resume a run* → a single mono input (*"Paste your run code"*) → the app fetches the run's state and **drops the user back at the exact checkpoint**: mid-pipeline runs return to the Chamber at their current node state; a run paused at the threshold returns to the review screen; a run paused at the checkpoint returns to the questions. The resume input validates format locally and gives a plain error on a bad or unknown code (*"That code doesn't match a run we can find — check the characters?"*), never a raw failure.

---

## 8. The final report

The nbconvert HTML render is the thing a director actually reads. It must look like a **document taken seriously**, nodding to the DTA tool's visual language **without imitating Commonwealth branding** (no coat of arms, no gov.au masthead — the *seriousness*, not the *insignia*). This is the Report register of the type system (§3.3): IBM Plex Serif body, Plex Sans headings, Plex Mono for data and citations, generous margins, real section numbering.

The default nbconvert theme is replaced with a custom stylesheet delivering:

- **A title block, not a notebook header.** Project title, *DRAFT — for SME review* mark, run code, generation date, and the standing disclaimer (§4.2) — so the document announces what it is before its first section.
- **The DTA 12-section structure, faithfully numbered.** Sections 1–12 with the tool's own numbering (1–4 threshold, 5–12 full). Numbering here is load-bearing — it maps directly to the instrument an SME already knows — so it is prominent and exact.
- **Page-cited references as a first-class apparatus.** Every corpus-based claim carries an inline citation (mono: *[ISM, p.112]*) and the document ends with a full reference list. Where feasible, citations link to their entry. Citations are the report's credibility; they are styled to be scannable, never buried.
- **Specialist diagrams** embedded as pre-rendered SVG (the node/flow grammar, §3.5), captioned and attributed to the specialist who authored them.
- **The gap / next-steps register** — a clear, actionable section (*"Recommended next steps"*), each gap stating what couldn't be determined and the concrete step the project team should take. Skipped checkpoint questions (§7.3) land here. This reads as *a plan*, not a list of failures.
- **The unresolved-disagreement block — designed to read as rigour, not failure.** Titled *"Points of unresolved disagreement,"* it presents each unresolved conflict as two well-argued positions the system chose **not** to force into false consensus, with a plain framing line: *"For a governance assessment, honest disagreement is more credible than manufactured agreement. These points are flagged for human judgement."* Visually it is calm and confident — a bordered panel in neutral tones, not an error box. This block is a highlight of the product's integrity and should be styled to be found, not skimmed past.
- **The provenance section** — the audit trail: run id, timestamps, model per role, corpus manifest versions, agent-to-section attribution, and the input-sensitivity attestation. Set in mono, structured as a clean record. It is what lets a human *audit the audit* (§ project brief §10, "reviewer authority").
- **The standing disclaimer**, repeated in the running header/footer of every page so it survives printing: *"Draft for SME review — not an approval, not legal advice."*
- **Print-friendliness.** A director may print it. A print stylesheet gives proper page breaks (never splitting a risk table across pages), keeps the header/footer disclaimer on every page, and ensures risk chips and citations remain legible in greyscale (colour is never the only cue — §3.2).
- **The revision affordance (in-app, beside the rendered report — not part of the document).** The same honest cap pattern as the threshold screen (§7.4): *"You can ask for up to 2 rounds of revisions. (0 used.)"*, with a plain free-text box for what should change. On submission the Chamber reprises for the shorter pass — the targeted specialists, the reviewer, and assembly re-activate through the same animation grammar (tech spec §5.8) — and the regenerated report returns marked *"Revision N of 2"* in its title block, so the document is honest about its own history.

The overall feel: quiet authority. Lots of white space, exact numbering, precise citations, honest about its own gaps and disagreements. A document that earns a serious reader's trust by not overclaiming — which is the whole product in one artefact.

---

## 9. Accessibility (WCAG 2.1 AA as a floor) and the competition demo

Accessibility and demo-robustness are treated as the same work (§ principle 6). The AA floor, mapped to the surfaces where it bites hardest:

- **Colour is never the only channel.** Risk ratings carry label + shape (§3.2); node states carry label + the activity log; the pause/amber and failure/clay states are always named in text. This is what also lets the product survive a washed-out projector.
- **Contrast.** All text meets AA (4.5:1 body, 3:1 large). The `chamber` surface is checked for the log and labels specifically, since that is the reading-heavy part of the dark view. "Quiet" upcoming stages and ghosted placeholders sit *at or above* AA — quiet means low emphasis, never illegible.
- **Motion.** `prefers-reduced-motion` is honoured everywhere (§3.6); every animation has an information-preserving static equivalent, and the activity log means no one who turns motion off loses any content of the flagship animation.
- **Keyboard.** Full keyboard operability with visible focus on every interactive element: the warning gate, the canvas edit affordances, the checkpoint form, the run-code copy and resume input, and all report links.
- **Screen readers.** The animation's activity log is an ARIA live region so a screen-reader user hears the pipeline's progress in words as it happens — the log isn't a fallback bolted on, it is the animation's accessible form by design. Warning gate, checkpoint, and review screens use labelled regions and sensible reading order.
- **The demo specifically.** Everything degrades gracefully on a projector: the flagship reads from the high-contrast log even if the glow washes out; the risk chips read in poor colour because of their shape/label redundancy; type sizes are large enough to read from the back of a room. The dogfood run (Windtunnel assessing Windtunnel) is the demo centrepiece, so the report styling (§8) is what the room will be looking at — it gets the polish.

---

## 10. Coordination summary — what design has defined for the tech spec

Collected here so the tech-spec instance has one place to find the design-side contract:

- **The `status.json` needs and the event vocabulary** (§7.2.6): whole-graph node-state map over a fixed topology, an append-only event log with stable ids and a small controlled `type` set (`stage_started`, `retrieval`, `drafting`, `question_raised`, `revision`, `review_finding`, `stage_complete`, `heartbeat`, `error`), batched-questions payload, failure payload with a separated `technical` field, and optional per-stage `expected_range` hints. Controlling constraints: **one poll fully determines visible state**, the log is **append-only with stable ids**, and a **`heartbeat`** exists for honest-staleness messaging.
- **Fixed node ids** shared between animation and pipeline (§7.2.6) so the pre-scripted graph and the emitted events line up.
- **Run-code format** (§7.5): `WT-`-prefixed, hyphen-chunked, drawn from an unambiguous character set (no `0/O`, `1/I/L`, `U/V`).
- **Artefact-embedded elements** the pipeline must author *into* files, not around them: the PoC limitations banner inside `poc.html` (§6.3), and the standing disclaimer inside every downloadable artefact header (§4.2, §8).

## 11. Open items for Tom

- **The name** (§1). Recommendation is to keep *Windtunnel*; a shortlist is offered. One-token change downstream.
- **Font substitutions** (§3.3). The recommended system (Archivo + IBM Plex Sans/Serif/Mono) is free and Pages-friendly; the design depends on the *roles*, so swaps are fine.
- **Exact risk-rating labels** (§3.2, §7.4). The chip scale accommodates whatever the DTA tool's Table 2 actually names its levels; confirm the tool's wording and the design inherits it.
- **Competition demo format** (§ project brief §10). If the demo is a projected walkthrough vs a hands-on booth, that back-propagates into which surfaces get the final polish pass — the flagship animation and the dogfood report are the safe bets either way.
