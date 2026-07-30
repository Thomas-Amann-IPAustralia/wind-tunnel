<!--
  Windtunnel project outline. Contract: TECH_SPEC.md §7.1.
  This file is copied verbatim into runs/<run-id>/brainstorm/outline.md at run
  creation. Only the backend writes it. Each section body is replaced whole,
  between its anchor comment and the next; the front-matter `resolved` list is
  machine-maintained and is the single deterministic record of completeness.
-->
---
schema_version: 1
run_id: "WT-KPDA-QG"
title: "Workflow Discovery AI Agent"
summary: "An iterative AI agent that interviews staff to dynamically map complex workflows, identify bottlenecks, and build a structured process knowledge base."
created_at: "2026-07-30T05:13:52Z"
updated_at: "2026-07-30T05:19:22Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui", "constraints", "success_criteria"]
---

<!-- section: problem -->
## 1. Problem

Teams often struggle to document complex workflows, leading to hidden bottlenecks and inconsistent processes that are difficult to analyze or improve.

<!-- section: solution -->
## 2. Proposed solution

An AI-driven conversational agent that conducts iterative, stateful interviews to map workflows. It dynamically generates follow-up questions based on previous responses to uncover branching logic, pain points, and bottlenecks, progressively building a structured knowledge base of the process.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

Internal team members are the primary users; process owners and management are the stakeholders who consume the resulting workflow maps.

<!-- section: data -->
## 4. Data

The agent will process transcripts of internal interviews and potentially existing process documentation; this data is internal and likely contains sensitive operational details.

<!-- section: happy_path -->
## 5. Happy path

A team member starts a session, and the agent asks initial discovery questions. As the user provides details, the agent identifies gaps and asks targeted follow-up questions to clarify branching logic. Once the agent has sufficient information, it generates a draft process map for the user to review and confirm, which is then exported for management.

<!-- section: alternatives -->
## 6. Alternatives considered

Manual interviews conducted by a business analyst, or using standard process mining software that tracks system logs rather than human-reported pain points.

<!-- section: ux_ui -->
## 7. UX and interface

A chat-based interface (e.g., Slack or a web portal) where the agent guides the user through a structured interview.

<!-- section: constraints -->
## 8. Constraints and preferences

Must ensure data privacy for sensitive internal processes, maintain a verifiable audit trail of user confirmations, and be capable of integrating with existing documentation tools.

<!-- section: success_criteria -->
## 9. Success criteria

The agent successfully maps at least three core workflows that are validated by process owners as accurate and actionable.
