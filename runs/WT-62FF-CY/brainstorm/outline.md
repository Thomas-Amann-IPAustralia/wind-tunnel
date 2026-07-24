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
summary: "An AI-assisted triage and guidance tool that uses real-time ATO data integration to verify eligibility and accelerate application processing."
created_at: "2026-07-24T05:59:18Z"
updated_at: "2026-07-24T06:36:45Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui", "constraints", "success_criteria"]
---

<!-- section: problem -->
## 1. Problem

The current Austudy application process is manual, document-heavy, and prone to delays, with processing times stretching up to six months due to incomplete submissions and complex eligibility verification.

<!-- section: solution -->
## 2. Proposed solution

An AI-driven document triage and eligibility assistant that extracts key information from uploaded evidence and cross-references it against policy requirements to flag missing information or potential issues before a human officer reviews the file.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

Primary users are Centrelink processing officers; students are the primary stakeholders affected by the speed and accuracy of the decision.

<!-- section: data -->
## 4. Data

Sensitive personal information, including financial records, enrolment status, and identity documents sourced from student applications, supplemented by real-time income and employment data retrieved via secure API from the Australian Taxation Office (ATO).

<!-- section: happy_path -->
## 5. Happy path

A student uploads documents and provides consent for ATO data matching. The AI validates the application in real-time; if data matches, it is queued for automated approval. In the 10% of cases where the AI detects a discrepancy between self-reported data and ATO records, the system flags the specific conflict for a human officer, providing a side-by-side 'diff' comparison of the conflicting data points to facilitate rapid resolution.

<!-- section: alternatives -->
## 6. Alternatives considered

Non-AI options include digitising the existing paper-based workflow, hiring more processing staff, or simplifying the policy rules themselves.

<!-- section: ux_ui -->
## 7. UX and interface

A dual-interface system: a student-facing 'application assistant' widget that provides real-time validation feedback, and an internal dashboard for officers that displays AI-extracted evidence summaries alongside the original documents.

<!-- section: constraints -->
## 8. Constraints and preferences

Must comply with strict privacy and data sovereignty requirements. The system must maintain a clear audit trail of all AI-assisted suggestions. We assume a policy-driven approach to cross-agency data sharing, with a defined 'human-in-the-loop' protocol for the 10% of cases where automated verification fails or identifies discrepancies.

<!-- section: success_criteria -->
## 9. Success criteria

A significant reduction in total application processing time from six months to a target of weeks, alongside a measurable decrease in 'request for information' (RFI) notices sent to students.
