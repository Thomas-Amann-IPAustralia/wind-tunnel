import { useEffect, useRef } from "react";

import { friendlyFor } from "../lib/topology";
import type { StatusEvent } from "../lib/types";
import "./ActivityLog.css";

/**
 * The activity log (design §7.2.1) — the substance and the fallback: a scrolling,
 * timestamped, plain-language feed of the same events the graph shows. It is **not
 * optional; it is the accessibility and honesty backbone of the flagship.** It is
 * an ARIA live region, so a screen-reader user hears the pipeline progress in words
 * as it happens (§9), and it alone tells the complete story when motion is reduced
 * or the projector washes out the glow.
 *
 * Heartbeats are liveness pings with no content (§7.2.6) — they drive the staleness
 * note elsewhere and are not shown as log lines here.
 */
export function ActivityLog({
  events,
  staleSeconds,
  offline,
  running,
}: {
  events: StatusEvent[];
  staleSeconds: number | null;
  offline: boolean;
  running: boolean;
}) {
  const feedRef = useRef<HTMLOListElement>(null);
  const visible = events.filter((e) => e.type !== "heartbeat");

  // Follow the feed as new lines land by scrolling *the feed itself*, not the page:
  // `scrollIntoView` would bubble to the window and drag the flagship graph out of
  // view on load. Setting the feed's own scrollTop keeps the page still.
  useEffect(() => {
    const el = feedRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [visible.length]);

  return (
    <div className="wt-log">
      <div className="wt-log__head">
        <h3 className="wt-log__title">Activity</h3>
      </div>
      <ol className="wt-log__feed" aria-live="polite" aria-label="Live activity log" ref={feedRef}>
        {visible.length === 0 ? (
          <li className="wt-log__empty">Ready to run.</li>
        ) : (
          visible.map((e) => (
            <li key={e.id} className={`wt-log__line wt-log__line--${e.type}`}>
              <span className="wt-log__time wt-mono">{clock(e.ts)}</span>
              <span className="wt-log__agent">{friendlyFor(e.agent)}</span>
              <span className="wt-log__detail">{e.detail}</span>
            </li>
          ))
        )}
      </ol>
      {running ? (
        <p className="wt-log__stale" role="status">
          {offline
            ? "Reconnecting to the tunnel — your progress is saved."
            : staleSeconds !== null && staleSeconds >= 8
              ? `Still working — last update ${staleSeconds}s ago.`
              : "Working…"}
        </p>
      ) : null}
    </div>
  );
}

/** HH:MM from an ISO timestamp; falls back to the raw string if unparseable. */
function clock(ts: string): string {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
