import type { FeasibilityVerdict } from "../lib/types";
import "./BrainstormSynthesis.css";

/**
 * The two expressive input surfaces on the Brainstorm canvas — the proof of concept
 * (§6.3) and the flow map (§6.4). These are not artefacts squeezed out of the outline:
 * they are alternative ways for a public servant to *say what they want the end state
 * to be*, more vividly than prose. Each lives behind its own top-of-page tab (design
 * §6.2), so it reads as a thing you do, not a leftover at the foot of the page.
 *
 * Both are encouraged honestly, never nagged (§6.5): the outline alone is enough to
 * submit; a PoC or a flow map simply gives the specialists — and the user — a sharper
 * picture. Each produced artefact shows in a `sandbox=""` iframe: it is derived from
 * untrusted user content (§9.2), so, like the report, it can only display, never act.
 *
 * Presentational: all state and the API calls live in the Brainstorm route.
 */

/** The proof-of-concept panel. Offered until the feasibility gate has spoken; if the
 * gate decides a static mock is not a fit, the build action is replaced by an honest
 * note pointing at the flow map (which was produced instead) — no dead button. */
export function PocPanel({
  feasibility,
  pocUrl,
  building,
  error,
  onBuildPoc,
}: {
  feasibility: FeasibilityVerdict | null;
  pocUrl: string | null;
  building: boolean;
  error: string | null;
  onBuildPoc: () => void;
}) {
  const pocNotAFit = feasibility !== null && !feasibility.feasible;

  return (
    <section className="wt-synth wt-panel" aria-label="Proof of concept">
      <div className="wt-synth__head">
        <h3 className="wt-synth__title">Proof of concept — optional</h3>
        <p className="wt-synth__lead">
          Sketch the end state. A clickable mock can say what you&rsquo;re picturing far more
          vividly than words — and the specialists read it too. Your outline is already enough to
          submit; this just sharpens it.
        </p>
      </div>

      {pocNotAFit ? (
        <p className="wt-synth__not-a-fit" role="status">
          <span className="wt-synth__not-a-fit-label">Not a fit for this idea.</span>{" "}
          {feasibility?.reason} We&rsquo;ve drawn a flow map instead — see the Flow map tab.
        </p>
      ) : (
        <div className="wt-synth__actions">
          <button
            type="button"
            className="wt-btn wt-btn--secondary"
            onClick={onBuildPoc}
            disabled={building}
          >
            {building
              ? "Building a proof of concept…"
              : pocUrl
                ? "Rebuild the proof of concept"
                : "Build a proof of concept"}
          </button>
        </div>
      )}

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
    </section>
  );
}

/** The flow-map panel. Always available. The SVG is rendered client-side (CLAUDE.md §9)
 * and shown in a sandboxed iframe. It uses the same node/flow grammar as the pipeline
 * animation the user is about to watch (§3.5). */
export function FlowMapPanel({
  flowSvg,
  building,
  error,
  onGenerateMap,
}: {
  flowSvg: string | null;
  building: boolean;
  error: string | null;
  onGenerateMap: () => void;
}) {
  return (
    <section className="wt-synth wt-panel" aria-label="Flow map">
      <div className="wt-synth__head">
        <h3 className="wt-synth__title">Flow map — optional</h3>
        <p className="wt-synth__lead">
          Draw the shape of the thing: the actors, the systems, and how data moves between them.
          It&rsquo;s often the clearest way to externalise where the AI actually sits. Your outline
          is already enough to submit; this just sharpens it.
        </p>
      </div>

      <div className="wt-synth__actions">
        <button
          type="button"
          className="wt-btn wt-btn--secondary"
          onClick={onGenerateMap}
          disabled={building}
        >
          {building
            ? "Drawing the flow map…"
            : flowSvg
              ? "Regenerate the flow map"
              : "Generate a flow map"}
        </button>
      </div>

      {error ? (
        <p className="wt-synth__error" role="alert">
          {error}
        </p>
      ) : null}

      {flowSvg ? (
        <figure className="wt-synth__artefact">
          <figcaption className="wt-synth__artefact-head">
            <span className="wt-synth__artefact-title">Flow map</span>
            <button
              type="button"
              className="wt-btn wt-btn--quiet"
              onClick={() => openSvgInNewTab(flowSvg)}
            >
              Open in a new tab
            </button>
          </figcaption>
          <iframe
            className="wt-synth__frame wt-synth__frame--map"
            title="Information-flow map"
            srcDoc={svgDoc(flowSvg)}
            sandbox=""
          />
          <p className="wt-synth__caveat">
            Actors, systems, and how data moves. It reads the same way as the pipeline you&rsquo;re
            about to watch. The preview is small — open it in a new tab to see it full-size.
          </p>
        </figure>
      ) : null}
    </section>
  );
}

/** Open the rendered flow map full-size in a new browser tab. The SVG is client-side only
 * (never committed as a servable file until its `/flow-map/svg` round-trip), so there is no
 * artefact URL to link — we wrap it as a standalone document in a blob URL. The blob is
 * revoked after a minute so it doesn't leak once the tab has loaded. */
function openSvgInNewTab(svg: string): void {
  const blob = new Blob([svgDoc(svg)], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener,noreferrer");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
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
