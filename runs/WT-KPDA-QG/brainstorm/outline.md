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
summary: "An iterative AI agent that interviews staff to map workflows, cross-referencing multi-user inputs to resolve process conflicts while enforcing a separation between operational discovery and technical solutioning."
created_at: "2026-07-30T05:13:52Z"
updated_at: "2026-07-30T05:35:09Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui", "constraints", "success_criteria"]
---

<!-- section: problem -->
## 1. Problem

Teams often struggle to document complex workflows, leading to hidden bottlenecks and inconsistent processes that are difficult to analyze or improve.

<!-- section: solution -->
## 2. Proposed solution

An AI-driven conversational agent that conducts iterative, stateful interviews to map workflows. The process begins with a Business Analyst (BA) seeding the agent with foundational concepts and policy documentation. The agent cross-references inputs from multiple team members, prioritizing SME operational reality over BA foundational data. It actively identifies and flags 'solutioning' attempts by staff, providing a gentle nudge to refocus the conversation on the underlying problem. It flags irreconcilable process conflicts for human management review. The final output is a visual process map and a structured report, including a 'To BA's Attention' section for unresolved conflicts and an automated summary of changes between versioned iterations.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

Internal team members are the primary users; process owners and management are the stakeholders who consume the resulting workflow maps.

<!-- section: data -->
## 4. Data

The agent processes transcripts of internal interviews, existing process documentation, and foundational knowledge provided by the BA; this data is internal and contains sensitive operational details.

<!-- section: happy_path -->
## 5. Happy path

A team member starts a session, and the agent asks discovery questions. As the user provides details, the agent identifies gaps or conflicts with previous interviews, asking the user to clarify or provide reasoning. Once the agent has sufficient information, it generates a draft process map for user review, highlighting areas of consensus and unresolved friction for management oversight.

<!-- section: alternatives -->
## 6. Alternatives considered

Manual interviews conducted by a business analyst, or using standard process mining software that tracks system logs rather than human-reported pain points.

<!-- section: ux_ui -->
## 7. UX and interface

A chat-based interface (e.g., Slack or a web portal) for the interview process, with a dashboard view for managers to access the generated visual process maps and structured reports.

<!-- section: constraints -->
## 8. Constraints and preferences

Must ensure data privacy for sensitive internal processes, maintain a verifiable audit trail of user confirmations, support version history for all generated maps and reports with automated change summaries, and be capable of integrating with existing documentation tools.

<!-- section: success_criteria -->
## 9. Success criteria

The agent successfully maps at least three core workflows that are validated by process owners as accurate and actionable.
