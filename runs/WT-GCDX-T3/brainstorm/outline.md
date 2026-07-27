<!--
  Windtunnel project outline. Contract: TECH_SPEC.md §7.1.
  This file is copied verbatim into runs/<run-id>/brainstorm/outline.md at run
  creation. Only the backend writes it. Each section body is replaced whole,
  between its anchor comment and the next; the front-matter `resolved` list is
  machine-maintained and is the single deterministic record of completeness.
-->
---
schema_version: 1
run_id: "WT-GCDX-T3"
title: "Policy Impact Mapper"
summary: "An AI tool that automates the identification of internal policy dependencies by cross-referencing new legislation against a version-controlled snapshot of agency documentation."
created_at: "2026-07-27T04:44:01Z"
updated_at: "2026-07-27T04:48:35Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui", "constraints", "success_criteria"]
---

<!-- section: problem -->
## 1. Problem

Government agencies struggle to manually track how new legislation or policy updates impact existing internal frameworks, leading to slow response times and the risk of missing critical dependencies.

<!-- section: solution -->
## 2. Proposed solution

An AI-powered impact mapping tool that ingests new requirements and cross-references them against an agency's internal document repository to flag affected policies, forms, and processes with clear citations.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

Primary users are policy, legal, compliance, and operational staff. Affected stakeholders include the public and frontline staff who rely on accurate, up-to-date agency guidance.

<!-- section: data -->
## 4. Data

The system ingests public legislation and a curated, version-controlled snapshot of internal documents. It relies on metadata (owner, status, version, dates) to ensure it operates on the current approved state. It is designed to flag version conflicts or duplicates for human resolution rather than guessing, and it maintains an audit trail of which specific document versions were used for each analysis.

<!-- section: happy_path -->
## 5. Happy path

A policy officer uploads a new regulation; the tool generates an impact map highlighting three affected internal policies; the officer reviews the suggestions, confirms two as valid, and assigns them to the relevant business owners for update.

<!-- section: alternatives -->
## 6. Alternatives considered

Manual review via cross-departmental working groups (current state) or keyword-based search tools that lack semantic understanding of legislative intent.

<!-- section: ux_ui -->
## 7. UX and interface

A web-based dashboard where users can upload source text, view a generated impact map, and interact with a 'review/reject/assign' workflow for each identified dependency.

<!-- section: constraints -->
## 8. Constraints and preferences

Must remain a decision-support tool only; no automated changes. Restricted to unclassified internal data. For the POC, it will use a manually curated, frozen document set rather than live repository integration to ensure data integrity and auditability.

<!-- section: success_criteria -->
## 9. Success criteria

The success criteria now include a structured evaluation framework: tracking the ratio of confirmed versus rejected suggestions, categorizing false positives to inform system tuning, and measuring 'human-only' discoveries to identify gaps in the AI's retrieval logic. Performance will be validated through regression testing against a fixed set of examples after each iterative update.
