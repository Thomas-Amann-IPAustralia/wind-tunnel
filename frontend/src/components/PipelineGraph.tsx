import { useCallback, useEffect, useRef, useState } from "react";

import { allNodes, EDGES, NODE_H, NODE_W, nodeById, workspaceSize } from "../lib/topology";
import type { GraphNode } from "../lib/topology";
import type { NodeState } from "../lib/types";
import "./PipelineGraph.css";

/**
 * The pipeline graph (design §7.2.1) — the spectacle: the machinery, laid out as a
 * node graph and lit as it works. This is the redesign's flagship: a pannable,
 * clickable canvas of the real pipeline (`lib/topology`), driven by the whole-graph
 * `nodes` map from one status poll (CLAUDE.md §3). Each stage is a card you can open
 * to read, in plain language, what it is and what it's doing right now.
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

function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v));
}

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
          <svg
            className="wt-graph__wires"
            width={ws.width}
            height={ws.height}
            viewBox={`0 0 ${ws.width} ${ws.height}`}
            aria-hidden="true"
          >
            {EDGES.map((edge) => {
              const flow = edgeFlow(nodes[edge.from] ?? "pending", nodes[edge.to] ?? "pending");
              const d = wirePath(edge.from, edge.to);
              if (!d) return null;
              return (
                <g key={`${edge.from}->${edge.to}`}>
                  <path className={`wt-wire wt-wire--${flow}`} d={d} />
                  {flow === "flow" ? <path className="wt-wire__pulse" d={d} /> : null}
                </g>
              );
            })}
          </svg>

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
        Drag to move around, scroll to zoom, and select any stage to see — in plain terms — what it
        is and what it&rsquo;s doing.
      </p>
    </div>
  );
}

/** The cubic path for a wire: right-centre of the source to left-centre of the
 * target. Anchors to the fixed card footprint (never measured), so wires are
 * deterministic across environments. */
function wirePath(fromId: string, toId: string): string | null {
  const a = nodeById(fromId);
  const b = nodeById(toId);
  if (!a || !b) return null;
  const x0 = a.pos.x + NODE_W;
  const y0 = a.pos.y + NODE_H / 2;
  const x1 = b.pos.x;
  const y1 = b.pos.y + NODE_H / 2;
  const dx = Math.max(Math.abs(x1 - x0) * 0.5, 60);
  return `M ${x0} ${y0} C ${x0 + dx} ${y0}, ${x1 - dx} ${y1}, ${x1} ${y1}`;
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
        <span className="wt-gnode__dot" aria-hidden="true" />
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
