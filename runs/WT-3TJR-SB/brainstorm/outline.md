<!--
  Windtunnel project outline. Contract: TECH_SPEC.md §7.1.
  This file is copied verbatim into runs/<run-id>/brainstorm/outline.md at run
  creation. Only the backend writes it. Each section body is replaced whole,
  between its anchor comment and the next; the front-matter `resolved` list is
  machine-maintained and is the single deterministic record of completeness.
-->
---
schema_version: 1
run_id: "WT-3TJR-SB"
title: "APS AI Thought Partner"
summary: "A creative AI-powered brainstorming assistant designed to help public servants identify and explore novel solutions to complex policy and project challenges."
created_at: "2026-07-17T15:27:49Z"
updated_at: "2026-07-17T15:34:05Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui"]
---

<!-- section: problem -->
## 1. Problem

Public servants often face challenges in identifying creative or novel approaches to complex problems because they lack exposure to diverse methodologies or perspectives, leading to a 'blind spot' where they are unaware of potential solutions they haven't yet considered.

<!-- section: solution -->
## 2. Proposed solution

A web-based brainstorming tool that acts as a creative thought partner for public servants, using generative AI to help users iterate on project ideas, policy drafts, or research questions.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

The tool is intended for use by any public servant across the Australian Public Service (APS), with initial deployment planned via the Department of Finance's GovAI Exchange platform. The primary users are policy officers and project managers, while the broader APS benefits from more robust and creative policy outcomes.

<!-- section: data -->
## 4. Data

The tool processes non-sensitive, OFFICIAL information. Users primarily input rough notes, project ideas, and preliminary policy concepts rather than classified or sensitive internal documents.

<!-- section: happy_path -->
## 5. Happy path

A policy officer opens the tool and uses voice input to describe a rough, early-stage project idea. The AI listens, then responds conversationally to build on the concept, offering alternative perspectives or gently challenging underlying assumptions. The interaction continues as a back-and-forth dialogue until the officer reaches a point of clarity or identifies a new, creative direction for their project.

<!-- section: alternatives -->
## 6. Alternatives considered

While traditional search tools like Google exist, they are limited to retrieving existing information and cannot provide the iterative, conversational synthesis required to develop new project ideas. No non-AI solution is considered viable for providing this specific type of interactive, lateral-thinking support.

<!-- section: ux_ui -->
## 7. UX and interface

The interface is voice-first, designed to feel like a natural conversation with a human partner. The visual design is clean and minimalist to keep the focus entirely on the dialogue and the generation of ideas.

<!-- section: constraints -->
## 8. Constraints and preferences

*The hard limits and strong preferences: technical, organisational, maintenance.*

<!-- section: success_criteria -->
## 9. Success criteria

*How you'd know, six months in, that it worked.*
