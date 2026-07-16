import type { ReactNode } from "react";

import { Wordmark } from "./Wordmark";
import "./Surface.css";

/**
 * The two surfaces (design §3.4). `console` is the light ground where the user
 * builds and reviews; `chamber` is the deep dark surface where they watch the
 * governance run. Same shell, two registers — the spatial arc is the one
 * justified aesthetic risk (§3.4).
 */
export function Surface({
  kind,
  subtitle,
  header,
  children,
}: {
  kind: "console" | "chamber";
  subtitle?: string;
  header?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className={`wt-surface wt-surface--${kind}`}>
      <header className="wt-surface__bar">
        <Wordmark subtitle={subtitle} />
        {header ? <div className="wt-surface__header-slot">{header}</div> : null}
      </header>
      <main className="wt-surface__body">{children}</main>
    </div>
  );
}
