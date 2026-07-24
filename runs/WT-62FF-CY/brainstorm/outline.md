<!--
  Windtunnel project outline. Contract: TECH_SPEC.md §7.1.
  This file is copied verbatim into runs/<run-id>/brainstorm/outline.md at run
  creation. Only the backend writes it. Each section body is replaced whole,
  between its anchor comment and the next; the front-matter `resolved` list is
  machine-maintained and is the single deterministic record of completeness.
-->
---
schema_version: 1
run_id: "WT-62FF-CY"
title: "Austudy Application Modernisation"
summary: "An AI-assisted triage tool to accelerate Austudy eligibility verification by automating document review and flagging application gaps."
created_at: "2026-07-24T05:59:18Z"
updated_at: "2026-07-24T06:30:20Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "alternatives"]
---

<!-- section: problem -->
## 1. Problem

The current Austudy application process is manual, document-heavy, and prone to delays caused by incomplete submissions or complex eligibility verification, leading to long wait times for students.

<!-- section: solution -->
## 2. Proposed solution

An AI-driven document triage and eligibility assistant that extracts key information from uploaded evidence and cross-references it against policy requirements to flag missing information or potential issues before a human officer reviews the file.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

Primary users are Centrelink processing officers; students are the primary stakeholders affected by the speed and accuracy of the decision.

<!-- section: data -->
## 4. Data

Sensitive personal information, including financial records, enrolment status, and identity documents sourced directly from student applications.

<!-- section: happy_path -->
## 5. Happy path

*One ordinary, successful use — narrated start to finish.*

<!-- section: alternatives -->
## 6. Alternatives considered

Non-AI options include digitising the existing paper-based workflow, hiring more processing staff, or simplifying the policy rules themselves.

<!-- section: ux_ui -->
## 7. UX and interface

*What the user sees and touches — or an honest "nothing; it's headless."*

<!-- section: constraints -->
## 8. Constraints and preferences

*The hard limits and strong preferences: technical, organisational, maintenance.*

<!-- section: success_criteria -->
## 9. Success criteria

*How you'd know, six months in, that it worked.*
