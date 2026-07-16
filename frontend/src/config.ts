/**
 * Deployment identity the SPA needs — the TS owner of the facts CLAUDE.md §6
 * says belong "in a committed frontend/ config ... not hardcoded across files".
 *
 * This mirrors `backend/config.py` by hand (there is no Python↔TS codegen — see
 * STATUS.md Decisions). When either side changes an owner/repo/branch or the
 * backend base URL, update both. Nothing here is secret; the backend is the sole
 * holder of GEMINI_API_KEY / WINDTUNNEL_PAT (CLAUDE.md §6).
 */

// The GitHub repo this deployment commits run state to (TECH_SPEC §1). Kept in
// sync with vite.config.ts `base` (/wind-tunnel/) and backend/config.py.
export const GITHUB_OWNER = "Thomas-Amann-IPAustralia";
export const GITHUB_REPO = "wind-tunnel";
export const GITHUB_BRANCH = "main";

/**
 * The backend base URL. In production the SPA (GitHub Pages) talks to the
 * backend on Render; in `vite dev` it talks to a locally-run backend. The value
 * is baked at build time from `VITE_BACKEND_URL`, falling back to the local dev
 * backend so `npm run dev` works with no extra config.
 */
export const BACKEND_URL: string = (
  import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

/**
 * The public repo browse URL for a given run — the run directory is
 * world-readable by design (CLAUDE.md §3, design §4), so the run code is a
 * locator, not a secret (§7.5). Used by the honest "everything here is public"
 * affordances.
 */
export function runRepoUrl(runCode: string): string {
  return `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/tree/${GITHUB_BRANCH}/runs/${runCode}`;
}
