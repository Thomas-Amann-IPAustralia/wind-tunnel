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
summary: "An AI-assisted triage and guidance tool that helps students submit complete applications while providing processing officers with pre-verified summaries to accelerate eligibility decisions."
created_at: "2026-07-24T05:59:18Z"
updated_at: "2026-07-24T06:30:41Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui", "constraints", "success_criteria"]
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

A student uploads documents via the portal; the AI provides real-time feedback on missing fields or unclear evidence. Once submitted, the AI generates a summary report for the processing officer, highlighting verified data points and flagging potential policy conflicts, allowing the officer to approve the application in minutes rather than hours.

<!-- section: alternatives -->
## 6. Alternatives considered

Non-AI options include digitising the existing paper-based workflow, hiring more processing staff, or simplifying the policy rules themselves.

<!-- section: ux_ui -->
## 7. UX and interface

A dual-interface system: a student-facing 'application assistant' widget that provides real-time validation feedback, and an internal dashboard for officers that displays AI-extracted evidence summaries alongside the original documents.

<!-- section: constraints -->
## 8. Constraints and preferences

Must comply with strict privacy and data sovereignty requirements for sensitive personal information; the system must maintain a clear audit trail of all AI-assisted suggestions for human oversight.

<!-- section: success_criteria -->
## 9. Success criteria

A 30% reduction in average processing time and a measurable decrease in 'request for information' (RFI) notices sent to students due to incomplete initial applications.
