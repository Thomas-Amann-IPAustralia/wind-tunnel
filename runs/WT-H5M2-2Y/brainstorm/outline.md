<!--
  Windtunnel project outline. Contract: TECH_SPEC.md §7.1.
  This file is copied verbatim into runs/<run-id>/brainstorm/outline.md at run
  creation. Only the backend writes it. Each section body is replaced whole,
  between its anchor comment and the next; the front-matter `resolved` list is
  machine-maintained and is the single deterministic record of completeness.
-->
---
schema_version: 1
run_id: "WT-H5M2-2Y"
title: "Canberra Business Navigator AI"
summary: "A conversational assistant to help Canberra small businesses navigate government registrations and funding opportunities."
created_at: "2026-07-18T02:03:29Z"
updated_at: "2026-07-18T02:03:48Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui", "constraints", "success_criteria"]
---

<!-- section: problem -->
## 1. Problem

Small business owners in Canberra struggle to navigate the fragmented landscape of government registration requirements, compliance obligations, and available funding opportunities.

<!-- section: solution -->
## 2. Proposed solution

A conversational AI chatbot integrated into the government business portal that provides tailored guidance on registrations, permits, and grants based on user-provided business details.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

Primary users are small business owners and entrepreneurs. Stakeholders include the various government departments responsible for regulation and funding, who are affected by the quality and accuracy of the guidance provided.

<!-- section: data -->
## 4. Data

The system will process public-facing government policy documents, grant criteria, and registration requirements. It will also handle user-provided business information, which may include sensitive identifiers.

<!-- section: happy_path -->
## 5. Happy path

A user visits the portal, describes their business type and location, and the chatbot provides a prioritized checklist of necessary registrations and a list of relevant funding programs with direct links to application forms.

<!-- section: alternatives -->
## 6. Alternatives considered

A static, searchable FAQ database or a traditional 'wizard' style form that guides users through a decision tree without generative AI.

<!-- section: ux_ui -->
## 7. UX and interface

A web-based chat interface embedded on the government business portal, likely featuring a 'human-in-the-loop' escalation button for complex queries.

<!-- section: constraints -->
## 8. Constraints and preferences

Must strictly adhere to official government policy and maintain high accuracy; must be accessible and mobile-friendly.

<!-- section: success_criteria -->
## 9. Success criteria

A measurable reduction in support tickets related to basic registration questions and positive user feedback on the clarity of the guidance provided.
