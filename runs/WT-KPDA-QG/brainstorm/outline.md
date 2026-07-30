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
summary: "An iterative AI agent that interviews staff to map workflows, requiring SME validation and timestamping for all inputs to ensure accuracy and auditability."
created_at: "2026-07-30T05:13:52Z"
updated_at: "2026-07-30T05:39:20Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui", "constraints", "success_criteria"]
---

<!-- section: problem -->
## 1. Problem

Teams often struggle to document complex workflows, leading to hidden bottlenecks and inconsistent processes that are difficult to analyze or improve.

<!-- section: solution -->
## 2. Proposed solution

An AI-driven conversational agent that conducts iterative, stateful interviews to map workflows. The process begins with a Business Analyst (BA) seeding the agent with foundational concepts. The agent cross-references inputs from multiple team members, prioritizing SME operational reality over BA data. It enforces a strict 'no-interpolation' policy, requiring the agent to ask for clarification rather than inferring meaning. It flags 'solutioning' attempts by staff with a gentle nudge to refocus on the problem, and flags irreconcilable process conflicts for human management review. Every input must be validated and timestamped by the SME before being committed to the knowledge base. The final output is a visual process map and a structured report, including a 'To BA's Attention' section and an automated summary of versioned changes.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

Internal team members are the primary users; process owners and management are the stakeholders who consume the resulting workflow maps.

<!-- section: data -->
## 4. Data

The agent processes transcripts of internal interviews, existing process documentation, and foundational knowledge provided by the BA; this data is internal and contains sensitive operational details.

<!-- section: happy_path -->
## 5. Happy path

A team member starts a session, and the agent asks discovery questions. As the user provides details, the agent identifies gaps or conflicts with previous interviews, asking the user to clarify. Once the agent has a draft, the SME reviews and validates the summary; upon their timestamped approval, the data is committed to the knowledge base. The agent then generates a visual process map, highlighting areas of consensus and unresolved friction for management oversight.

<!-- section: alternatives -->
## 6. Alternatives considered

Manual interviews conducted by a business analyst, or using standard process mining software that tracks system logs rather than human-reported pain points.

<!-- section: ux_ui -->
## 7. UX and interface

A chat-based interface (e.g., Slack or a web portal) for the interview process, with a dashboard view for managers to access the generated visual process maps and structured reports.

<!-- section: constraints -->
## 8. Constraints and preferences

The system must operate within standard internal data privacy protocols. It requires integration with existing documentation repositories to pull foundational policy data and push final process maps and reports.

<!-- section: success_criteria -->
## 9. Success criteria

Success will be measured by the speed at which teams reach consensus on process changes, validated by a reduction in the time required for management to resolve process conflicts compared to manual discovery methods.
