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
updated_at: "2026-07-18T23:36:44Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "ux_ui"]
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

*One ordinary, successful use — narrated start to finish.*

<!-- section: alternatives -->
## 6. Alternatives considered

*What else could solve this, including at least one non-AI option.*

<!-- section: ux_ui -->
## 7. UX and interface

A web-based chat interface integrated into the existing ATO portal, likely featuring a disclaimer and links to official policy documentation for verification.

<!-- section: constraints -->
## 8. Constraints and preferences

*The hard limits and strong preferences: technical, organisational, maintenance.*

<!-- section: success_criteria -->
## 9. Success criteria

*How you'd know, six months in, that it worked.*
