import { useCallback, useEffect, useRef, useState } from "react";

import {
  allKbNodes,
  allNodes,
  EDGES,
  KB_EDGES,
  KB_H,
  KB_W,
  NODE_H,
  NODE_W,
  nodeById,
  kbNodeById,
  SPEC_JOIN_X,
  workspaceSize,
} from "../lib/topology";
import type { GraphNode, KbNode, NodeKind } from "../lib/topology";
import type { NodeState } from "../lib/types";
import "./PipelineGraph.css";

/**
 * The pipeline graph (design §7.2.1) — the spectacle: the machinery, laid out as a
 * node graph and lit as it works. This is the redesign's flagship: a pannable,
 * clickable canvas of the real pipeline (`lib/topology`), driven by the whole-graph
 * `nodes` map from one status poll (CLAUDE.md §3). Each stage is a card you can open
 * to read, in plain language, what it is and what it's doing right now.
 *
 * The **knowledge plane** rides alongside the specialist college: each specialist is
 * paired 1:1 with the knowledge base it reads from (KB_NODES), joined by a retrieval
 * wire. Those shelves are presentational — not status nodes — so their state is
 * derived from the paired specialist (still one poll). This is the PoC's most
 * important element restored: the user sees *which* body of authority grounds each
 * expert, and watches sources flow off the shelf as it reads.
 *
 * State is carried by **label + shape + position**, never colour alone (§9): every
 * node names its state in words and the activity log states every event in words
 * too, so the story survives reduced motion, a washed-out projector, and a screen
 * reader (§7.2.1). The wires and their flowing pulses are enhancement over that
 * substance, not the signal. `subActivity` is the node's genuine current work (the
 * document it's reading now, from real retrieval events) — the difference between a
 * trust instrument and a decorative spinner (§7.2.5).
 */

const STATE_LABEL: Record<NodeState, string> = {
  pending: "waiting",
  active: "working",
  waiting_user: "waiting on you",
  complete: "done",
  failed: "stopped",
};

type EdgeFlow = "pending" | "ready" | "flow" | "done";

/** How a wire reads, from the states of the two nodes it joins. `flow` is the live
 * handoff (work arriving at an active node); `ready` is a completed source whose
 * next stage hasn't begun; `done` is settled; `pending` is not yet reached. */
function edgeFlow(from: NodeState, to: NodeState): EdgeFlow {
  if (to === "active") return "flow";
  if (from === "complete" && to === "complete") return "done";
  if (from === "complete") return "ready";
  return "pending";
}

/** How a shelf reads, from its paired specialist's state: `serving` while the
 * specialist is actively reading, `read` once it's finished, else `idle`. */
type KbState = "idle" | "serving" | "read";
function kbState(specState: NodeState): KbState {
  if (specState === "active") return "serving";
  if (specState === "complete") return "read";
  return "idle";
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v));
}

// Chunk chips (the PoC's chunks flying off a shelf) ride the retrieval wire via
// CSS offset-path — enhancement only, gated on support and reduced motion.
const CHIP_OK =
  typeof CSS !== "undefined" && CSS.supports?.("offset-path", 'path("M 0 0 L 10 10")');

export function PipelineGraph({
  nodes,
  subActivity,
  selectedId,
  onSelect,
}: {
  nodes: Record<string, NodeState>;
  subActivity: Record<string, string>;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}) {
  const stageRef = useRef<HTMLDivElement>(null);
  const ws = workspaceSize();
  const [view, setView] = useState({ x: 0, y: 0, s: 1 });
  const drag = useRef<{ x: number; y: number; vx: number; vy: number; moved: number } | null>(null);

  const fit = useCallback(() => {
    const el = stageRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return; // no layout yet (or a headless test) — leave identity
    const pad = 48;
    const s = clamp(Math.min((r.width - pad) / ws.width, (r.height - pad) / ws.height), 0.25, 1.1);
    setView({
      s,
      x: (r.width - ws.width * s) / 2,
      y: Math.max((r.height - ws.height * s) / 2, 16),
    });
  }, [ws.width, ws.height]);

  // Fit on mount and whenever the stage resizes (ResizeObserver is absent in the
  // headless test env — guard it; the graph still renders, just unscaled).
  useEffect(() => {
    fit();
    const el = stageRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => fit());
    ro.observe(el);
    return () => ro.disconnect();
  }, [fit]);

  const zoomAt = useCallback((cx: number, cy: number, factor: number) => {
    setView((v) => {
      const ns = clamp(v.s * factor, 0.2, 1.8);
      const k = ns / v.s;
      return { s: ns, x: cx - (cx - v.x) * k, y: cy - (cy - v.y) * k };
    });
  }, []);

  const onWheel = useCallback(
    (e: React.WheelEvent) => {
      const el = stageRef.current;
      if (!el) return;
      e.preventDefault();
      const r = el.getBoundingClientRect();
      zoomAt(e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * 0.0012));
    },
    [zoomAt],
  );

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      // A press that starts on a node card is a selection, not a pan.
      if ((e.target as HTMLElement).closest(".wt-gnode")) return;
      drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, moved: 0 };
      (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
    },
    [view.x, view.y],
  );

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    const d = drag.current;
    if (!d) return;
    d.moved += Math.abs(e.movementX) + Math.abs(e.movementY);
    setView((v) => ({ ...v, x: d.vx + (e.clientX - d.x), y: d.vy + (e.clientY - d.y) }));
  }, []);

  const onPointerUp = useCallback(() => {
    const d = drag.current;
    drag.current = null;
    // A press that didn't move is a click on the background — deselect.
    if (d && d.moved < 4) onSelect(null);
  }, [onSelect]);

  return (
    <div className="wt-graph">
      <div
        className="wt-graph__stage"
        ref={stageRef}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div
          className="wt-graph__viewport"
          style={{
            width: ws.width,
            height: ws.height,
            transform: `translate(${view.x}px, ${view.y}px) scale(${view.s})`,
          }}
        >
          <GraphFrames />

          <svg
            className="wt-graph__wires"
            width={ws.width}
            height={ws.height}
            viewBox={`0 0 ${ws.width} ${ws.height}`}
            aria-hidden="true"
          >
            {EDGES.map((edge) => {
              const flow = edgeFlow(nodes[edge.from] ?? "pending", nodes[edge.to] ?? "pending");
              const d = edgePath(edge.from, edge.to);
              if (!d) return null;
              return (
                <g key={`${edge.from}->${edge.to}`}>
                  <path className={`wt-wire wt-wire--${flow}`} d={d} />
                  {flow === "flow" ? <path className="wt-wire__pulse" d={d} /> : null}
                </g>
              );
            })}
            {KB_EDGES.map((edge) => {
              const ks = kbState(nodes[edge.from] ?? "pending");
              const d = edgePath(edge.from, edge.to);
              if (!d) return null;
              return (
                <path
                  key={`${edge.from}~${edge.to}`}
                  className={`wt-kbwire wt-kbwire--${ks}`}
                  d={d}
                />
              );
            })}
          </svg>

          {/* Chunk chips fly off a shelf while its specialist reads — enhancement. */}
          {CHIP_OK ? (
            <div className="wt-graph__chips" aria-hidden="true">
              {KB_EDGES.map((edge) => {
                if (kbState(nodes[edge.from] ?? "pending") !== "serving") return null;
                if (!subActivity[edge.from]) return null;
                const d = edgePath(edge.from, edge.to);
                if (!d) return null;
                return (
                  <span key={edge.to} className="wt-chip" style={{ offsetPath: `path("${d}")` }} />
                );
              })}
            </div>
          ) : null}

          {allNodes().map((node) => (
            <NodeCard
              key={node.id}
              node={node}
              state={nodes[node.id] ?? "pending"}
              subActivity={subActivity[node.id]}
              selected={selectedId === node.id}
              onSelect={onSelect}
            />
          ))}

          {allKbNodes().map((kb) => (
            <KbCard
              key={kb.id}
              kb={kb}
              state={kbState(nodes[kb.specialistId] ?? "pending")}
              selected={selectedId === kb.id}
              onSelect={onSelect}
            />
          ))}
        </div>

        <div className="wt-graph__controls" aria-hidden="false">
          <button
            type="button"
            className="wt-graph__ctl"
            onClick={() => setView((v) => ({ ...v, s: clamp(v.s * 0.8, 0.2, 1.8) }))}
            aria-label="Zoom out"
          >
            −
          </button>
          <span className="wt-graph__zoom wt-mono">{Math.round(view.s * 100)}%</span>
          <button
            type="button"
            className="wt-graph__ctl"
            onClick={() => setView((v) => ({ ...v, s: clamp(v.s * 1.25, 0.2, 1.8) }))}
            aria-label="Zoom in"
          >
            +
          </button>
          <button type="button" className="wt-graph__ctl" onClick={fit} aria-label="Fit to view">
            Fit
          </button>
        </div>
      </div>

      <p className="wt-graph__hint">
        Drag to move around, scroll to zoom, and select any stage — or a knowledge base — to see, in
        plain terms, what it is and what it&rsquo;s doing.
      </p>
    </div>
  );
}

/** Faint group frames + captions behind the nodes — the PoC's labelled structure:
 * the two phases, and the college with its knowledge plane. Pure layout chrome. */
function GraphFrames() {
  const specs = allKbNodes();
  const kbLeft = specs[0]?.pos.x ?? 0;
  const collegeNodes = allNodes().filter((n) => n.id.startsWith("full.specialist."));
  const collegeLeft = Math.min(...collegeNodes.map((n) => n.pos.x));
  const collegeTop = Math.min(...collegeNodes.map((n) => n.pos.y));
  const collegeRight = kbLeft + KB_W;
  const collegeBottom = Math.max(...specs.map((n) => n.pos.y + KB_H));
  const pad = 26;
  return (
    <div className="wt-graph__frames" aria-hidden="true">
      <div
        className="wt-graph__group"
        style={{
          left: collegeLeft - pad,
          top: collegeTop - pad - 8,
          width: collegeRight - collegeLeft + pad * 2,
          height: collegeBottom - collegeTop + pad * 2 + 8,
        }}
      >
        <span className="wt-graph__group-label">The specialist college · knowledge plane</span>
      </div>
      <span className="wt-graph__phase" style={{ left: 0, top: -44 }}>
        Threshold assessment
      </span>
      <span className="wt-graph__phase" style={{ left: collegeLeft - pad, top: -44 }}>
        Full assessment
      </span>
    </div>
  );
}

/** The rectangle a wire endpoint anchors to — a pipeline node or a shelf. Anchors
 * to the fixed card footprint (never measured), so wires are deterministic. */
function rectOf(id: string): { x: number; y: number; w: number; h: number } | null {
  const n = nodeById(id);
  if (n) return { x: n.pos.x, y: n.pos.y, w: NODE_W, h: NODE_H };
  const k = kbNodeById(id);
  if (k) return { x: k.pos.x, y: k.pos.y, w: KB_W, h: KB_H };
  return null;
}

/** The cubic path for a wire: right-centre of the source to left-centre of the
 * target. A specialist's onward handoff to the checkpoint first runs horizontally
 * past the knowledge plane (to SPEC_JOIN_X) so it clears the shelves, then curves —
 * the PoC's routing. Everything else is a plain right-to-left cubic. */
function edgePath(fromId: string, toId: string): string | null {
  const a = rectOf(fromId);
  const b = rectOf(toId);
  if (!a || !b) return null;
  const x0 = a.x + a.w;
  const y0 = a.y + a.h / 2;
  const x1 = b.x;
  const y1 = b.y + b.h / 2;
  if (fromId.startsWith("full.specialist.") && toId === "full.checkpoint") {
    const c = 120;
    return `M ${x0} ${y0} L ${SPEC_JOIN_X} ${y0} C ${SPEC_JOIN_X + c} ${y0}, ${x1 - c} ${y1}, ${x1} ${y1}`;
  }
  const dx = Math.max(Math.abs(x1 - x0) * 0.5, 60);
  return `M ${x0} ${y0} C ${x0 + dx} ${y0}, ${x1 - dx} ${y1}, ${x1} ${y1}`;
}

/** A small inline icon per node kind — a visual anchor for the lay reader (the PoC
 * gives every node an icon). Decorative; the name and state word carry meaning. */
function NodeIcon({ kind }: { kind: NodeKind | "kb" }) {
  const common = {
    width: 13,
    height: 13,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  switch (kind) {
    case "compute": // deterministic engine — a waveform/gears cue
      return (
        <svg {...common}>
          <path d="M4 17V7l6 5 6-5v10" />
          <path d="M20 7v10" />
        </svg>
      );
    case "pause": // the human checkpoint — a person
      return (
        <svg {...common}>
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5" />
        </svg>
      );
    case "kb": // a corpus — a database cylinder
      return (
        <svg {...common}>
          <ellipse cx="12" cy="5.5" rx="8" ry="3" />
          <path d="M4 5.5v13c0 1.7 3.6 3 8 3s8-1.3 8-3v-13" />
          <path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />
        </svg>
      );
    default: // an AI agent/specialist — a node square
      return (
        <svg {...common}>
          <rect x="5" y="5" width="14" height="14" rx="3" />
          <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
        </svg>
      );
  }
}

function NodeCard({
  node,
  state,
  subActivity,
  selected,
  onSelect,
}: {
  node: GraphNode;
  state: NodeState;
  subActivity?: string;
  selected: boolean;
  onSelect: (id: string | null) => void;
}) {
  return (
    <button
      type="button"
      className={`wt-gnode wt-gnode--${state} wt-gnode--${node.kind}${selected ? " is-selected" : ""}`}
      style={{ left: node.pos.x, top: node.pos.y, width: NODE_W, height: NODE_H }}
      data-state={state}
      aria-pressed={selected}
      aria-label={`${node.friendly} — ${STATE_LABEL[state]}. ${node.blurb} Select for detail.`}
      onClick={() => onSelect(selected ? null : node.id)}
    >
      <span className="wt-gnode__strip" aria-hidden="true" />
      <span className="wt-gnode__head">
        <span className="wt-gnode__ico" aria-hidden="true">
          <NodeIcon kind={node.kind} />
        </span>
        <span className="wt-gnode__name">{node.friendly}</span>
        <span className="wt-gnode__state">{STATE_LABEL[state]}</span>
      </span>
      <span className="wt-gnode__blurb">{node.blurb}</span>
      <span className="wt-gnode__foot">
        {state === "active" && subActivity ? (
          <span className="wt-gnode__sub">{subActivity}</span>
        ) : node.kind === "compute" ? (
          <span className="wt-gnode__kind">computed, not judged</span>
        ) : (
          <span className="wt-gnode__engine">{node.engine}</span>
        )}
      </span>
    </button>
  );
}

const KB_STATE_LABEL: Record<KbState, string> = {
  idle: "not read yet",
  serving: "being read",
  read: "read",
};

function KbCard({
  kb,
  state,
  selected,
  onSelect,
}: {
  kb: KbNode;
  state: KbState;
  selected: boolean;
  onSelect: (id: string | null) => void;
}) {
  return (
    <button
      type="button"
      className={`wt-gnode wt-kbnode wt-kbnode--${state}${selected ? " is-selected" : ""}`}
      style={{ left: kb.pos.x, top: kb.pos.y, width: KB_W, height: KB_H }}
      data-state={state}
      aria-pressed={selected}
      aria-label={`${kb.friendly} — a knowledge base, ${KB_STATE_LABEL[state]}. ${kb.blurb} Select for detail.`}
      onClick={() => onSelect(selected ? null : kb.id)}
    >
      <span className="wt-gnode__strip" aria-hidden="true" />
      <span className="wt-gnode__head">
        <span className="wt-gnode__ico" aria-hidden="true">
          <NodeIcon kind="kb" />
        </span>
        <span className="wt-gnode__name">{kb.friendly}</span>
        <span className="wt-kbnode__state">{KB_STATE_LABEL[state]}</span>
      </span>
      <span className="wt-kbnode__foot wt-mono">{kb.docCount} sources · knowledge base</span>
    </button>
  );
}
