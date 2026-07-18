<!--
  Windtunnel project outline. Contract: TECH_SPEC.md §7.1.
  This file is copied verbatim into runs/<run-id>/brainstorm/outline.md at run
  creation. Only the backend writes it. Each section body is replaced whole,
  between its anchor comment and the next; the front-matter `resolved` list is
  machine-maintained and is the single deterministic record of completeness.
-->
---
schema_version: 1
run_id: "WT-FXD5-3G"
title: "ATO Deduction Assistant"
summary: "A public-facing chatbot designed to help taxpayers understand deduction eligibility through conversational guidance."
created_at: "2026-07-18T23:35:12Z"
updated_at: "2026-07-18T23:39:15Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui", "constraints"]
---

<!-- section: problem -->
## 1. Problem

Taxpayers often struggle to navigate complex deduction rules, leading to errors in their returns or unnecessary inquiries to the ATO.

<!-- section: solution -->
## 2. Proposed solution

A public-facing chatbot hosted by the ATO that provides guidance on eligible tax deductions based on user-provided employment or expense details, using an LLM to interpret tax policy documents.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

Primary users are individual taxpayers; stakeholders include ATO support staff and policy teams responsible for the accuracy of the guidance.

<!-- section: data -->
## 4. Data

The system will process public tax policy documents and potentially anonymized user-provided financial scenarios; it must be strictly isolated from actual taxpayer account data.

<!-- section: happy_path -->
## 5. Happy path

A taxpayer accesses the portal, answers three triage questions to filter their deduction category, and then interacts with the chatbot. The bot provides guidance based on specific policy documents, citing the source, and directs the user to the official ATO website for final verification before they submit their return.

<!-- section: alternatives -->
## 6. Alternatives considered

Non-AI alternatives include an interactive decision tree or a static FAQ wizard. While these are highly accurate, they often fail to capture the nuance of unique taxpayer scenarios, which is why a RAG-based LLM is being explored.

<!-- section: ux_ui -->
## 7. UX and interface

A web-based chat interface integrated into the existing ATO portal, likely featuring a disclaimer and links to official policy documentation for verification.

<!-- section: constraints -->
## 8. Constraints and preferences

The system must remain strictly advisory, include prominent disclaimers, and ensure no integration with live taxpayer account data to maintain security and legal boundaries.

<!-- section: success_criteria -->
## 9. Success criteria

*How you'd know, six months in, that it worked.*
