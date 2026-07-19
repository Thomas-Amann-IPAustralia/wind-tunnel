# Draft submission email — Build a Bureaucrat Bot 2026

> **Before sending, check/fill in the bracketed placeholders below** — I pulled your name and
> agency from the repository owner (`Thomas-Amann-IPAustralia`) as a best guess, but couldn't find
> your position/title anywhere in the repo, and don't know the submission address, deadline, or
> whether a live demo link should be included. Everything else is drawn from the actual build.

---

**To:** [Build a Bureaucrat Bot submission address]
**Subject:** Build a Bureaucrat Bot 2026 entry — Windtunnel

Hi [Build a Bureaucrat Bot team],

I'd like to enter **Windtunnel** in this year's Build a Bureaucrat Bot challenge, in the **Chief
AI Officer's Aide** and **AI Trailblazer** categories.

**Entrant:** Tom Amann [confirm name/spelling], [your position/title], IP Australia [confirm agency]

**The bot:** Windtunnel — *test the design under load before you build the aircraft.*

### Intent, and how it fits the theme

This year's theme — *Ready or not…* — is what drove the build. Windtunnel is genuinely useful on
its own terms: it takes a public servant's loose idea for an AI solution through a co-design
conversation and a multi-agent governance assessment, and hands back a substantially complete,
fully-cited draft AI impact assessment — built directly on the DTA's own instrument — in hours
instead of weeks.

But its real purpose is a provocation. The friction that used to sit between "I have an idea" and
"I have a working thing" was technical know-how, and that friction is disappearing fast.
Windtunnel is built to show the same is now becoming true on the governance side: a well-argued,
properly-cited first draft against a twelve-section impact assessment tool, produced in an
afternoon, by someone who isn't a specialist in privacy law, security, or administrative law. If
both of those bottlenecks — *build it* and *govern it* — are dissolving at once, the interesting
question isn't "can AI do this." It's: **where does the friction move to next?** What does the
rest of an agency's bureaucracy look like once neither "we don't have the technical skill" nor
"governance takes too long" is a valid reason to sit on an idea? Windtunnel doesn't answer that
question — it's built so you can put your own idea through it and watch the question become
concrete.

### Why it fits these two categories

- **The Chief AI Officer's Aide.** Windtunnel's output is exactly the artefact a CAIO or
  governance body needs to turn ambition into accountable action: a structured draft against the
  government's own instrument, every risk rating computed deterministically rather than asserted
  by a model, every claim pinned to a citable source. It turns "how risky is this, and where do
  we start" from a multi-week SME engagement into a same-day starting draft — supporting risk
  framing, prioritisation across a portfolio of ideas, and executive-ready briefings.
- **The AI Trailblazer.** It's built for the person with the idea, not the specialist. The
  Brainstorm phase turns a loose thought into a structured concept, an optional clickable
  mock-up, and a flow map through plain conversation. The Governance phase then works through the
  real risks against the real instrument, asks only what it genuinely can't infer, and ends in an
  implementation plan traceable to every mitigation raised — curiosity to a credible first draft,
  on the user's own steam.

### Bot card

**Purpose.** Windtunnel helps public servants explore AI ideas responsibly from day one. Through
a guided co-design conversation followed by a multi-agent governance assessment, it transforms an
early concept into a substantially complete, fully cited draft AI Impact Assessment aligned to
the Australian Government's AI Impact Assessment Tool (v1.0). A complete, plain-language
walkthrough is available in
[`SYSTEM_OVERVIEW.ipynb`](https://github.com/Thomas-Amann-IPAustralia/wind-tunnel/blob/main/SYSTEM_OVERVIEW.ipynb).

**Intended users.** Public servants who are exploring AI-enabled services and want to understand
governance implications before engaging formal subject matter experts or assessment panels.

**Information used.** Information voluntarily provided by the user about their proposed AI
system; a curated library of roughly 110 publicly available government policies, standards and
guidance documents; the Australian Government AI Impact Assessment Tool and supporting guidance.

**Limitations.** Produces a draft assessment only. Does not provide legal advice or replace
official governance, approval or assurance processes. Knowledge is limited to its curated
document library and does not represent all Commonwealth policy.

**Key risks.** Everything submitted or generated is stored in a public, world-readable GitHub
repository, and the system carries no security accreditation — disclosed prominently before any
input is accepted. Users may over-rely on AI-generated outputs. AI models may produce unsupported
conclusions. User-provided content could contain prompt injection attempts. These are mitigated
through the up-front public-storage disclosure, deterministic risk calculations (models never
assign a rating), mandatory evidence-based citations, specialist agent boundaries, and treating
all user input as untrusted data.

**Tools used.** Google Gemini (Flash-Lite, Flash and Pro) for the reasoning agents; Claude Code
as the engineering tool throughout; Python, FastAPI (hosted on Render) and GitHub Actions for the
backend and governance pipeline; React and TypeScript, served via GitHub Pages, for the
interface; Mermaid.js for client-side flow-map rendering; SQLite (FTS5) for the specialist
knowledge bases; Jupyter (`nbformat`/`nbconvert`) for the notebook and report; the GitHub
repository itself as the durable store and audit trail; and ChatGPT plus Adobe Photoshop for the
loading-animation sprite sheet (AI-generated, then manually corrected).

*(The bot card also stands alone at `docs/bot_card.md` in the repository, should you want to
lift it out separately.)*

### Acknowledgement

I confirm Windtunnel is my own work, built for this challenge as part of Innovation Month 2026.
It was engineered end-to-end with Claude Code (Anthropic) as the coding tool, under my direction
and design decisions throughout — which felt like the right way to build this particular entry,
given the theme.

**Repository** (code, prompts, and every run's committed artefacts — the whole system is public
by design): <https://github.com/Thomas-Amann-IPAustralia/wind-tunnel>
**System walkthrough:** <https://github.com/Thomas-Amann-IPAustralia/wind-tunnel/blob/main/SYSTEM_OVERVIEW.ipynb>
**Live demo:** [https://thomas-amann-ipaustralia.github.io/wind-tunnel/ — confirm the Render
backend is currently deployed/awake before sharing this link; see `STATUS.md` for known
deployment caveats]

Happy to walk through a live run if that's useful.

Thanks,
Tom Amann [confirm]
[your position/title]
IP Australia [confirm]
[contact email / phone, if the form requires it]
