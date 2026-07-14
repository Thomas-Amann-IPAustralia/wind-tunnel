# Project Brief — Windtunnel (working title)

**Version:** 1.0 · **Date:** 11 July 2026 · **Author:** Drafted with Claude from Tom's concept description, the DTA *AI impact assessment tool* v1.0 (01/12/2025) and its supporting *Guidance*.

**Purpose of this document:** This brief is the source of truth for two downstream documents — a technical specification and a design brief — each produced by a separate Claude instance, with development carried out primarily in Claude Code. Where a decision has been made, it is recorded as made. Where a decision is deliberately deferred to the tech spec or design brief, it is flagged as such. Companion files: `TECH_SPEC.md` and `DESIGN_BRIEF.md` (both complete).

---

## 1. What this is

Windtunnel takes a public servant's loose idea for an AI solution and carries it through two phases. The **Brainstorm phase** is an interactive co-design session that sharpens the idea into a structured project outline, optionally accompanied by an HTML proof-of-concept and an information-flow map — "a lens coming into focus." The **Governance phase** then subjects those artefacts to a rigorous, multi-agent assessment built directly on the Australian Government's *AI impact assessment tool* (DTA, v1.0), producing a substantially complete draft impact assessment as a Jupyter notebook (source of record) and a rendered HTML report (the thing you actually hand to subject matter experts).

The name is a placeholder Tom can replace; the metaphor — test the design under load before you build the aircraft — is the point. The Governance phase is the heart of the project and where quality effort should concentrate: the arguments made by the specialist agents must be thoughtful, evidenced, pinpoint-cited to their sources (page, provision or row level), and able to withstand scrutiny from real human experts.

**Context:** Built as an entry in a competition for Australian public servants. It is a demonstration system, but it must behave like a serious one. No real login-gated user base is expected in v1.

### Non-goals (state these in the product itself)

The system's output is a **draft for SME and assessing-officer review — never an approval**. It does not constitute legal advice, does not authorise any AI use case, and does not replace the assessing officer, approving officer, or accountable use case owner roles defined in the AI policy. The tool's own disclaimer language (per the DTA documents) should be echoed in the final artefacts. The finished system should also, as its first dogfood run, be put through its own Governance phase — this is both a genuine test and an excellent competition narrative.

---

## 2. Problem statement

The updated *Policy for the responsible use of AI in government* (December 2025) makes an AI impact assessment mandatory for in-scope use cases, with agencies required to implement the requirement by 15 December 2026. The assessment instrument is a 12-section document demanding structured risk reasoning, stakeholder mapping, and engagement with a wide body of frameworks (AI Ethics Principles, APPs, PSPF, ISM, Framework for Governance of Indigenous Data, administrative law principles, and more). Most public servants with a good AI idea have neither the time nor the cross-domain expertise to produce a credible first draft, so ideas either stall at the governance gate or proceed with thin assessments. Windtunnel compresses the distance between "I have an idea" and "here is a well-argued draft assessment my SMEs can review" from weeks to hours.

---

## 3. Users, access and data handling

Access is a public URL with no authentication in v1 — obscurity plus a usage warning is the agreed posture. The warning must be prominent, worded plainly, and shown before any input is accepted: the sensitivity ceiling is **OFFICIAL**; users must not enter OFFICIAL: Sensitive information, security classified information, or personally identifiable information; and everything submitted or generated is stored in a public GitHub repository and is world-readable. The Governance phase output should note in the notebook's provenance cell that inputs were user-attested as at-or-below OFFICIAL.

### Repository and data layout (decision)

One **public** repository on Tom's free GitHub account holds everything: code, workflows, prompts, corpus documents, built specialist knowledge bases, and all run state and artefacts (`runs/<run-id>/…`). Public visibility supports the competition, gives unlimited free GitHub Actions minutes on standard runners, and turns the run commits into a public audit trail.

Two consequences follow and are accepted by design. First, everything a user submits — project descriptions, interview transcripts, generated assessments — is world-readable; the usage warning must disclose this plainly alongside the sensitivity ceiling. Second, every corpus document is effectively republished in chunked form inside the knowledge bases, so the corpus is limited to genuinely redistributable material (Commonwealth CC-BY publications, OWASP and similar); the ingestion pipeline's licence check is a **hard gate that refuses anything else**, not a router.

### Security posture notes for the tech spec

Gemini API key lives in Render environment variables and GitHub Actions secrets (Tom has pre-paid Gemini tokens and will add the key). The Governance pipeline commits with the built-in Actions token; the Render backend commits brainstorm state via a fine-grained PAT scoped to the repo. User-supplied text flows into many prompts, so baseline prompt-injection hygiene applies: user content delimited and labelled as untrusted in every prompt, agents instructed never to treat user text as instructions, and retrieval corpora are curated/trusted by construction.

---

## 4. Phase 1 — Brainstorm

### Purpose

Turn a simple idea into a concept with clarity: the problem, the solution, the solution's happy path, UX/UI requirements, and the user's constraints and preferences. The system extracts implicit and explicit information from the interaction and feeds it into a living project outline document. Each of the three stages runs as a separate LLM instance that knows which stage it is in; the intent of each stage is clearly telegraphed to the user, and the user should visibly see their decisions shaping the artefacts.

### Stage 1 — Scoping interview (mandatory)

The user provides a loose concept and any hard constraints (e.g., "a tool to sort my SharePoint files; Microsoft products only; easy to maintain"). An interviewer agent then works the idea over using structured questioning — Claude-style multiple-choice options with free-text escape hatches — covering, at minimum: the problem being solved (independent of the solution, mirroring tool section 2.1), the intended users and affected stakeholders, data touched by the solution (type, source, sensitivity), the happy path as a narrated sequence, non-AI alternatives considered, constraints (technical, organisational, maintenance), and success criteria.

While the interview runs, the **project outline updates live in a canvas-style panel** beside the conversation. The user watches the document assemble; edits and suggestions from the user flow into it at any time. When a sufficiency judge (an LLM check against a rubric derived from the outline template — every section populated, no internal contradictions, happy path narratable end-to-end) deems the outline adequate, the user is told so and offered the optional stages. The user may override in either direction: proceed early, or keep refining.

The interview conversation itself is unbounded. The two-cycle regeneration cap (see §7) applies only to artefacts after their initial generation.

### Stage 2 — Proof of concept (optional, conditional)

Before offering a PoC, a feasibility gate (LLM judgement) asks: would a static, single-file HTML PoC meaningfully visualise this solution? Interfaces, dashboards, and form-driven tools: yes. Headless pipelines, integrations, and pure back-office automations: no — in which case the system produces the **information-flow map instead** and says why. Where a PoC is produced, it must carry an explicit, visually distinct limitations banner enumerating what the PoC does **not** do that the full system would (no real data, no real integrations, simulated logic, etc.) — the realistic bounds stated up front, not buried.

### Stage 3 — Information-flow / architecture map (optional)

Generated from the outline (and PoC, if one exists): a diagram of actors, systems, data stores and flows. Authored as Mermaid source and rendered to SVG at generation time so it embeds reliably in the notebook and HTML report later. A user who built a PoC can still request the map afterwards; the two coexist.

### Amendments

User suggestions at any point propagate to the outline, PoC, and map. Consistency is maintained by regenerating downstream artefacts from the amended outline rather than patching them independently — the outline is the single source of truth for the concept.

### Phase 1 outputs (committed to the repo under `runs/<run-id>/`)

`outline.md` (structured, with YAML front-matter so downstream agents can parse fields deterministically), `poc.html` (single file, self-contained), `flow-map.mmd` + `flow-map.svg`, and the interview transcript. The outline is downloadable by the user as markdown.

### Submission gate

The user explicitly submits to the Governance phase. Outline is required; PoC and flow map are encouraged but optional, and the submission screen should encourage them honestly (the assessment is richer with them).

---

## 5. Phase 2 — Governance

### 5.1 Fidelity to the DTA instrument (hard requirement)

The pipeline follows the *AI impact assessment tool* v1.0 structure exactly: sections 1–4 constitute the **threshold assessment**; sections 5–12 the **full assessment**. Section 3 contains eight inherent-risk categories (3.1 accessibility/inclusion, 3.2 unfair discrimination, 3.3 stereotyping/demeaning representations, 3.4 harm, 3.5 privacy, 3.6 security–data aspects, 3.7 security–system aspects, 3.8 reputation/public confidence), each requiring a consequence level, a likelihood level, a risk rating and a written rationale.

**Design rule — models argue, code computes.** LLM agents select consequence and likelihood with evidenced rationale (using the tool's own 5-tier descriptors and the guidance appendix's consequence table, which should be in every generalist's context). The risk rating for each category is then computed deterministically from the tool's Table 2 matrix, and the overall inherent rating (3.9) is computed as highest-wins. No model ever asserts a rating directly. The same rule applies at 12.3–12.4 (risk summary and residual rating). This removes the most attackable failure mode of the whole system.

The tool's own precautionary guidance is encoded in prompts: where generalists are uncertain or disagree, take the higher rating; document assumptions; likelihood defaults to at least "possible" when evidence is thin.

### 5.2 Threshold assessment

Two generalist agents (Gemini Flash) independently and in parallel complete sections 1–4 from the brainstorm artefacts — independent parallel drafting was chosen over sequential debate because disagreement between independent assessors is signal, and the tool's own guidance says to resolve rating disagreement upward. A reconciler agent (Gemini Pro) then compares the two drafts, adopts or synthesises each field, applies higher-rating-wins where they diverge on consequence/likelihood, and writes the final threshold assessment. Disagreements are **surfaced, not hidden**: the reconciler records material divergences and its resolution reasoning in a visible "assessor divergence" note.

The completed threshold assessment, including the deterministic 3.9 outcome, is presented to the user for review and input, and is downloadable as markdown. The routing then follows the tool's own logic: if all risks are low, the user may conclude here (with the artefact framed as ready for an approving officer's endorsement); if any risk is medium or high, a full assessment is required; and the user may also elect a full assessment regardless. The threshold artefact supports the standard two revision cycles (§7).

### 5.3 Full assessment — the specialist college

Six specialist agents, each with its own discrete SQLite knowledge base and clear section ownership. **Specialists must not edit another specialist's work or any supporting artefact** — enforced structurally: each agent's write scope is limited to its own assigned sections.

| Specialist | Primary sections | Indicative corpus (Tom curates; suggestions welcome) |
| --- | --- | --- |
| IT Security | 6.7 (intervene/disengage), 7.3 (security risks), contributes 3.6/3.7 context to reviewer | Australian ISM (June 2026), OWASP ASVS 5.0, OWASP State of Agentic AI Security & Governance 2.01, ASD *Engaging with AI*, ASD AI data security guidance, PSPF extracts incl. the OFFICIAL-information-with-generative-AI advisory |
| Privacy | 7.1, 7.2 | Privacy Act 1988 APPs (Schedule 1), OAIC APP guidelines extracts, OAIC guidance on AI and privacy / commercially available AI products, Australian Government Agencies Privacy Code, OAIC PIA advice, De-identification Decision-Making Framework |
| Ethics & Fairness | 5.1, 5.2, 8.1, 8.2, 8.4, 10.1 | Australia's AI Ethics Principles, NAIC *Implementing Australia's AI Ethics Principles*, CSIRO Data61 Responsible AI Pattern Catalogue (incl. Fairness Assessor Metrics Pattern), APS Framework for Engagement and Participation, AIATSIS engagement principles |
| Legal & Administrative Law | 9.1, 9.2, 10.2, 11.1, 12.1, 12.2 | Anti-discrimination Acts (Age 2004, Disability 1992, Racial 1975, Sex 1984 — summaries/extracts), Human Rights (Parliamentary Scrutiny) Act 2011 treaty list, Commonwealth Ombudsman ADM Better Practice Guide, ADJR Act overview, Robodebt RC rec 17.1 context, PGPA duty-of-care material |
| Data Governance | 6.1, 6.2, 8.3 | APS Data Ethics Framework, ABS Data Quality Framework, Framework for Governance of Indigenous Data (+ CARE/FAIR principles), NAA Information Management Standard and AI-records advice, Archives Act obligations summary |
| Solution Architect | 6.3–6.6, 6.8, and the **Implementation Plan appendix** | DTA AI technical standard, AI procurement guidance / contract template / model clauses, NIST AI RMF + Playbook, MIT AI Risk Repository, plus general architecture references Tom selects |

Section 12.3/12.4 are assembled by code plus the reviewer; 12.5 (internal governance body review) is emitted as a flagged human action, since no agent can perform it.

Each specialist works from: the brainstorm artefacts, the completed threshold assessment, retrieval over its own KB, and the tool's question text plus the corresponding guidance section. Specialists have broad creative freedom — subheadings, Mermaid diagrams, worked examples — provided every claim resting on the corpus **cites document and pinpoint locator** (true page for PDFs; provision, heading or sheet/row anchor otherwise — tech spec §8.2). Where information is missing from the scoping material, the specialist does not silently guess: it states the gap, recommends the concrete step the project team should take, and flags it in a machine-readable way so gaps aggregate into a "Recommended next steps" register in the final notebook.

### 5.4 The question checkpoint (single pause)

Each specialist may ask the user a maximum of three questions, and only where guessing would be genuinely inappropriate despite its expertise; the happy path is zero questions. Mechanically this is one checkpoint: all specialists draft, all questions are batched, the pipeline pauses and surfaces the questions in the UI under the run code, and once answered the run resumes with each specialist revising its own sections once in light of the answers. Unanswered questions (user may skip) convert to flagged gaps.

### 5.5 Solution architect appendix

After the specialists finalise, the architect reads the complete draft impact assessment, threshold assessment and brainstorm artefacts and writes a detailed implementation plan as a notebook appendix — architecture and sequencing, diagrams, code examples where useful, and explicit traceability to the mitigations and controls the specialists proposed (so the plan demonstrably answers the assessment rather than existing beside it). The architect cannot modify any other content.

### 5.6 Adjudicating review

A reviewer agent on the most capable model (Gemini Pro) audits the assembled document for two things: **coverage** (every question in the tool answered or explicitly flagged as a gap) and **coherence** (no internal contradictions between sections, and consistency with the threshold assessment). On finding a conflict, the reviewer determines which specialist's position is less well supported and directs that specialist to amend its own section, with reasons. This loop is capped at **two cycles**; conflicts still unresolved after two cycles are not forced into false agreement but recorded in a visible "Points of unresolved disagreement" block — for a governance artefact, honest disagreement is more credible than manufactured consensus.

### 5.7 Assembly and outputs

The final artefact is a Jupyter notebook, **assembly-and-provenance format, not executable** — built programmatically with nbformat, following the tool's 12-section structure, embedding the rendered PoC, the flow map and any specialist diagrams (SVG, pre-rendered), the full citation apparatus, the gap/next-steps register, the divergence and disagreement notes, and a provenance cell (run ID, timestamps, model versions per role, corpus manifest versions, agent-to-section attribution, input-sensitivity attestation). An nbconvert HTML render is produced alongside it as the shareable deliverable for SMEs. Both are committed under the run ID and downloadable from the UI. The notebook is treated as a final artefact: it should hold up to scrutiny from its creator and from subject matter experts.

---

## 6. Transparency layer — the useful loading screen

Throughout the Governance phase the user watches an animated pipeline diagram showing which agents are active and what they are doing — tool calls, document retrievals ("Privacy specialist retrieving: OAIC PIA guidance, p.14"), drafting, review cycles. The animation is **pre-scripted against the known pipeline topology**, with simple variables streamed in to drive it: the pipeline writes a `status.json` (current step, active agent, event log entries with a small controlled event vocabulary) to the repo at each step, and the frontend polls it every few seconds. Near-real-time is the agreed fidelity; no websockets or true streaming required. The goal is that a non-expert finishes a run feeling confident every element of the assessment was comprehensively considered — the animation is a trust instrument, not decoration. The design brief owns its look and storyboard; the tech spec owns the event vocabulary.

---

## 7. Resilience, resume and revision rules

Every run is issued a short human-copyable **run code** (e.g., `WT-7K3D-Q2`) displayed persistently in the UI. The pipeline checkpoints after every stage by committing state (JSON) and artefacts to the repo. On any mid-run failure the UI surfaces the run code with a plain-language explanation; pasting the code later resumes from the last completed checkpoint. The question checkpoint (§5.4) rides on the same mechanism — a paused run and a failed run resume identically.

**Revision caps (agreed):** the initial brainstorm conversation is unbounded; after initial generation, the information-flow map, the PoC, the threshold assessment and the full impact assessment each support a maximum of **two** user-driven revision cycles. The reviewer's internal correction loop is separately capped at two cycles (§5.6).

---

## 8. Architecture summary

Recorded here so the tech spec elaborates rather than re-decides.

| Component | Decision | Notes |
| --- | --- | --- |
| Frontend | Static SPA (React/Vite), hosted on GitHub Pages | Talks to Render API; polls status.json for pipeline views |
| Interactive backend | Python FastAPI on Render free tier | Runs the Brainstorm phase (live Gemini calls), issues run codes, triggers Governance runs via `workflow_dispatch`, proxies run status. Render free tier sleeps when idle — UI must set the ~60s cold-start expectation gracefully |
| Governance pipeline | Python, GitHub Actions in the repo | Free unlimited minutes on public-repo standard runners; commits state back with the built-in Actions token |
| Persistence | Git commits to the repo (`runs/<run-id>/`) | Render's disk is ephemeral; the repo is the durable store and doubles as the public audit trail |
| Specialist KBs | One SQLite file per specialist | Structure-anchored chunks with typed locators (page / provision / sheet-row); a committed LLM-readable index per KB plus FTS5 BM25 search — specialists navigate the index and fetch chunks through a bounded tool loop; no dense-embedding stack (tech spec §8, revised after corpus review). All ingestion compute happens inside Actions runners, never on Render |
| Ingestion | GitHub Action, manually or push-triggered | Tom uploads corpus documents to per-specialist folders; the Action extracts structure-aware (true pages for PDFs, style trees for docx, normalized sheets for xlsx), chunks along document structure, builds the index and FTS search, and writes each KB with a manifest recording document metadata, version and a licence/redistributability flag. The flag is a hard gate: ingestion refuses any document not cleared for public redistribution, since the repo is public |
| LLM provider | Gemini (Tom's pre-paid tokens) | Key in Render env + Actions secrets. Exponential backoff on rate limits; per-run token/cost logging into the provenance record |

**Model allocation (single config file, adjustable):** Flash-Lite — brainstorm interviewer turns and sufficiency checks; Flash — outline synthesis, PoC and map generation, the two threshold generalists, the six specialists; Pro — threshold reconciler, adjudicating reviewer, solution architect. Rationale: Flash-Lite is fine where the artefact is conversational or rubric-checked; risk reasoning and cited argumentation warrant Flash; synthesis-and-judgement roles warrant Pro. If quality testing shows specialists need Pro, the config flip is one line — budget for that possibility.

---

## 9. Delivery stages

| Stage | Scope | Exit test |
| --- | --- | --- |
| 0 — Foundations | Single-repo scaffold (§3), run-state model + run codes, ingestion pipeline, one populated specialist KB end-to-end | A fetch/search returns pinpoint-cited chunks from a real corpus doc |
| 1 — Brainstorm | Interview + live outline canvas, sufficiency gate, PoC + feasibility gate, flow map, amendment propagation, submission gate | A stranger takes a loose idea to a submitted outline (+PoC) unaided |
| 2 — Threshold | Generalists, reconciler, deterministic rating engine, review/revise UI, markdown export | Threshold output for a known test case matches a hand-worked assessment's ratings exactly |
| 3 — Full assessment | Specialist college, question checkpoint, architect appendix, reviewer loop, notebook + HTML assembly | An SME reads the HTML report cold and can follow every claim to a cited source |
| 4 — Transparency & polish | Animated pipeline view, failure/resume UX, accessibility pass, **dogfood run: Windtunnel assesses Windtunnel** | Dogfood notebook is presentable as the competition demo |

The Governance phase (stages 2–3) is the priority; if timeboxing forces cuts, they come from stage 4 polish and brainstorm niceties, never from citation quality or instrument fidelity.

---

## 10. Risks and open items

**Gemini rate limits vs run duration.** A full assessment is dozens of LLM calls; with backoff a run may take tens of minutes. Acceptable (the transparency animation exists precisely to make waiting tolerable), but the tech spec should budget calls per stage and log actuals.

**Mermaid in notebooks.** Mermaid does not render natively in nbconvert HTML; all diagrams are rendered to SVG at generation time and embedded as images, with Mermaid source preserved alongside for provenance.

**Corpus licensing.** With a single public repo, every corpus document is republished twice over — as source and as chunked text inside the KBs — so only genuinely redistributable material can be ingested (Commonwealth CC-BY material and OWASP are fine; verify anything else before adding it). The ingestion manifest's licence flag enforces this as a hard gate.

**Citation integrity.** Pinpoint citations are only as good as the extraction. Ingestion must store a true source locator with each chunk (real page numbers for PDFs; provision, heading or sheet/row anchors for formats without fixed pages), and stage-3 exit testing must include manual spot-checks of citations against source documents.

**Reviewer authority.** "Amend the less-correct specialist" requires the reviewer to justify its ruling in writing; those rulings are preserved in provenance so a human can audit the audit.

**PoC quality variance.** Single-file HTML PoCs from an LLM vary in quality; the limitations banner plus the feasibility gate manage expectations, and the two-cycle revision cap prevents rabbit-holing.

**Open items for Tom:** final product name; final corpus lists per specialist (indicative lists above are a starting point); competition submission constraints (deadline, demo format) that should back-propagate into stage sequencing.

---

## 11. Handoff

The technical specification treats §5.1's "models argue, code computes" rule, the single-public-repo layout, the checkpoint/resume model, and the revision caps as fixed. The design brief owns the canvas layout, stage telegraphing, warning treatments, animation storyboard, and report styling. Both documents are complete and sit alongside this brief as `TECH_SPEC.md` and `DESIGN_BRIEF.md`; each closes with its own open-items list (tech spec §16, design brief §11). The handoff stubs that briefed those two instances have been fully absorbed into the completed documents and are not part of this repository.
