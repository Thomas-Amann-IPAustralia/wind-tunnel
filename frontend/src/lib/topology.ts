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
 *
 * Beyond the id/name/kind mirror this module also carries the **spatial layout**
 * (node positions + the wires between them) and a **plain-language explanation**
 * per node. The Chamber renders these as a node graph a lay reader can click
 * through — the point of the redesign is transparency: showing *how the machine
 * works* in words a non-engineer follows (the design's flagship, §7.2). The
 * positions/edges are static layout data (no DOM measurement), so the wires are
 * deterministic and render identically in every environment. The explanatory copy
 * is descriptive only — the machine-checkable specialist↔section map still lives in
 * `instrument/sections.json`; nothing here is a second authority for it.
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
  /** Workspace position (top-left, in layout px) — static, never measured. */
  pos: { x: number; y: number };
  /** The tool behind the node, in lay terms — which model tier, or "code". */
  engine: string;
  /** One line: what this node does, plainly. */
  blurb: string;
  /** A short paragraph a non-engineer can follow: what it does and why it matters. */
  explain: string;
  /** What part of the assessment it is responsible for (descriptive, not the map). */
  owns?: string;
}

/** A wire between two nodes — a handoff in the pipeline (the flow grammar §3.5). */
export interface GraphEdge {
  from: string;
  to: string;
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

/** Card footprint (kept in sync with PipelineGraph.css) — the wire maths anchors
 * to the fixed centre of each card, so the height is fixed and the sub-activity
 * slot is always reserved (the card never resizes as work streams in). */
export const NODE_W = 244;
export const NODE_H = 122;

// The two lay-audience model tiers actually used in governance (config/models.yml):
// flash drafts fast; pro reasons deeply. Deterministic nodes run no model at all —
// the load-bearing "code computes" honesty (CLAUDE.md §3).
const FAST = "Fast drafting model";
const DEEP = "Deep-reasoning model";
const CODE = "Fixed rules — no AI";

const SPECIALISTS: ReadonlyArray<{
  id: string;
  friendly: string;
  blurb: string;
  owns: string;
}> = [
  {
    id: "it_security",
    friendly: "IT Security specialist",
    blurb: "Security controls and AI-specific threats.",
    owns: "Security posture, incidents, threat surface",
  },
  {
    id: "privacy",
    friendly: "Privacy specialist",
    blurb: "Personal information and Privacy Act / APP obligations.",
    owns: "Privacy and personal-information handling",
  },
  {
    id: "ethics",
    friendly: "Ethics & Fairness specialist",
    blurb: "Fairness, transparency and contestability.",
    owns: "AI ethics principles, explainability, human values",
  },
  {
    id: "legal",
    friendly: "Legal & Administrative Law specialist",
    blurb: "Administrative law, decision safeguards, records.",
    owns: "Legal authority, review rights, accountability",
  },
  {
    id: "data_governance",
    friendly: "Data Governance specialist",
    blurb: "Data lineage, retention and metadata standards.",
    owns: "Data sourcing, quality, retention",
  },
  {
    id: "solution_architect",
    friendly: "Solution Architect (sections)",
    blurb: "Hosting, patterns, failure modes and monitoring.",
    owns: "Solution design and operational sections",
  },
];

// -- layout grid ---------------------------------------------------------------
// Left-to-right flow, matching the real pipeline: the two threshold assessors →
// reconciler → rating engine, then the engine blooms into the six-specialist
// college → checkpoint → architect → reviewer → assembly. Columns are pitched so
// wires read as unambiguous handoffs; the specialist column spreads vertically so
// the "bloom" fans out from a single point (§7.2.2).
const COL = {
  intake: 0,
  reconcile: 300,
  rating: 600,
  spec: 920,
  check: 1240,
  arch: 1540,
  rev: 1840,
  asm: 2140,
};
const SPEC_Y0 = 20;
const SPEC_PITCH = 132;
const specY = (i: number) => SPEC_Y0 + i * SPEC_PITCH;
// Centre of the specialist column, so the threshold lane and the tail align to it.
const MID_Y = (specY(0) + specY(SPECIALISTS.length - 1)) / 2;

export const TOPOLOGY: readonly Band[] = [
  {
    key: "threshold",
    title: "Threshold assessment",
    clusters: [
      {
        layout: "parallel",
        label: "Two independent assessors, drafting in parallel",
        nodes: [
          {
            id: "threshold.generalist_a",
            friendly: "Assessor A",
            kind: "llm",
            pos: { x: COL.intake, y: MID_Y - 96 },
            engine: FAST,
            blurb: "First independent read of your idea.",
            explain:
              "One of two assessors that read your submission fresh and, on their own, draft a first-pass view of how risky the idea is. Two of them work separately so a second opinion can genuinely disagree with the first.",
            owns: "Draft of sections 1–4",
          },
          {
            id: "threshold.generalist_b",
            friendly: "Assessor B",
            kind: "llm",
            pos: { x: COL.intake, y: MID_Y + 96 },
            engine: FAST,
            blurb: "Second independent read of your idea.",
            explain:
              "The second of two independent assessors. It never sees the first one's answers, so when the two agree that agreement means something — and where they differ, the reconciler has to resolve it.",
            owns: "Draft of sections 1–4",
          },
        ],
      },
      {
        layout: "single",
        nodes: [
          {
            id: "threshold.reconciler",
            friendly: "Reconciler",
            kind: "llm",
            pos: { x: COL.reconcile, y: MID_Y },
            engine: DEEP,
            blurb: "Merges both reads into one agreed view.",
            explain:
              "Reads both assessors' drafts side by side. Where they disagree it takes the more cautious reading and records the disagreement, then writes a single agreed threshold view. It settles the wording — it never sets the risk rating.",
            owns: "Final sections 1–4",
          },
        ],
      },
      {
        layout: "single",
        nodes: [
          {
            id: "threshold.rating_engine",
            friendly: "Rating engine",
            kind: "compute",
            pos: { x: COL.rating, y: MID_Y },
            engine: CODE,
            blurb: "Turns the agreed answers into risk ratings.",
            explain:
              "This is not an AI. It is plain, fixed rules that turn the agreed consequence and likelihood into a risk rating the same way every time. The models argue; the code computes — so the ratings can't be talked into a softer result.",
            owns: "Computed ratings 3.1–3.9",
          },
        ],
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
        nodes: SPECIALISTS.map((s, i) => ({
          id: `full.specialist.${s.id}`,
          friendly: s.friendly,
          kind: "llm" as const,
          pos: { x: COL.spec, y: specY(i) },
          engine: FAST,
          blurb: s.blurb,
          explain: `Reads its own shelf of official government sources and drafts the parts of the assessment it owns — ${s.blurb.toLowerCase().replace(/\.$/, "")}. Every finding it makes has to cite the source it came from, so nothing is asserted without a reference.`,
          owns: s.owns,
        })),
      },
      {
        layout: "single",
        nodes: [
          {
            id: "full.checkpoint",
            friendly: "Question checkpoint",
            kind: "pause",
            pos: { x: COL.check, y: MID_Y },
            engine: "Waits for you",
            blurb: "Where the specialists pause to ask you anything.",
            explain:
              "The one place the run stops for you. If a specialist couldn't safely assume something about your idea, it asks here. You answer what you can and skip the rest — anything you skip is written up honestly as a gap, never guessed.",
            owns: "Your answers",
          },
        ],
      },
      {
        layout: "single",
        nodes: [
          {
            id: "full.architect",
            friendly: "Solution Architect (appendix)",
            kind: "llm",
            pos: { x: COL.arch, y: MID_Y },
            engine: DEEP,
            blurb: "Writes the implementation-plan appendix.",
            explain:
              "Once every specialist is finished, this pass writes the implementation-plan appendix — a grounded picture of how the idea would actually be built, hosted and run, drawing on everything the specialists found.",
            owns: "Implementation Plan appendix",
          },
        ],
      },
      {
        layout: "single",
        nodes: [
          {
            id: "full.reviewer",
            friendly: "Adjudicating reviewer",
            kind: "llm",
            pos: { x: COL.rev, y: MID_Y },
            engine: DEEP,
            blurb: "Checks the whole draft holds together.",
            explain:
              "Reads the assembled draft for coverage and coherence — did every section get answered, does it hang together, is anything contradictory. It can send a fix back to a specialist, and it computes the residual risk once mitigations are in.",
            owns: "Coverage, coherence, residual risk",
          },
        ],
      },
      {
        layout: "single",
        nodes: [
          {
            id: "full.assembly",
            friendly: "Assembly",
            kind: "compute",
            pos: { x: COL.asm, y: MID_Y },
            engine: CODE,
            blurb: "Builds the final report.",
            explain:
              "Not an AI either. It gathers every signed-off section, its citations and the computed ratings and assembles them into the notebook and the HTML report you finish with — nothing added, nothing rephrased.",
            owns: "Notebook + HTML report",
          },
        ],
      },
    ],
  },
];

/** The wires between nodes, in the pipeline's real handoff order. Each phase's
 * intra-flow, plus the bloom from the rating engine into the specialist college
 * and the fan back in to the checkpoint (the two parallel moments, §7.2.2). */
export const EDGES: readonly GraphEdge[] = [
  { from: "threshold.generalist_a", to: "threshold.reconciler" },
  { from: "threshold.generalist_b", to: "threshold.reconciler" },
  { from: "threshold.reconciler", to: "threshold.rating_engine" },
  ...SPECIALISTS.map((s) => ({
    from: "threshold.rating_engine",
    to: `full.specialist.${s.id}`,
  })),
  ...SPECIALISTS.map((s) => ({
    from: `full.specialist.${s.id}`,
    to: "full.checkpoint",
  })),
  { from: "full.checkpoint", to: "full.architect" },
  { from: "full.architect", to: "full.reviewer" },
  { from: "full.reviewer", to: "full.assembly" },
];

/** Every node id in graph order — the complete key set of `status.json.nodes`. */
export function allNodeIds(): string[] {
  return TOPOLOGY.flatMap((b) => b.clusters.flatMap((c) => c.nodes.map((n) => n.id)));
}

/** Every node, in graph order — the flat list the canvas positions and wires. */
export function allNodes(): GraphNode[] {
  return TOPOLOGY.flatMap((b) => b.clusters.flatMap((c) => c.nodes));
}

/** The node record for an id, or undefined for an unknown id. */
export function nodeById(id: string): GraphNode | undefined {
  return allNodes().find((n) => n.id === id);
}

/** The overall workspace size the layout occupies (for the canvas viewport). */
export function workspaceSize(): { width: number; height: number } {
  const nodes = allNodes();
  const width = Math.max(...nodes.map((n) => n.pos.x + NODE_W));
  const height = Math.max(...nodes.map((n) => n.pos.y + NODE_H));
  return { width, height };
}

/** The friendly name for a node id (falls back to the id — the log may carry an
 * `agent` that is already a friendly name, so this is only a best-effort lookup). */
export function friendlyFor(nodeId: string): string {
  return nodeById(nodeId)?.friendly ?? nodeId;
}
