import "./StandingDisclaimer.css";

/**
 * The standing disclaimer (design §4.2): the draft-not-approval stance never
 * fully leaves the screen. A slim, permanent, never-dismissible footer strip on
 * both the Console and Chamber. Low emphasis, always legible.
 */
export function StandingDisclaimer() {
  return (
    <footer className="wt-disclaimer" role="contentinfo">
      Windtunnel produces drafts for SME review — not approvals, and not legal advice.
    </footer>
  );
}
