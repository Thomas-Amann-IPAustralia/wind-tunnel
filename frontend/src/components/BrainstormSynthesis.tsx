import type { FeasibilityVerdict } from "../lib/types";
import "./BrainstormSynthesis.css";

/**
 * The optional synthesis block on the Brainstorm canvas (design §6.2–6.4) — the two
 * "enrich the assessment" actions and their produced artefacts. Both are encouraged
 * honestly, never nagged (§6.5): the outline alone is enough to submit; a PoC or a
 * flow map simply gives the specialists more to work with.
 *
 * - **Proof of concept (§6.3).** Offered until the feasibility gate has spoken. If the
 *   gate decides a static mock is not a fit, the PoC action is replaced by an honest
 *   conditional-stage note and the flow map is produced instead — no dead button.
 * - **Flow map (§6.4).** Always available. The SVG is rendered client-side (CLAUDE.md
 *   §9) and shown in a sandboxed iframe — it is derived from untrusted user content
 *   (§9.2), so, like the report, it can only display, never act. It uses the same
 *   node/flow grammar as the pipeline animation the user is about to watch (§3.5).
 *
 * Presentational: all state and the API calls live in the Brainstorm route.
 */
export function BrainstormSynthesis({
  feasibility,
  pocUrl,
  flowSvg,
  building,
  error,
  onBuildPoc,
  onGenerateMap,
}: {
  feasibility: FeasibilityVerdict | null;
  pocUrl: string | null;
  flowSvg: string | null;
  building: "poc" | "map" | null;
  error: string | null;
  onBuildPoc: () => void;
  onGenerateMap: () => void;
}) {
  const busy = building !== null;
  const pocNotAFit = feasibility !== null && !feasibility.feasible;

  return (
    <section className="wt-synth wt-panel" aria-label="Enrich the assessment">
      <div className="wt-synth__head">
        <h3 className="wt-synth__title">Enrich the assessment — optional</h3>
        <p className="wt-synth__lead">
          Your outline is enough on its own. A proof of concept or a flow map gives the specialists
          more to work with — add either, or submit as you are.
        </p>
      </div>

      <div className="wt-synth__actions">
        {pocNotAFit ? null : (
          <button
            type="button"
            className="wt-btn wt-btn--secondary"
            onClick={onBuildPoc}
            disabled={busy}
          >
            {building === "poc"
              ? "Building a proof of concept…"
              : pocUrl
                ? "Rebuild the proof of concept"
                : "Build a proof of concept"}
          </button>
        )}
        <button
          type="button"
          className="wt-btn wt-btn--secondary"
          onClick={onGenerateMap}
          disabled={busy}
        >
          {building === "map"
            ? "Drawing the flow map…"
            : flowSvg
              ? "Regenerate the flow map"
              : "Generate a flow map"}
        </button>
      </div>

      {pocNotAFit ? (
        <p className="wt-synth__not-a-fit" role="status">
          <span className="wt-synth__not-a-fit-label">
            Proof of concept — not a fit for this idea.
          </span>{" "}
          {feasibility?.reason} You&rsquo;ll get a flow map instead.
        </p>
      ) : null}

      {error ? (
        <p className="wt-synth__error" role="alert">
          {error}
        </p>
      ) : null}

      {pocUrl ? (
        <figure className="wt-synth__artefact">
          <figcaption className="wt-synth__artefact-head">
            <span className="wt-synth__artefact-title">Proof of concept</span>
            <a className="wt-btn wt-btn--quiet" href={pocUrl} target="_blank" rel="noreferrer">
              Open in a new tab
            </a>
          </figcaption>
          <iframe
            className="wt-synth__frame wt-synth__frame--poc"
            title="Proof-of-concept preview"
            src={pocUrl}
            sandbox=""
          />
          <p className="wt-synth__caveat">
            An illustrative mock — its own limitations banner names exactly what it fakes.
          </p>
        </figure>
      ) : null}

      {flowSvg ? (
        <figure className="wt-synth__artefact">
          <figcaption className="wt-synth__artefact-head">
            <span className="wt-synth__artefact-title">Flow map</span>
          </figcaption>
          <iframe
            className="wt-synth__frame wt-synth__frame--map"
            title="Information-flow map"
            srcDoc={svgDoc(flowSvg)}
            sandbox=""
          />
          <p className="wt-synth__caveat">
            Actors, systems, and how data moves. It reads the same way as the pipeline you&rsquo;re
            about to watch.
          </p>
        </figure>
      ) : null}
    </section>
  );
}

/** Wrap a rendered SVG as a minimal standalone document for a sandboxed iframe, so
 * the map is never injected into the app DOM (no innerHTML for untrusted-derived
 * markup, §9.2) yet still scales to the frame. */
function svgDoc(svg: string): string {
  return (
    '<!doctype html><meta charset="utf-8">' +
    "<style>html,body{margin:0;padding:0;background:transparent}" +
    "svg{display:block;max-width:100%;height:auto;margin:0 auto}</style>" +
    svg
  );
}
