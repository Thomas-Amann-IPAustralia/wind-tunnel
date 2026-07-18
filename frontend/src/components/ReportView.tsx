import { useState } from "react";

import { ApiError, artefactUrl, NetworkError, reviseRun } from "../lib/api";
import "./ReportView.css";

/**
 * The report view (design §8) — the completed draft assessment. The nbconvert HTML
 * (`assessment.html`) is the thing a director actually reads; it is fully
 * self-contained (styles inlined, no external fonts/scripts, §12), so it renders
 * in a **sandboxed** iframe — the artefact is derived from untrusted user content
 * (§9.2), and the sandbox denies scripts and same-origin access so it can only
 * display, never act.
 *
 * Beside it (not part of the document) sits the honest revision affordance: the
 * same ≤2 cap pattern as the threshold screen (§7.4), a plain box for what should
 * change. On submit the Chamber reprises for the shorter pass and the regenerated
 * report returns marked "Revision N of 2" (§5.8). The exact used-count is not yet
 * in status.json (see STATUS.md handoff), so the cap is stated up front and the
 * server enforces it — a spent cap surfaces as a plain message, never a raw error.
 */
export function ReportView({ runCode }: { runCode: string }) {
  const [open, setOpen] = useState(false);
  const [instructions, setInstructions] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    const text = instructions.trim();
    if (!text) return;
    setError(null);
    setBusy(true);
    try {
      await reviseRun(runCode, text);
      setDone(true);
      // The pipeline resumes into USER_REVISION; the Chamber poll takes over.
    } catch (err) {
      setBusy(false);
      setError(describe(err));
    }
  }

  return (
    <div className="wt-report">
      <header className="wt-report__head">
        <h2 className="wt-report__title">Your draft assessment is ready</h2>
        <div className="wt-report__actions">
          <a
            className="wt-btn wt-btn--secondary"
            href={artefactUrl(runCode, "assessment.html")}
            target="_blank"
            rel="noreferrer"
          >
            Open in a new tab
          </a>
          <a
            className="wt-btn wt-btn--quiet"
            href={artefactUrl(runCode, "assessment.ipynb", { download: true })}
            download
          >
            Download notebook
          </a>
        </div>
      </header>

      <iframe
        className="wt-report__frame"
        title="Draft impact assessment report"
        src={artefactUrl(runCode, "assessment.html")}
        sandbox=""
      />

      <section className="wt-report__revise wt-panel">
        <div className="wt-report__revise-head">
          <h3 className="wt-report__revise-title">Ask for a revision</h3>
          <p className="wt-report__revise-cap">You can ask for up to 2 rounds of revisions.</p>
        </div>
        {done ? (
          <p className="wt-report__revise-done" role="status">
            Revision requested — the tunnel is re-running the targeted specialists, the reviewer,
            and assembly. This screen will update when the new draft is ready.
          </p>
        ) : !open ? (
          <button type="button" className="wt-btn wt-btn--secondary" onClick={() => setOpen(true)}>
            Request a revision
          </button>
        ) : (
          <div className="wt-report__revise-form">
            <label htmlFor="revise" className="wt-report__revise-label">
              What should change? The targeted specialists, the reviewer, and assembly will run
              again.
            </label>
            <textarea
              id="revise"
              className="wt-report__revise-input"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              rows={4}
              placeholder="e.g. The privacy section should address biometric data specifically."
            />
            {error ? (
              <p className="wt-report__revise-error" role="alert">
                {error}
              </p>
            ) : null}
            <div className="wt-report__revise-buttons">
              <button
                type="button"
                className="wt-btn wt-btn--primary"
                onClick={submit}
                disabled={busy || instructions.trim().length === 0}
              >
                {busy ? "Starting the revision…" : "Submit revision"}
              </button>
              <button
                type="button"
                className="wt-btn wt-btn--quiet"
                onClick={() => setOpen(false)}
                disabled={busy}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function describe(err: unknown): string {
  if (err instanceof NetworkError)
    return "Couldn't reach the tunnel to request the revision. Give it a moment and try again.";
  if (err instanceof ApiError) return err.message;
  return "Something went wrong requesting the revision. Please try again.";
}
