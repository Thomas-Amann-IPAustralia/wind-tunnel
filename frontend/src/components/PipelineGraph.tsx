import { TOPOLOGY } from "../lib/topology";
import type { GraphNode } from "../lib/topology";
import type { NodeState } from "../lib/types";
import "./PipelineGraph.css";

/**
 * The pipeline graph (design §7.2.1) — the spectacle: the machinery, lit as it
 * works. Pre-scripted to the fixed topology (`lib/topology`), driven by the
 * whole-graph `nodes` map from one status poll. State is carried by **label +
 * shape + position**, never colour alone (§9): every node names its state in text
 * and every event the graph shows the activity log states in words too, so the
 * story survives reduced motion and a washed-out projector (§7.2.1).
 *
 * `subActivity` is the node's genuine current sub-activity (the document it is
 * reading right now, from real retrieval events) — the difference between a trust
 * instrument and a decorative spinner (§7.2.5).
 */
const STATE_LABEL: Record<NodeState, string> = {
  pending: "waiting",
  active: "working",
  waiting_user: "waiting on you",
  complete: "done",
  failed: "stopped",
};

export function PipelineGraph({
  nodes,
  subActivity,
}: {
  nodes: Record<string, NodeState>;
  subActivity: Record<string, string>;
}) {
  return (
    <div className="wt-graph" aria-label="Pipeline progress">
      {TOPOLOGY.map((band) => (
        <section key={band.key} className="wt-graph__band">
          <h3 className="wt-graph__band-title">{band.title}</h3>
          <ol className="wt-graph__clusters">
            {band.clusters.map((cluster, i) => (
              <li key={i} className={`wt-graph__cluster wt-graph__cluster--${cluster.layout}`}>
                {cluster.label ? <p className="wt-graph__cluster-label">{cluster.label}</p> : null}
                <div className="wt-graph__nodes">
                  {cluster.nodes.map((node) => (
                    <NodeChip
                      key={node.id}
                      node={node}
                      state={nodes[node.id] ?? "pending"}
                      subActivity={subActivity[node.id]}
                    />
                  ))}
                </div>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

function NodeChip({
  node,
  state,
  subActivity,
}: {
  node: GraphNode;
  state: NodeState;
  subActivity?: string;
}) {
  return (
    <div className={`wt-node wt-node--${state} wt-node--${node.kind}`} data-state={state}>
      <span className="wt-node__dot" aria-hidden="true" />
      <span className="wt-node__body">
        <span className="wt-node__name">{node.friendly}</span>
        <span className="wt-node__state">{STATE_LABEL[state]}</span>
        {state === "active" && subActivity ? (
          <span className="wt-node__sub">{subActivity}</span>
        ) : null}
        {node.kind === "compute" ? (
          <span className="wt-node__kind">computed, not judged</span>
        ) : null}
      </span>
    </div>
  );
}
