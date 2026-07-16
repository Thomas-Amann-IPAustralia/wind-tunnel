import "./Wordmark.css";

/**
 * The wordmark (design §1, §3.3 — Archivo). One word, product-not-facility. Name
 * is a one-token change if Tom picks an alternative (§1); everything downstream is
 * name-agnostic.
 */
export function Wordmark({ subtitle }: { subtitle?: string }) {
  return (
    <div className="wt-wordmark">
      <span className="wt-wordmark__name">Windtunnel</span>
      {subtitle ? <span className="wt-wordmark__subtitle">{subtitle}</span> : null}
    </div>
  );
}
