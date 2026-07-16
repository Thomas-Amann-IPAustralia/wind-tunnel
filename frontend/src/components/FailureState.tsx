import { useState } from "react";

import { RunCodeChip } from "./RunCodeChip";
import { friendlyFor } from "../lib/topology";
import type { FailurePayload } from "../lib/types";
import "./FailureState.css";

/**
 * The failure state (design §7.2.4). Runs are dozens of LLM calls over tens of
 * minutes; failures happen, and the state is **calm and actionable**, never
 * blaring. Completed work stays visibly saved (the graph above keeps its
 * `complete` nodes); here we give the plain explanation, surface the run code
 * prominently with resume instructions (a paused and a failed run resume
 * identically, §7.5), and tuck the technical detail behind a disclosure for Tom or
 * a curious user — reassurance first, the one action that matters, then the detail
 * only if asked.
 */
export function FailureState({
  runCode,
  failure,
}: {
  runCode: string;
  failure: FailurePayload | null;
}) {
  const [showTechnical, setShowTechnical] = useState(false);
  const where = failure?.stage ? friendlyFor(failure.stage) : "one of the stages";

  return (
    <div className="wt-failure" role="alert">
      <h2 className="wt-failure__title">The run stopped — your progress is saved</h2>
      <p className="wt-failure__lead">
        {failure?.message ?? `The run stopped at ${where}.`} Everything completed up to that point
        is saved. Nothing is lost.
      </p>

      <div className="wt-failure__resume">
        <p className="wt-failure__resume-lead">
          Pick up from the last saved point with your run code:
        </p>
        <RunCodeChip code={runCode} prominent />
        <p className="wt-failure__resume-note">
          Paste it on the landing screen&rsquo;s &ldquo;Resume a run&rdquo; to continue from here.
        </p>
      </div>

      {failure?.technical ? (
        <div className="wt-failure__technical">
          <button
            type="button"
            className="wt-btn wt-btn--quiet"
            aria-expanded={showTechnical}
            onClick={() => setShowTechnical((s) => !s)}
          >
            {showTechnical ? "Hide technical detail" : "Show technical detail"}
          </button>
          {showTechnical ? (
            <pre className="wt-failure__detail wt-mono">{failure.technical}</pre>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
