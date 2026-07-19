import { useEffect, useRef } from "react";

import { Wordmark } from "./Wordmark";
import "./UsageWarningGate.css";

/**
 * The gate before anything (design §4.1). Shown before any input is accepted, on
 * first arrival. Prominence comes from space, position and a single focus mark —
 * not red borders or all-caps. Orientation the user needs, not terms to survive.
 *
 * Accessibility (§4.1): a labelled region announced on load, focus lands on the
 * heading, the continue action is reachable by tab immediately.
 */
export function UsageWarningGate({ onAccept }: { onAccept: () => void }) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  return (
    <div className="wt-gate" role="dialog" aria-modal="true" aria-labelledby="wt-gate-heading">
      <div className="wt-gate__card wt-panel">
        <div className="wt-gate__brand">
          <Wordmark subtitle="Before you start" />
        </div>

        <h1 id="wt-gate-heading" className="wt-gate__heading" tabIndex={-1} ref={headingRef}>
          A few things to know first
        </h1>

        <ul className="wt-gate__points">
          <li>
            <span className="wt-gate__mark" aria-hidden="true">
              ◆
            </span>
            <span>
              <strong>This is public.</strong> Everything you type or generate here is saved to a
              world-readable GitHub repository. Anyone on the internet can read it — treat this like
              posting in the open.
            </span>
          </li>
          <li>
            <span className="wt-gate__mark" aria-hidden="true">
              ◆
            </span>
            <span>
              <strong>Nothing sensitive.</strong> Don&rsquo;t enter classified information,
              sensitive information, or personal information about identifiable people. This system
              carries no security accreditation and makes no claim about what it can safely handle —
              the rule is simply: don&rsquo;t put in anything you wouldn&rsquo;t be comfortable
              seeing posted in the open.
            </span>
          </li>
          <li>
            <span className="wt-gate__mark" aria-hidden="true">
              ◆
            </span>
            <span>
              <strong>Draft only.</strong> What you get back is a draft to give your subject-matter
              experts. It isn&rsquo;t an approval, and it isn&rsquo;t legal advice.
            </span>
          </li>
        </ul>

        <button type="button" className="wt-btn wt-btn--primary wt-gate__accept" onClick={onAccept}>
          I understand — continue
        </button>
      </div>
    </div>
  );
}
