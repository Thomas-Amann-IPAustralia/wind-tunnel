import type { GraphNode, NodeKind } from "../lib/topology";
import type { NodeState } from "../lib/types";
import "./NodeDetail.css";

/**
 * The node detail drawer (the redesign's transparency payload). Opening a stage
 * explains, in plain language a non-engineer can follow, what that stage is and
 * what it is doing — and backs the explanation with the *real* evidence from the
 * status log: the sources it has read and the questions it has raised. This is
 * where "make the system more transparent by explaining how it works" lands: the
 * graph shows the shape, the drawer tells the story, and both are the same events
 * the activity log states in words (§7.2.1 — nothing exists only in the graph).
 *
 * Everything shown is derived from one status poll (CLAUDE.md §3); the drawer never
 * fetches. Compute nodes get the load-bearing "no AI model here" callout — the
 * visible face of "models argue, code computes" (CLAUDE.md §3).
 */

export interface NodeEvidence {
  /** Sources this node has read this run, newest first (retrieval events). */
  retrievals: { detail: string; doc?: string; locator?: string }[];
  /** Questions this node has raised for the user (question_raised events). */
  questions: { id: string; text: string }[];
}

const KIND_LABEL: Record<NodeKind, string> = {
  llm: "AI agent",
  compute: "Automated step",
  pause: "Your input",
};

const STATE_LABEL: Record<NodeState, string> = {
  pending: "Waiting its turn",
  active: "Working now",
  waiting_user: "Waiting on you",
  complete: "Done",
  failed: "Stopped",
};

export function NodeDetail({
  node,
  state,
  subActivity,
  evidence,
  onClose,
}: {
  node: GraphNode;
  state: NodeState;
  subActivity?: string;
  evidence: NodeEvidence;
  onClose: () => void;
}) {
  const isCompute = node.kind === "compute";
  return (
    <aside className="wt-ndetail" aria-label={`${node.friendly} detail`}>
      <div className="wt-ndetail__head">
        <span className={`wt-ndetail__kind wt-ndetail__kind--${node.kind}`}>
          {KIND_LABEL[node.kind]}
        </span>
        <h3 className="wt-ndetail__title">{node.friendly}</h3>
        <button
          type="button"
          className="wt-ndetail__close"
          onClick={onClose}
          aria-label="Close detail"
        >
          ×
        </button>
      </div>

      <div className="wt-ndetail__body">
        <p className={`wt-ndetail__status wt-ndetail__status--${state}`}>
          <span className="wt-ndetail__status-dot" aria-hidden="true" />
          {STATE_LABEL[state]}
          {state === "active" && subActivity ? (
            <span className="wt-ndetail__now"> — {subActivity}</span>
          ) : null}
        </p>

        <p className="wt-ndetail__explain">{node.explain}</p>

        <dl className="wt-ndetail__facts">
          <div>
            <dt>Runs on</dt>
            <dd>{node.engine}</dd>
          </div>
          {node.owns ? (
            <div>
              <dt>Responsible for</dt>
              <dd>{node.owns}</dd>
            </div>
          ) : null}
        </dl>

        {isCompute ? (
          <p className="wt-ndetail__callout">
            No AI model runs here. This step is fixed rules — the same inputs always produce the
            same result, so nothing about it can be talked into a different answer.
          </p>
        ) : null}

        {node.kind === "llm" ? (
          <section className="wt-ndetail__sec">
            <h4 className="wt-ndetail__sec-title">Sources it has read</h4>
            {evidence.retrievals.length > 0 ? (
              <ul className="wt-ndetail__list">
                {evidence.retrievals.map((r, i) => (
                  <li key={i} className="wt-ndetail__source">
                    <span className="wt-ndetail__source-doc">{r.doc ?? r.detail}</span>
                    {r.locator ? (
                      <span className="wt-ndetail__source-loc wt-mono">{r.locator}</span>
                    ) : null}
                    {r.doc && r.detail && r.detail !== r.doc ? (
                      <span className="wt-ndetail__source-note">{r.detail}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="wt-ndetail__empty">
                Nothing read yet — the sources this stage relies on will appear here, each one
                traceable, as it works.
              </p>
            )}
          </section>
        ) : null}

        {evidence.questions.length > 0 ? (
          <section className="wt-ndetail__sec">
            <h4 className="wt-ndetail__sec-title">Questions it raised for you</h4>
            <ul className="wt-ndetail__list">
              {evidence.questions.map((q) => (
                <li key={q.id} className="wt-ndetail__question">
                  {q.text}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </aside>
  );
}
