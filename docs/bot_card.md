# Windtunnel — Bot Card

## Purpose

Windtunnel helps public servants explore AI ideas responsibly from day one. Through a guided
co-design conversation followed by a multi-agent governance assessment, it transforms an early
concept into a substantially complete, fully cited draft AI Impact Assessment aligned to the
Australian Government's AI Impact Assessment Tool (v1.0).

A complete, plain-language walkthrough is available in
[`SYSTEM_OVERVIEW.ipynb`](https://github.com/Thomas-Amann-IPAustralia/wind-tunnel/blob/main/SYSTEM_OVERVIEW.ipynb).

## Intended users

Public servants who are exploring AI-enabled services and want to understand governance
implications before engaging formal subject matter experts or assessment panels.

## Information used

- Information voluntarily provided by the user about their proposed AI system.
- A curated library of approximately 110 publicly available government policies, standards and
  guidance documents.
- The Australian Government AI Impact Assessment Tool and supporting guidance.

## Limitations

- Produces a draft assessment only.
- Does not provide legal advice or replace official governance, approval or assurance processes.
- Knowledge is limited to its curated document library and does not represent all Commonwealth
  policy.

## Key risks

- Everything submitted or generated is stored in a public, world-readable GitHub repository, and
  the system carries no security accreditation — disclosed prominently before any input is
  accepted.
- Users may over-rely on AI-generated outputs.
- AI models may produce unsupported conclusions.
- User-provided content could contain prompt injection attempts.

These risks are mitigated through prominent up-front disclosure of the public-repository storage,
deterministic risk calculations (models never assign a rating), mandatory evidence-based
citations, specialist agent boundaries, and treating all user input as untrusted data.

## Tools used

- Google Gemini (Flash-Lite, Flash and Pro) — the reasoning agents
- Claude Code — the engineering tool used to build the system
- Python, FastAPI (hosted on Render) and GitHub Actions — the backend and governance pipeline
- React and TypeScript, served via GitHub Pages — the interface
- Mermaid.js — client-side flow-map rendering
- SQLite (FTS5) — the specialist knowledge bases
- Jupyter (nbformat/nbconvert) — the assessment notebook and HTML report
- The GitHub repository itself — the durable store and public audit trail for every run
- ChatGPT and Adobe Photoshop — the loading-animation sprite sheet (AI-generated, then manually
  corrected)
