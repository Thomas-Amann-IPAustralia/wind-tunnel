import { describe, expect, it } from "vitest";

import { allNodeIds, friendlyFor, TOPOLOGY } from "./topology";

// Pins the topology to the ids `pipeline/status.py` `_node_specs()` owns, in graph
// order (design §7.2.6). If the pipeline adds/renames/reorders a node, this test
// fails until the mirror is updated — the same drift guard runCode.test.ts gives
// the run-code format. The animation is pre-scripted to exactly these ids.
const EXPECTED_IDS = [
  "threshold.generalist_a",
  "threshold.generalist_b",
  "threshold.reconciler",
  "threshold.rating_engine",
  "full.specialist.it_security",
  "full.specialist.privacy",
  "full.specialist.ethics",
  "full.specialist.legal",
  "full.specialist.data_governance",
  "full.specialist.solution_architect",
  "full.checkpoint",
  "full.architect",
  "full.reviewer",
  "full.assembly",
];

describe("topology", () => {
  it("mirrors the fixed status.py node ids in graph order", () => {
    expect(allNodeIds()).toEqual(EXPECTED_IDS);
  });

  it("has no duplicate node ids", () => {
    const ids = allNodeIds();
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("bloom clusters are parallel (the two generalists, the six specialists)", () => {
    const parallel = TOPOLOGY.flatMap((b) => b.clusters).filter((c) => c.layout === "parallel");
    expect(parallel.map((c) => c.nodes.length)).toEqual([2, 6]);
    // Each parallel cluster carries a plain caption (§7.2.1 "no event only in graph").
    expect(parallel.every((c) => typeof c.label === "string" && c.label.length > 0)).toBe(true);
  });

  it("resolves a friendly name and falls back to the id for an unknown node", () => {
    expect(friendlyFor("threshold.rating_engine")).toBe("Rating engine");
    expect(friendlyFor("full.specialist.privacy")).toBe("Privacy specialist");
    expect(friendlyFor("nonexistent.node")).toBe("nonexistent.node");
  });

  it("marks the deterministic nodes as compute and the checkpoint as a pause", () => {
    const byId = Object.fromEntries(
      TOPOLOGY.flatMap((b) => b.clusters).flatMap((c) => c.nodes.map((n) => [n.id, n.kind])),
    );
    expect(byId["threshold.rating_engine"]).toBe("compute");
    expect(byId["full.assembly"]).toBe("compute");
    expect(byId["full.checkpoint"]).toBe("pause");
    expect(byId["full.specialist.privacy"]).toBe("llm");
  });
});
