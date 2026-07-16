import { useState } from "react";

import "./RunCodeChip.css";

/**
 * The run-code chip (design §3.7, §7.5) — the persistent WT-XXXX-XX element with
 * one-tap copy. The run code is a locator, not a secret (the whole repo is public,
 * §4), so the tooltip says so honestly rather than implying secrecy. `prominent`
 * is the pause/failure treatment where the chip grows into the primary element.
 */
export function RunCodeChip({ code, prominent = false }: { code: string; prominent?: boolean }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard blocked (e.g. insecure context) — the code is visible to select
      // by hand, so this is a non-fatal degradation, not an error to surface.
    }
  }

  return (
    <div className={`wt-runcode${prominent ? " wt-runcode--prominent" : ""}`}>
      <span className="wt-runcode__label">Run code</span>
      <code className="wt-runcode__value">{code}</code>
      <button
        type="button"
        className="wt-runcode__copy"
        onClick={copy}
        title="Your ticket back to this run. (Everything here is public, remember.)"
        aria-label={`Copy run code ${code}. This run is public.`}
      >
        {copied ? "copied" : "copy"}
      </button>
    </div>
  );
}
