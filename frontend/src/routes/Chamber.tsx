import { useCallback, useMemo, useState } from "react";
import { Navigate, useParams } from "react-router-dom";

import { ActivityLog } from "../components/ActivityLog";
import { Checkpoint } from "../components/Checkpoint";
import { FailureState } from "../components/FailureState";
import { PipelineGraph } from "../components/PipelineGraph";
import { ReportView } from "../components/ReportView";
import { RunCodeChip } from "../components/RunCodeChip";
import { Surface } from "../components/Surface";
import { ThresholdReview } from "../components/ThresholdReview";
import { useStatusPoll } from "../hooks/useStatusPoll";
import { ApiError, artefactUrl, NetworkError, redispatchRun } from "../lib/api";
import { isValid } from "../lib/runCode";
import { TOPOLOGY } from "../lib/topology";
import type { StatusDoc } from "../lib/types";
import "./Chamber.css";

/**
 * The Chamber (design §7) — the governance surface where the user watches their
 * idea go through the tunnel. This route is the poll host: one status poll fully
 * determines the visible state (CLAUDE.md §3), and the run's `overall_state` +
 * `questions` pick which face to show. The flagship transparency animation (the
 * graph + activity log, §7.2) is the running/created face; the run breaks out to
 * the Console for the threshold review (§7.4) and the question checkpoint (§7.3),
 * settles into the report on completion (§8), and rests in a calm, resumable
 * failure state on error (§7.2.4). The resume-by-code flow lands here and the same
 * state logic drops the user at the exact right face (§7.5).
 */
export function Chamber() {
  const { code } = useParams();
  const valid = Boolean(code && isValid(code));
  const { doc, error, staleSeconds, offline } = useStatusPoll(code, valid);

  if (!valid || !code) return <Navigate to="/" replace />;

  // Hard error (e.g. an unknown code) — a plain message, never a raw failure.
  if (error) {
    return (
      <Surface kind="chamber" subtitle="Governance" header={<RunCodeChip code={code} />}>
        <div className="wt-chamber__notice" role="alert">
          <h2>We couldn&rsquo;t load this run</h2>
          <p>{error}</p>
        </div>
      </Surface>
    );
  }

  // First load / cold start — honest connecting copy.
  if (!doc) {
    return (
      <Surface kind="chamber" subtitle="Governance" header={<RunCodeChip code={code} />}>
        <div className="wt-chamber__notice" role="status">
          <h2>Opening the tunnel…</h2>
          <span className="wt-chamber__travel" aria-hidden="true" />
          <p>
            {offline
              ? "The backend may be warming up — this can take up to a minute on a cold start. It hasn't stalled; keep this open."
              : "Loading your run."}
          </p>
        </div>
      </Surface>
    );
  }

  const paused = doc.overall_state === "paused";
  const failed = doc.overall_state === "failed";
  const complete = doc.overall_state === "complete";
  const atCheckpoint = paused && hasQuestions(doc);
  const atThreshold = paused && !hasQuestions(doc);
  const concluded = complete && doc.phase === "threshold";

  // The Console pauses + the report render on the light surface (design §7.4/§7.3/§8);
  // watching the run and the calm failure state live on the dark Chamber.
  const onConsole = atCheckpoint || atThreshold || complete;
  const prominent = paused || failed;

  return (
    <Surface
      kind={onConsole ? "console" : "chamber"}
      subtitle="Governance"
      header={<RunCodeChip code={code} prominent={prominent} />}
    >
      {atThreshold ? (
        <ThresholdReview runCode={code} />
      ) : atCheckpoint && doc.questions ? (
        <Checkpoint runCode={code} questions={doc.questions} />
      ) : concluded ? (
        <ConcludedView runCode={code} />
      ) : complete ? (
        <ReportView runCode={code} />
      ) : (
        <RunningView doc={doc} failed={failed} staleSeconds={staleSeconds} offline={offline} />
      )}
    </Surface>
  );
}

function RunningView({
  doc,
  failed,
  staleSeconds,
  offline,
}: {
  doc: StatusDoc;
  failed: boolean;
  staleSeconds: number | null;
  offline: boolean;
}) {
  const subActivity = useMemo(() => buildSubActivity(doc), [doc]);
  const range = doc.expected_ranges?.[doc.phase];
  // A submitted run whose pipeline hasn't demonstrably begun — no node has left
  // `pending` and nothing has failed. Usually the GitHub Action is just spinning
  // up (checkout + deps, up to ~a minute), but a `workflow_dispatch` that never
  // took (§5.7 — e.g. a PAT lacking actions:write) looks identical, so offer an
  // honest wait + a safe re-kick rather than a silently frozen graph.
  const notStarted = !failed && allPending(doc.nodes);

  return (
    <div className="wt-chamber">
      <p className="wt-chamber__orient">
        Your idea is going through the tunnel. Here&rsquo;s every stage — watch it work.
      </p>
      {notStarted ? <NotStartedPrompt runCode={doc.run_code} staleSeconds={staleSeconds} /> : null}
      <div className="wt-chamber__panes">
        <div className="wt-chamber__graph">
          <PipelineGraph nodes={doc.nodes} subActivity={subActivity} />
          {range && !failed ? (
            <p className="wt-chamber__range">
              This phase usually takes {minutes(range[0])}–{minutes(range[1])} minutes. You can
              safely close the tab and come back with your run code.
            </p>
          ) : null}
        </div>
        <aside className="wt-chamber__side">
          {failed ? null : (
            <ActivityLog
              events={doc.log}
              staleSeconds={staleSeconds}
              offline={offline}
              running={doc.overall_state === "running" || doc.overall_state === "created"}
            />
          )}
        </aside>
      </div>
      {failed ? <FailureState runCode={doc.run_code} failure={doc.failure} /> : null}
    </div>
  );
}

/**
 * Shown while a submitted run's pipeline hasn't demonstrably started (§5.7). It is
 * honest about the usual cause (the run's GitHub Action taking a moment to spin up)
 * and, after a short wait, offers a safe re-kick for the case where the dispatch
 * genuinely never took (the bug behind "the chamber opened but nothing happened").
 * The re-dispatch is idempotent and serialised per run, so a click during a healthy
 * cold start simply queues behind the run that is already starting.
 */
function NotStartedPrompt({
  runCode,
  staleSeconds,
}: {
  runCode: string;
  staleSeconds: number | null;
}) {
  const [state, setState] = useState<"idle" | "working" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const restart = useCallback(async () => {
    setState("working");
    setError(null);
    try {
      const res = await redispatchRun(runCode);
      if (res.dispatched) {
        setState("done");
      } else {
        setState("error");
        setError(res.dispatch_error ?? "The run could not be started. Please try again shortly.");
      }
    } catch (err) {
      setState("error");
      setError(
        err instanceof NetworkError
          ? "Couldn't reach the tunnel — it may be warming up. Give it a moment and try again."
          : err instanceof ApiError
            ? err.message
            : "Something went wrong trying to restart the run. Please try again.",
      );
    }
  }, [runCode]);

  // Give the Action a genuine chance to start before nudging a retry (§7.2.5).
  const waitedAWhile = staleSeconds !== null && staleSeconds >= 45;

  return (
    <div className="wt-chamber__start" role="status">
      <span className="wt-chamber__travel" aria-hidden="true" />
      <p className="wt-chamber__start-lead">
        Waiting for the run to start. This can take up to a minute while the tunnel spins up —
        it&rsquo;s still working, not stuck. You can safely close the tab and come back with your
        run code.
      </p>
      {state === "done" ? (
        <p className="wt-chamber__start-note">Restart requested — watch the stages above.</p>
      ) : (
        <>
          <p className="wt-chamber__start-note">
            {waitedAWhile
              ? "Still nothing after a moment? You can restart the run — it won't lose any progress."
              : "If nothing happens after a minute, you can restart it."}
          </p>
          <button
            type="button"
            className="wt-btn wt-btn--secondary"
            onClick={restart}
            disabled={state === "working"}
          >
            {state === "working" ? "Restarting…" : "Restart the run"}
          </button>
          {state === "error" && error ? (
            <p className="wt-chamber__start-error" role="alert">
              {error}
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}

/** A threshold run the user chose to conclude — no full report, just the
 * threshold artefact and a plain, non-overclaiming close (§7.4). */
function ConcludedView({ runCode }: { runCode: string }) {
  return (
    <div className="wt-chamber__notice wt-chamber__notice--light">
      <h2>Your threshold assessment is complete</h2>
      <p>
        This threshold assessment is ready for an approving officer to consider. You chose to
        conclude here rather than run the full assessment.
      </p>
      <a className="wt-btn wt-btn--secondary" href={artefactUrl(runCode, "threshold.md")} download>
        Download the assessment (Markdown)
      </a>
    </div>
  );
}

function hasQuestions(doc: StatusDoc): boolean {
  return Boolean(doc.questions && (doc.questions.specialists?.length ?? 0) > 0);
}

/** True when no node has left `pending` — the pipeline hasn't demonstrably begun.
 * An empty map counts as "not started" too (a just-submitted run before the first
 * pipeline write). */
function allPending(nodes: StatusDoc["nodes"]): boolean {
  return Object.values(nodes).every((s) => s === "pending");
}

/** The genuine current sub-activity per node — the latest retrieval/drafting
 * detail, keyed by node id (the log's `agent` may be a node id or its friendly
 * name, §7.2.6), so the active node shows what it is *actually* doing (§7.2.5). */
function buildSubActivity(doc: StatusDoc): Record<string, string> {
  const byAgent: Record<string, string> = {};
  for (const e of doc.log) {
    if (e.type === "retrieval" || e.type === "drafting") byAgent[e.agent] = e.detail;
  }
  const out: Record<string, string> = {};
  for (const band of TOPOLOGY) {
    for (const cluster of band.clusters) {
      for (const node of cluster.nodes) {
        const detail = byAgent[node.id] ?? byAgent[node.friendly];
        if (detail) out[node.id] = detail;
      }
    }
  }
  return out;
}

function minutes(seconds: number): number {
  return Math.max(1, Math.round(seconds / 60));
}
