<!--
  Windtunnel project outline. Contract: TECH_SPEC.md §7.1.
  This file is copied verbatim into runs/<run-id>/brainstorm/outline.md at run
  creation. Only the backend writes it. Each section body is replaced whole,
  between its anchor comment and the next; the front-matter `resolved` list is
  machine-maintained and is the single deterministic record of completeness.
-->
---
schema_version: 1
run_id: "WT-TR4C-DC"
title: "Canberra Business Navigator"
summary: "A chatbot designed to guide small business owners through government registration, regulatory requirements, and funding opportunities."
created_at: "2026-07-17T09:10:23Z"
updated_at: "2026-07-17T09:27:11Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui", "constraints"]
---

<!-- section: problem -->
## 1. Problem

Small business owners in Canberra often struggle to navigate the complex landscape of government registration requirements, regulatory obligations, and available funding opportunities, leading to confusion and potential compliance gaps.

<!-- section: solution -->
## 2. Proposed solution

The solution is a conversational AI assistant that acts as a navigator for small business owners. It uses a large language model to ingest and interpret government regulatory documents, legislation, and funding guidelines, allowing users to ask plain-language questions about their specific business obligations and opportunities.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

The primary users are small business owners in Canberra. Key stakeholders include ACT government staff who manage regulatory compliance, as well as professional business advisors and accountants, whose workflows may be impacted by the tool's ability to provide instant regulatory guidance.

<!-- section: data -->
## 4. Data

The tool will ingest and reference publicly available government regulatory documents, legislation, and funding guidelines. It does not require access to private business records or sensitive internal government data.

<!-- section: happy_path -->
## 5. Happy path

A new cafe owner texts the WhatsApp bot asking about their WHS obligations. The bot analyzes the query against the ingested ACT government regulatory documents and provides a concise, plain-language summary of the relevant requirements. If the query is ambiguous or the bot lacks a definitive answer, it provides links to official ACT government contact points and portals for further guidance, ensuring the user is never left without a path to resolution.

<!-- section: alternatives -->
## 6. Alternatives considered

The primary non-AI alternatives are centralized government call centers and static, search-based knowledge bases. These options are limited by their operating hours and their inability to interpret the specific, nuanced context of a user's business query. An AI-driven approach provides 24/7 accessibility and the capacity to translate complex regulatory language into actionable, personalized advice, while still grounding the output in authoritative government content.

<!-- section: ux_ui -->
## 7. UX and interface

The interface is a conversational chatbot accessible via WhatsApp for mobile convenience, with an integrated web-based version hosted on the official Business.gov portal.

<!-- section: constraints -->
## 8. Constraints and preferences

The system must strictly avoid providing legal advice or recommending specific commercial suppliers. All interactions must be clearly framed as informational guidance. Additionally, the system must retain logs of all data interactions for audit and improvement purposes, while ensuring compliance with government information standards.

<!-- section: success_criteria -->
## 9. Success criteria

*How you'd know, six months in, that it worked.*
