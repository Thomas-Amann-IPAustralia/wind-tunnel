import { useCallback, useState } from "react";

import { RunCodeChip } from "./RunCodeChip";
import { ApiError, NetworkError, redispatchRun } from "../lib/api";
import { friendlyFor } from "../lib/topology";
import type { FailurePayload } from "../lib/types";
import "./FailureState.css";

/**
 * The failure state (design §7.2.4). Runs are dozens of LLM calls over tens of
 * minutes; failures happen, and the state is **calm and actionable**, never
 * blaring. Completed work stays visibly saved (the graph above keeps its
 * `complete` nodes); here we give the plain explanation, the one action that
 * matters — resume from the last checkpoint, right here — the run code for
 * coming back later (a paused and a failed run resume identically, §7.5), and
 * the technical detail behind a disclosure for Tom or a curious user.
 * "Resume the run" re-dispatches Governance (idempotent, §5.3 — completed
 * checkpoints are skipped, only the failed stage re-runs); the poll then sees
 * the run go `running` and this face swaps back to the live graph.
 */
export function FailureState({
  runCode,
  failure,
}: {
  runCode: string;
  failure: FailurePayload | null;
}) {
  const [showTechnical, setShowTechnical] = useState(false);
  const [retry, setRetry] = useState<"idle" | "working" | "done" | "error">("idle");
  const [retryError, setRetryError] = useState<string | null>(null);
  const where = failure?.stage ? friendlyFor(failure.stage) : "one of the stages";

  const resume = useCallback(async () => {
    setRetry("working");
    setRetryError(null);
    try {
      const res = await redispatchRun(runCode);
      if (res.dispatched) {
        setRetry("done");
      } else {
        setRetry("error");
        setRetryError(
          res.dispatch_error ?? "The run could not be restarted. Please try again shortly.",
        );
      }
    } catch (err) {
      setRetry("error");
      setRetryError(
        err instanceof NetworkError
          ? "Couldn't reach the tunnel — it may be warming up. Give it a moment and try again."
          : err instanceof ApiError
            ? err.message
            : "Something went wrong trying to resume the run. Please try again.",
      );
    }
  }, [runCode]);

  return (
    <div className="wt-failure" role="alert">
      <h2 className="wt-failure__title">The run stopped — your progress is saved</h2>
      <p className="wt-failure__lead">
        {failure?.message ?? `The run stopped at ${where}.`} Everything completed up to that point
        is saved. Nothing is lost.
      </p>

      <div className="wt-failure__resume">
        {retry === "done" ? (
          <p className="wt-failure__resume-lead" role="status">
            Resume requested — the run will pick up from its last saved point in a moment. Watch the
            stages above.
          </p>
        ) : (
          <>
            <button
              type="button"
              className="wt-btn wt-btn--primary"
              onClick={resume}
              disabled={retry === "working"}
            >
              {retry === "working" ? "Resuming…" : "Resume the run"}
            </button>
            {retry === "error" && retryError ? (
              <p className="wt-failure__resume-error" role="alert">
                {retryError}
              </p>
            ) : null}
          </>
        )}
        <p className="wt-failure__resume-lead">Or come back any time with your run code:</p>
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
