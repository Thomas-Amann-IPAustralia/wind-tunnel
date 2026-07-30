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
summary: "An AI agent that interviews staff to document workflows, identify bottlenecks, and map process branching."
created_at: "2026-07-30T05:13:52Z"
updated_at: "2026-07-30T05:15:22Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui", "constraints", "success_criteria"]
---

<!-- section: problem -->
## 1. Problem

Teams often struggle to document complex workflows, leading to hidden bottlenecks and inconsistent processes that are difficult to analyze or improve.

<!-- section: solution -->
## 2. Proposed solution

An AI-driven conversational agent that interviews team members to map out their current workflows, identifying branching logic, pain points, and operational bottlenecks.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

Internal team members are the primary users; process owners and management are the stakeholders who consume the resulting workflow maps.

<!-- section: data -->
## 4. Data

The agent will process transcripts of internal interviews and potentially existing process documentation; this data is internal and likely contains sensitive operational details.

<!-- section: happy_path -->
## 5. Happy path

A team member initiates a session with the agent, which asks targeted questions about their daily tasks. The agent identifies a recurring bottleneck in a specific approval step, summarizes the workflow, and exports a structured process map for the team lead.

<!-- section: alternatives -->
## 6. Alternatives considered

Manual interviews conducted by a business analyst, or using standard process mining software that tracks system logs rather than human-reported pain points.

<!-- section: ux_ui -->
## 7. UX and interface

A chat-based interface (e.g., Slack or a web portal) where the agent guides the user through a structured interview.

<!-- section: constraints -->
## 8. Constraints and preferences

Must ensure data privacy for sensitive internal processes and be capable of integrating with existing documentation tools.

<!-- section: success_criteria -->
## 9. Success criteria

The agent successfully maps at least three core workflows that are validated by process owners as accurate and actionable.
