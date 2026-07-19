# Bot card — Windtunnel

*Test the design under load before you build the aircraft.*

An **Innovation Month 2026 ("Ready or not…") entry** for the Build a Bureaucrat Bot challenge —
categories: **The Chief AI Officer's Aide** and **The AI Trailblazer**.

**Full walkthrough:** [`SYSTEM_OVERVIEW.ipynb`](https://github.com/Thomas-Amann-IPAustralia/wind-tunnel/blob/main/SYSTEM_OVERVIEW.ipynb) —
a complete, plain-language, illustrated tour of the whole system (real screenshots, one worked
example, start to finish).
**Repository:** <https://github.com/Thomas-Amann-IPAustralia/wind-tunnel>

---

## Purpose

Windtunnel takes a public servant's loose idea for an AI solution and carries it through two
phases: a co-design **Brainstorm** conversation that sharpens it into a structured concept (with
an optional clickable mock-up and information-flow map), then a multi-agent **Governance** phase
that stress-tests the concept against the Australian Government's *AI impact assessment tool*
(DTA, v1.0) and produces a substantially complete, fully-cited **draft impact assessment** — as a
notebook and an HTML report. It compresses the distance between *"I have an idea"* and *"here is a
well-argued draft my SMEs can review"* from weeks to hours.

## Intended users

Any public servant with an AI idea who will eventually need to clear the mandatory AI impact
assessment gate under the *Policy for the responsible use of AI in government* (in force from
15 December 2026). It's meant to be used early — before formal SME and assessing-officer
engagement — so that engagement starts from a credible draft instead of a blank page.

## Information used

Only what the user volunteers about their own idea, via a guided conversation — no production
data, no external lookups, no accounts. Every risk judgement is grounded in the Australian
Government's AI impact assessment tool and guidance, plus roughly 110 curated, publicly
redistributable government and standards documents (the ISM, OWASP guidance, the *Privacy Act*
and the APPs, Australia's AI Ethics Principles, anti-discrimination legislation, the *Archives
Act*, the DTA technical standard, NIST's AI RMF, and similar), split across six specialist
libraries and cited pinpoint-precise on every substantive claim.

## Limitations

The output is a **draft for SME and assessing-officer review — never an approval.** It is not
legal advice, and it does not replace the assessing, approving, or accountable roles the AI
policy defines. It is a demonstration system: no login, no security accreditation, and a full
run takes several minutes. Its knowledge is bounded by its curated ~110-document library, not the
entirety of Commonwealth policy — where a specialist's material genuinely doesn't cover
something, it records that as a gap rather than guessing.

## Risks, and how the build addresses them

- **Public repository, public data.** The whole system — code and every run — lives in one
  public GitHub repository by design. This is disclosed plainly, before any input is accepted:
  don't enter classified, sensitive, or personal information.
- **A model quietly setting its own risk rating.** Designed out structurally: agents only ever
  argue a *consequence* and a *likelihood*, each with a rationale. A fixed piece of code computes
  every rating from the instrument's own risk matrix — no model ever asserts one, on first pass
  or on revision.
- **Prompt injection via submitted idea text.** Every agent treats user-supplied text as
  untrusted information describing the idea, never as instructions to follow.
- **Unsupported or fabricated claims.** Specialists must cite a real, checkable source locator
  (page, provision, or heading) for every substantive claim, or record an honest gap instead of
  guessing.
- **An agent overstepping its brief.** Each specialist can write only its own owned sections of
  the assessment — enforced structurally, not by convention or prompt alone.

## Tools used

Google Gemini (three tiers — Flash-Lite, Flash and Pro — matched to task difficulty) for the
reasoning agents; Python (FastAPI + GitHub Actions) for the backend and governance pipeline; a
deterministic, LLM-free Python rating engine; React/TypeScript on GitHub Pages for the interface;
SQLite/FTS5 knowledge bases per specialist; Jupyter (`nbformat`/`nbconvert`) for the notebook and
report; the GitHub repository itself as the durable store and public audit trail. Built with
**Claude Code** as the engineering tool throughout, under the entrant's direction and design
decisions.
