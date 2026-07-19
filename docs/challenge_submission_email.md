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

**Purpose.** Windtunnel takes a public servant's loose idea for an AI solution and carries it
through two phases: a co-design **Brainstorm** conversation that sharpens it into a structured
concept (with an optional clickable mock-up and information-flow map), then a multi-agent
**Governance** phase that stress-tests the concept against the Australian Government's *AI
impact assessment tool* (DTA, v1.0) and produces a substantially complete, fully-cited **draft
impact assessment** — as a notebook and an HTML report.

**Intended users.** Any public servant with an AI idea who will eventually need to clear the
mandatory AI impact assessment gate (in force from 15 December 2026) — used early, before formal
SME and assessing-officer engagement, to arrive at that engagement with a credible starting draft
rather than a blank page.

**Information used.** Only what the user volunteers about their own idea, via a guided
conversation — no production data, no external lookups. Every risk judgement is grounded in the
Australian Government's AI impact assessment tool and guidance, plus roughly 110 curated,
publicly redistributable government and standards documents, split across six specialist
libraries and cited pinpoint-precise on every claim.

**Limitations.** The output is a draft for SME and assessing-officer review — never an approval.
It is not legal advice and does not replace the assessing, approving, or accountable roles the AI
policy defines. It is a demonstration system with no login and no security accreditation, and its
knowledge is bounded by its curated document library, not the entirety of Commonwealth policy.

**Risks (and how the build addresses them).** Public repository/public data, disclosed plainly
before any input is accepted; a model quietly setting its own risk rating, designed out
structurally (models argue consequence and likelihood, fixed code computes the rating); prompt
injection via submitted idea text, addressed by treating all user text as untrusted information,
never instructions; unsupported claims, addressed by a hard citation requirement or an honest
gap; an agent overstepping its brief, addressed by structural per-specialist write-scope.

**Tools used.** Google Gemini (Flash-Lite / Flash / Pro tiers) for the reasoning agents; Python
(FastAPI + GitHub Actions) for the backend and governance pipeline; a deterministic, LLM-free
Python rating engine; React/TypeScript on GitHub Pages for the interface; SQLite/FTS5 knowledge
bases; Jupyter (`nbformat`/`nbconvert`) for the notebook and report; the GitHub repository itself
as the durable store and audit trail. Built with **Claude Code** as the engineering tool
throughout.

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
