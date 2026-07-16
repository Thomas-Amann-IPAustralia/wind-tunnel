import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Surface } from "../components/Surface";
import { useBackendStatus } from "../context/BackendStatus";
import { ColdStartNote } from "../components/ColdStartNote";
import { ApiError, NetworkError, resumeRun } from "../lib/api";
import { routeForStage } from "../lib/navigation";
import { validate } from "../lib/runCode";
import "./ResumeScreen.css";

/**
 * The resume-entry flow (design §7.5). A single mono input; the code is validated
 * locally first (so a typo never becomes a network round-trip), then the run's
 * state is fetched and the user is dropped back at the exact checkpoint. A
 * well-formed but unknown code gives a plain error, never a raw failure.
 */
export function ResumeScreen() {
  const navigate = useNavigate();
  const { ensureWarm } = useBackendStatus();
  const [raw, setRaw] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const code = validate(raw);
    if (!code) {
      setError(
        "That doesn't look like a run code. They read like WT-7K3D-Q2 — check the characters?",
      );
      return;
    }
    setBusy(true);
    ensureWarm();
    try {
      const run = await resumeRun(code);
      navigate(routeForStage(code, run.stage));
    } catch (err) {
      setBusy(false);
      if (err instanceof ApiError && err.status === 404) {
        setError("That code doesn't match a run we can find — check the characters?");
      } else if (err instanceof NetworkError) {
        setError("Couldn't reach the tunnel. It may still be warming up — give it a moment.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong. Try again.");
      }
    }
  }

  return (
    <Surface kind="console" subtitle="Resume a run">
      <div className="wt-resume">
        <h1 className="wt-resume__title">Pick up where you left off.</h1>
        <p className="wt-resume__sub">
          Paste your run code. It&rsquo;s your ticket back to a paused or finished run — and since
          everything here is public, it&rsquo;s a locator, not a password.
        </p>

        <form className="wt-resume__form" onSubmit={submit}>
          <label className="wt-resume__label" htmlFor="wt-resume-code">
            Run code
          </label>
          <input
            id="wt-resume-code"
            className="wt-resume__input wt-mono"
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
            placeholder="WT-XXXX-XX"
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            aria-invalid={error != null}
            aria-describedby={error ? "wt-resume-error" : undefined}
          />
          <div className="wt-resume__actions">
            <button
              type="submit"
              className="wt-btn wt-btn--primary"
              disabled={busy || raw.trim() === ""}
            >
              {busy ? "Finding your run…" : "Resume"}
            </button>
            <button type="button" className="wt-btn wt-btn--quiet" onClick={() => navigate("/")}>
              Back
            </button>
          </div>
        </form>

        <div className="wt-resume__status" aria-live="polite">
          {error ? (
            <p id="wt-resume-error" className="wt-resume__error" role="alert">
              {error}
            </p>
          ) : (
            <ColdStartNote />
          )}
        </div>
      </div>
    </Surface>
  );
}
