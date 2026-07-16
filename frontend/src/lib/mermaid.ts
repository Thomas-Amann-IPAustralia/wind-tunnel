/**
 * The client-side Mermaid renderer (CLAUDE.md §9). The flow map (§6.4) is authored
 * as Mermaid source by the backend, but Render's free tier can't run the headless
 * Chromium `mermaid-cli` needs — so the SPA renders it to SVG in-browser and posts
 * the SVG back for commit. This module is the one place mermaid.js is touched, kept
 * thin so the Brainstorm canvas can mock it in tests (jsdom can't lay out an SVG).
 *
 * The source is derived from untrusted user content (§9.2), so `securityLevel:
 * "strict"` sanitises the output (no scripts, no click handlers, escaped labels).
 * The rendered SVG is still displayed inside a sandboxed iframe and the backend
 * refuses any `<script>` — defence in depth around the same untrusted text.
 */

import mermaid from "mermaid";

let initialised = false;

function ensureInit(): void {
  if (initialised) return;
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: "neutral",
    flowchart: { htmlLabels: false },
  });
  initialised = true;
}

/**
 * Render Mermaid source to an SVG string. Rejects if the source is not valid Mermaid
 * (the caller surfaces that as a plain "couldn't draw the map" message and lets the
 * user regenerate) — the same reject-don't-repair discipline the backend uses.
 */
export async function renderMermaid(source: string): Promise<string> {
  ensureInit();
  const id = `wt-mermaid-${Math.random().toString(36).slice(2, 10)}`;
  const { svg } = await mermaid.render(id, source);
  return svg;
}
