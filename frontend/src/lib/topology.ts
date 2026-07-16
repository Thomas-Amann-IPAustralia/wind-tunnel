/**
 * The fixed pipeline topology the Chamber animation is pre-scripted against
 * (design §7.2, §7.2.6). Node ids and friendly names are **mirrored by hand** from
 * `pipeline/status.py` `_node_specs()` — the one owner of the topology — exactly as
 * `runCode.ts` mirrors `runcode.py` and `outline.ts` mirrors the section registry.
 * `topology.test.ts` pins the id set so it can't drift from that owner silently.
 *
 * The animation "already knows the whole map; events light it up" (§7.2): a single
 * status poll sets every node's state, and one poll fully determines the visible
 * graph (CLAUDE.md §3). Nothing here fetches or computes — it is pure layout data.
 */

/** How a node reads in the graph. `compute` nodes (rating engine, assembly) are
 * shown as deterministic — the quiet "models argue, code computes" cue (§7.2.2
 * beat 4); `pause` is the checkpoint that can go amber; `llm` nodes pulse when
 * active. */
export type NodeKind = "llm" | "compute" | "pause";

export interface GraphNode {
  id: string; // the status.json node id, verbatim
  friendly: string; // the design-facing name (status.py friendly)
  kind: NodeKind;
}

/** A row in a band: either one node, or a set that goes active *together* — the
 * two generalists in parallel, and the six-specialist "bloom" (§7.2.2 beats 2/6). */
export interface Cluster {
  layout: "single" | "parallel";
  label?: string; // the plain caption the design gives a parallel cluster
  nodes: GraphNode[];
}

export interface Band {
  key: "threshold" | "full";
  title: string;
  clusters: Cluster[];
}

const SPECIALISTS: ReadonlyArray<[string, string]> = [
  ["it_security", "IT Security specialist"],
  ["privacy", "Privacy specialist"],
  ["ethics", "Ethics & Fairness specialist"],
  ["legal", "Legal & Administrative Law specialist"],
  ["data_governance", "Data Governance specialist"],
  ["solution_architect", "Solution Architect (sections)"],
];

export const TOPOLOGY: readonly Band[] = [
  {
    key: "threshold",
    title: "Threshold assessment",
    clusters: [
      {
        layout: "parallel",
        label: "Two independent assessors, drafting in parallel",
        nodes: [
          { id: "threshold.generalist_a", friendly: "Assessor A", kind: "llm" },
          { id: "threshold.generalist_b", friendly: "Assessor B", kind: "llm" },
        ],
      },
      {
        layout: "single",
        nodes: [{ id: "threshold.reconciler", friendly: "Reconciler", kind: "llm" }],
      },
      {
        layout: "single",
        nodes: [{ id: "threshold.rating_engine", friendly: "Rating engine", kind: "compute" }],
      },
    ],
  },
  {
    key: "full",
    title: "Full assessment",
    clusters: [
      {
        layout: "parallel",
        label: "The specialist college — six experts, each reading its own sources",
        nodes: SPECIALISTS.map(([id, friendly]) => ({
          id: `full.specialist.${id}`,
          friendly,
          kind: "llm" as const,
        })),
      },
      {
        layout: "single",
        nodes: [{ id: "full.checkpoint", friendly: "Question checkpoint", kind: "pause" }],
      },
      {
        layout: "single",
        nodes: [{ id: "full.architect", friendly: "Solution Architect (appendix)", kind: "llm" }],
      },
      {
        layout: "single",
        nodes: [{ id: "full.reviewer", friendly: "Adjudicating reviewer", kind: "llm" }],
      },
      {
        layout: "single",
        nodes: [{ id: "full.assembly", friendly: "Assembly", kind: "compute" }],
      },
    ],
  },
];

/** Every node id in graph order — the complete key set of `status.json.nodes`. */
export function allNodeIds(): string[] {
  return TOPOLOGY.flatMap((b) => b.clusters.flatMap((c) => c.nodes.map((n) => n.id)));
}

/** The friendly name for a node id (falls back to the id — the log may carry an
 * `agent` that is already a friendly name, so this is only a best-effort lookup). */
export function friendlyFor(nodeId: string): string {
  for (const band of TOPOLOGY) {
    for (const cluster of band.clusters) {
      for (const node of cluster.nodes) {
        if (node.id === nodeId) return node.friendly;
      }
    }
  }
  return nodeId;
}
