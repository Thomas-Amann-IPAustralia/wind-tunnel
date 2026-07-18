<!--
  Windtunnel project outline. Contract: TECH_SPEC.md §7.1.
  This file is copied verbatim into runs/<run-id>/brainstorm/outline.md at run
  creation. Only the backend writes it. Each section body is replaced whole,
  between its anchor comment and the next; the front-matter `resolved` list is
  machine-maintained and is the single deterministic record of completeness.
-->
---
schema_version: 1
run_id: "WT-H2A8-H3"
title: "APS Markdown Conversion Service"
summary: "A cross-agency, ephemeral utility for public servants to convert diverse web and document formats into standardized Markdown using deterministic parsing."
created_at: "2026-07-18T06:17:32Z"
updated_at: "2026-07-18T06:22:14Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui", "constraints", "success_criteria"]
---

<!-- section: problem -->
## 1. Problem

Public servants often struggle with information trapped in poorly formatted PDFs, legacy web pages, or inconsistent document structures, making it difficult to index, search, or reuse content effectively.

<!-- section: solution -->
## 2. Proposed solution

A web-based conversion utility that accepts URLs or files and uses deterministic parsing libraries to transform content into standardized Markdown, avoiding LLM-based processing entirely.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

Primary users are public servants across all APS agencies; stakeholders include agency IT security teams who will need to vet the tool for cross-departmental data handling and compliance.

<!-- section: data -->
## 4. Data

The system processes public-facing web content and internal documents. To minimize risk, the architecture is designed to be ephemeral: data is processed in volatile memory and purged immediately upon completion, with no persistent storage of user-uploaded files or converted outputs.

<!-- section: happy_path -->
## 5. Happy path

A user pastes a URL into the tool, the system fetches the page, strips the navigation and ads, converts the core content to clean Markdown, and provides a download link.

<!-- section: alternatives -->
## 6. Alternatives considered

Manual re-typing, traditional web scraping scripts (BeautifulSoup), or off-the-shelf document conversion software like Pandoc.

<!-- section: ux_ui -->
## 7. UX and interface

A simple web interface with a single input field for a URL or file upload and a 'Convert' button.

<!-- section: constraints -->
## 8. Constraints and preferences

Must support cross-agency authentication; must implement strict data isolation; system is strictly ephemeral with no persistent storage, placing the burden of file retention on the user.

<!-- section: success_criteria -->
## 9. Success criteria

Success is defined by the tool providing a net positive utility for document conversion across the APS, accepting that occasional inaccuracies are an acceptable trade-off for speed and statelessness.
