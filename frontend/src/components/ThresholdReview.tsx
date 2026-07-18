import { useEffect, useState } from "react";

import { ApiError, artefactUrl, fetchArtefactText, NetworkError, thresholdRoute } from "../lib/api";
import { Markdown } from "../lib/markdown";
import "./ThresholdReview.css";

/**
 * The threshold review screen (design §7.4). The completed threshold assessment
 * (DTA sections 1–4) on the Console for the user to read before routing. The
 * design job: make the risk reasoning legible and the assessor divergence
 * *visible rather than buried* — divergence is signal, and showing it is the
 * honesty the whole product trades on. The rendered `threshold.md` carries the
 * risk table (chips are computed, §3.2) and the reconciler's divergence notes;
 * this screen wraps it with the routing decision, the markdown download, and the
 * honest ≤2-revision cap.
 *
 * Routing follows the tool's own logic: an all-low run *can conclude*; any
 * medium/high *requires full*; and the user may always choose full anyway. On
 * route the pipeline resumes (conclude → CONCLUDED; full → FULL_DRAFTING) and the
 * Chamber's poll swaps this screen out.
 */
export function ThresholdReview({ runCode }: { runCode: string }) {
  const [md, setMd] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [routing, setRouting] = useState(false);
  const [routeError, setRouteError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchArtefactText(runCode, "threshold.md")
      .then((text) => !cancelled && setMd(text))
      .catch((err) => !cancelled && setLoadError(describe(err, "load the threshold assessment")));
    return () => {
      cancelled = true;
    };
  }, [runCode]);

  async function route(outcome: "conclude" | "full") {
    setRouteError(null);
    setRouting(true);
    try {
      await thresholdRoute(runCode, outcome);
      // The pipeline resumes / concludes; the Chamber poll takes over from here.
    } catch (err) {
      setRouting(false);
      setRouteError(describe(err, "route this run"));
    }
  }

  return (
    <div className="wt-review">
      <header className="wt-review__head">
        <h2 className="wt-review__title">Your threshold assessment</h2>
        <p className="wt-review__lead">
          Two independent assessors drafted this; the reconciler drew them together, taking the
          higher rating wherever they disagreed. Each risk rating below is{" "}
          <strong>calculated from consequence × likelihood</strong> — it is not a model&rsquo;s
          opinion.
        </p>
      </header>

      <article className="wt-review__doc wt-panel">
        {loadError ? (
          <p className="wt-review__error" role="alert">
            {loadError}
          </p>
        ) : md === null ? (
          <p className="wt-review__loading" role="status">
            Loading the assessment…
          </p>
        ) : (
          <Markdown source={md} />
        )}
      </article>

      <footer className="wt-review__foot">
        <div className="wt-review__actions">
          <button
            type="button"
            className="wt-btn wt-btn--primary"
            onClick={() => route("full")}
            disabled={routing}
          >
            {routing ? "Starting…" : "Run the full assessment"}
          </button>
          <button
            type="button"
            className="wt-btn wt-btn--secondary"
            onClick={() => route("conclude")}
            disabled={routing}
          >
            Conclude here
          </button>
          <a
            className="wt-btn wt-btn--quiet"
            href={artefactUrl(runCode, "threshold.md", { download: true })}
            download
          >
            Download (Markdown)
          </a>
        </div>
        {routeError ? (
          <p className="wt-review__error" role="alert">
            {routeError}
          </p>
        ) : null}
        <p className="wt-review__note">
          &ldquo;Conclude here&rdquo; means this threshold assessment is ready for an approving
          officer to consider — not that it is approved. A full assessment brings the specialist
          college to bear on the risks above.
        </p>
      </footer>
    </div>
  );
}

function describe(err: unknown, action: string): string {
  if (err instanceof NetworkError)
    return `Couldn't reach the tunnel to ${action}. It may still be warming up — give it a moment.`;
  if (err instanceof ApiError) return err.message;
  return `Something went wrong trying to ${action}. Please try again.`;
}
