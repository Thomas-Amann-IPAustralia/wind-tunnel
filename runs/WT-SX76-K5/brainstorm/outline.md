<!--
  Windtunnel project outline. Contract: TECH_SPEC.md §7.1.
  This file is copied verbatim into runs/<run-id>/brainstorm/outline.md at run
  creation. Only the backend writes it. Each section body is replaced whole,
  between its anchor comment and the next; the front-matter `resolved` list is
  machine-maintained and is the single deterministic record of completeness.
-->
---
schema_version: 1
run_id: "WT-SX76-K5"
title: "Legacy Code Modernization Assistant"
summary: "An AI-driven, platform-agnostic tool to analyze, document, and map legacy software systems to accelerate modernization and security compliance."
created_at: "2026-07-29T23:53:46Z"
updated_at: "2026-07-30T00:00:02Z"
resolved: ["problem", "solution", "users_stakeholders", "data", "happy_path", "alternatives", "ux_ui", "constraints"]
---

<!-- section: problem -->
## 1. Problem

Government agencies are burdened by opaque, undocumented legacy software systems that are difficult to maintain, secure, or integrate with modern services.

<!-- section: solution -->
## 2. Proposed solution

A sovereign AI-powered analysis tool that ingests legacy source code to generate documentation, identify modular components for abstraction, and produce Software Bills of Materials (SBOMs) to guide modernization efforts.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

Primary users are software engineers and system architects within government IT departments; stakeholders include security officers, procurement leads, and the public who rely on the stability of these services.

<!-- section: data -->
## 4. Data

The system will process proprietary legacy source code, configuration files, and existing technical documentation. This data is highly sensitive and must remain within a sovereign, air-gapped or highly secure environment.

<!-- section: happy_path -->
## 5. Happy path

A developer runs the CLI tool against a legacy repository, which ingests the code and maps its internal dependencies. The developer then opens the web dashboard to view a visual dependency graph, where the AI has highlighted a specific, isolated module as a candidate for extraction. The developer uses the CLI to generate a refactoring plan and a corresponding SBOM for that module, allowing them to proceed with modernization while maintaining security compliance.

<!-- section: alternatives -->
## 6. Alternatives considered

Manual code audits by external consultants, static analysis tools (non-AI), or complete system replacement (rip-and-replace) which is often cost-prohibitive.

<!-- section: ux_ui -->
## 7. UX and interface

The interface will be a developer-focused CLI for ingestion and analysis, paired with a web-based dashboard for visualizing system architecture, dependency maps, and generated documentation.

<!-- section: constraints -->
## 8. Constraints and preferences

The system must be platform-agnostic, supporting a wide range of legacy languages, and must operate entirely within a sovereign, air-gapped environment to ensure data security.

<!-- section: success_criteria -->
## 9. Success criteria

*How you'd know, six months in, that it worked.*
