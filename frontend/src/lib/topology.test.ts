import { describe, expect, it } from "vitest";

import {
  allKbNodes,
  allNodeIds,
  allNodes,
  EDGES,
  friendlyFor,
  KB_EDGES,
  kbForSpecialist,
  nodeById,
  TOPOLOGY,
  workspaceSize,
} from "./topology";

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

  it("gives every node a position and lay-audience copy", () => {
    for (const node of allNodes()) {
      expect(Number.isFinite(node.pos.x)).toBe(true);
      expect(Number.isFinite(node.pos.y)).toBe(true);
      expect(node.engine.length).toBeGreaterThan(0);
      expect(node.blurb.length).toBeGreaterThan(0);
      // The explanation is the transparency payload — a real sentence, not a stub.
      expect(node.explain.length).toBeGreaterThan(40);
    }
  });

  it("wires only real nodes, and covers the pipeline's real handoffs", () => {
    const ids = new Set(allNodeIds());
    for (const e of EDGES) {
      expect(ids.has(e.from)).toBe(true);
      expect(ids.has(e.to)).toBe(true);
    }
    // The two parallel moments: two generalists → reconciler, and the six-specialist
    // bloom from the rating engine (§7.2.2).
    expect(EDGES.filter((e) => e.to === "threshold.reconciler")).toHaveLength(2);
    expect(EDGES.filter((e) => e.from === "threshold.rating_engine")).toHaveLength(6);
    expect(EDGES.filter((e) => e.to === "full.checkpoint")).toHaveLength(6);
  });

  it("computes a workspace that contains every node", () => {
    const { width, height } = workspaceSize();
    expect(width).toBeGreaterThan(0);
    expect(height).toBeGreaterThan(0);
    expect(nodeById("full.assembly")?.pos.x).toBeLessThanOrEqual(width);
  });
});

describe("knowledge plane", () => {
  const SPECIALIST_IDS = [
    "full.specialist.it_security",
    "full.specialist.privacy",
    "full.specialist.ethics",
    "full.specialist.legal",
    "full.specialist.data_governance",
    "full.specialist.solution_architect",
  ];

  it("pairs one knowledge base 1:1 with each drafting specialist", () => {
    const kb = allKbNodes();
    expect(kb.map((k) => k.specialistId)).toEqual(SPECIALIST_IDS);
    // Each shelf keys off a real specialist node id (not a status node itself).
    for (const k of kb) {
      expect(k.id).toBe(`kb.${k.specialistId.replace("full.specialist.", "")}`);
      expect(nodeById(k.specialistId)?.kind).toBe("llm");
    }
  });

  it("keeps shelves out of the status-node id set", () => {
    // Presentational only — a shelf must never appear in status.json `nodes`.
    const statusIds = new Set(allNodeIds());
    for (const k of allKbNodes()) expect(statusIds.has(k.id)).toBe(false);
  });

  it("wires each specialist to exactly its own shelf", () => {
    expect(KB_EDGES).toHaveLength(6);
    for (const e of KB_EDGES) {
      const kb = kbForSpecialist(e.from);
      expect(kb).toBeDefined();
      expect(e.to).toBe(kb?.id);
    }
  });

  it("gives every shelf lay-audience copy and a real document count", () => {
    for (const k of allKbNodes()) {
      expect(k.blurb.length).toBeGreaterThan(0);
      expect(k.contains.length).toBeGreaterThan(0);
      expect(k.explain.length).toBeGreaterThan(40);
      expect(k.docCount).toBeGreaterThan(0);
    }
  });

  it("includes the shelves in the workspace footprint", () => {
    const { width } = workspaceSize();
    for (const k of allKbNodes()) expect(k.pos.x).toBeLessThanOrEqual(width);
  });
});
