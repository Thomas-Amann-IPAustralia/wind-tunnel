import { describe, expect, it } from "vitest";

import { parseOutline, SECTION_IDS, SECTION_REGISTRY } from "./outline";

// A canonical outline as the backend renders it (front-matter values are JSON,
// nine anchored sections). Two sections resolved; the rest carry the template's
// italic guidance and are unresolved.
const CANONICAL = `<!--
  Windtunnel project outline. Only the backend writes it.
-->
---
schema_version: 1
run_id: "WT-ABCD-EF"
title: "Enquiry Triage"
summary: "An AI assistant that triages enquiries."
created_at: "2026-07-16T00:00:00Z"
updated_at: "2026-07-16T00:00:00Z"
resolved: ["problem", "solution"]
---

<!-- section: problem -->
## 1. Problem

Citizens wait too long for replies.

<!-- section: solution -->
## 2. Proposed solution

An AI triage assistant.

<!-- section: users_stakeholders -->
## 3. Users and stakeholders

*Who uses it, and who is affected by it.*

<!-- section: data -->
## 4. Data

*What data it touches.*

<!-- section: happy_path -->
## 5. Happy path

*One ordinary, successful use.*

<!-- section: alternatives -->
## 6. Alternatives considered

*What else could solve this.*

<!-- section: ux_ui -->
## 7. UX and interface

*What the user sees.*

<!-- section: constraints -->
## 8. Constraints and preferences

*The hard limits.*

<!-- section: success_criteria -->
## 9. Success criteria

*How you'd know it worked.*
`;

describe("parseOutline", () => {
  it("reads the front-matter title/summary/resolved from the canonical form", () => {
    const outline = parseOutline(CANONICAL);
    expect(outline.title).toBe("Enquiry Triage");
    expect(outline.summary).toBe("An AI assistant that triages enquiries.");
    expect(outline.resolved).toEqual(["problem", "solution"]);
  });

  it("returns all nine sections in registry order with parsed bodies", () => {
    const outline = parseOutline(CANONICAL);
    expect(outline.sections.map((s) => s.id)).toEqual([...SECTION_IDS]);
    expect(outline.sections[0]).toMatchObject({ id: "problem", n: 1, title: "Problem" });
    expect(outline.sections[0].body).toBe("Citizens wait too long for replies.");
    expect(outline.sections[1].body).toBe("An AI triage assistant.");
    // The heading line is stripped; the guidance survives for the unresolved ones.
    expect(outline.sections[3].body).toBe("*What data it touches.*");
  });

  it("marks resolved from the front-matter list, never from body text", () => {
    const outline = parseOutline(CANONICAL);
    const resolvedIds = outline.sections.filter((s) => s.resolved).map((s) => s.id);
    expect(resolvedIds).toEqual(["problem", "solution"]);
  });

  it("sanitises an unknown id out of the resolved list", () => {
    const md = CANONICAL.replace('resolved: ["problem", "solution"]', 'resolved: ["problem", "x"]');
    expect(parseOutline(md).resolved).toEqual(["problem"]);
  });

  it("tolerates the raw template front-matter form (empty values with comments)", () => {
    const md = `---
schema_version: 1
run_id: ""            # set at run creation
title: ""             # short project title
summary: ""           # the concept in one sentence
resolved: []          # maintained by the backend
---

<!-- section: problem -->
## 1. Problem

*What problem is this solving?*
`;
    const outline = parseOutline(md);
    expect(outline.title).toBe("");
    expect(outline.summary).toBe("");
    expect(outline.resolved).toEqual([]);
    expect(outline.sections[0].resolved).toBe(false);
    expect(outline.sections).toHaveLength(9); // absent anchors still fill from the registry
  });

  it("falls back to empty, unresolved bodies when a section anchor is missing", () => {
    const md = `---
title: "T"
summary: "S"
resolved: ["problem"]
---

<!-- section: problem -->
## 1. Problem

Only this one is present.
`;
    const outline = parseOutline(md);
    expect(outline.sections).toHaveLength(9);
    expect(outline.sections[0].body).toBe("Only this one is present.");
    expect(outline.sections[1].body).toBe("");
    expect(outline.sections[1].resolved).toBe(false);
  });
});

describe("SECTION_REGISTRY", () => {
  it("mirrors the fixed nine-section contract in document order (§7.1)", () => {
    // This is the frontend copy of the backend SECTION_REGISTRY, which is itself
    // pinned to templates/outline.md by a backend test (§7.1). Pin the ids + order
    // here so a hand-mirroring slip is caught on this side too.
    expect(SECTION_IDS).toEqual([
      "problem",
      "solution",
      "users_stakeholders",
      "data",
      "happy_path",
      "alternatives",
      "ux_ui",
      "constraints",
      "success_criteria",
    ]);
    expect(SECTION_REGISTRY).toHaveLength(9);
    expect(SECTION_REGISTRY.map(([, title]) => title)).toEqual([
      "Problem",
      "Proposed solution",
      "Users and stakeholders",
      "Data",
      "Happy path",
      "Alternatives considered",
      "UX and interface",
      "Constraints and preferences",
      "Success criteria",
    ]);
  });
});
