<!--
  Windtunnel project outline. Contract: TECH_SPEC.md §7.1.
  This file is copied verbatim into runs/<run-id>/brainstorm/outline.md at run
  creation. Only the backend writes it. Each section body is replaced whole,
  between its anchor comment and the next; the front-matter `resolved` list is
  machine-maintained and is the single deterministic record of completeness.
-->
---
schema_version: 1
run_id: "WT-CNSF-FW"
title: "Departmental Knowledge Graph"
summary: "Building an AI-powered knowledge graph to map and connect fragmented internal departmental information."
created_at: "2026-07-30T04:05:35Z"
updated_at: "2026-07-30T04:07:17Z"
resolved: ["problem", "solution", "users_stakeholders", "data"]
---

<!-- section: problem -->
## 1. Problem

Departmental information is currently siloed and fragmented, making it difficult for staff to discover relevant internal knowledge, policies, or project history efficiently.

<!-- section: solution -->
## 2. Proposed solution

An automated knowledge graph that ingests internal documents and communications to map relationships between entities, using AI to extract nodes and edges from unstructured text.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

Primary users are departmental staff and policy researchers; stakeholders include IT/data governance teams responsible for information security and the leadership team seeking better organizational insights.

<!-- section: data -->
## 4. Data

Internal unstructured data including policy documents, meeting minutes, project reports, and potentially internal wikis or email archives; sensitivity is likely high given the internal nature of the content.

<!-- section: happy_path -->
## 5. Happy path

*One ordinary, successful use — narrated start to finish.*

<!-- section: alternatives -->
## 6. Alternatives considered

*What else could solve this, including at least one non-AI option.*

<!-- section: ux_ui -->
## 7. UX and interface

*What the user sees and touches — or an honest "nothing; it's headless."*

<!-- section: constraints -->
## 8. Constraints and preferences

*The hard limits and strong preferences: technical, organisational, maintenance.*

<!-- section: success_criteria -->
## 9. Success criteria

*How you'd know, six months in, that it worked.*
