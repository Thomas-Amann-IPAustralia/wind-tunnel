import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ColdStartNote } from "../components/ColdStartNote";
import { Surface } from "../components/Surface";
import { useBackendStatus } from "../context/BackendStatus";
import logo from "../img/WindTunnelLogo.png";
import { ApiError, createRun, NetworkError } from "../lib/api";
import "./Landing.css";

/**
 * First contact (design §5). One clear path in — Start a new idea — and a quiet
 * secondary Resume a run. Empty states are written as invitations, not blanks.
 */
export function Landing() {
  const navigate = useNavigate();
  const { ensureWarm } = useBackendStatus();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setError(null);
    setStarting(true);
    ensureWarm(); // surface the cold start honestly while the create call runs
    try {
      const { run_code } = await createRun();
      navigate(`/run/${run_code}/brainstorm`);
    } catch (err) {
      setStarting(false);
      if (err instanceof NetworkError) {
        setError("Couldn't reach the tunnel. It may still be warming up — give it a moment.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong starting a new idea. Try again.");
      }
    }
  }

  return (
    <Surface kind="console">
      <div className="wt-landing">
        <div className="wt-landing__lede">
          <img className="wt-landing__logo" src={logo} alt="Windtunnel" width={112} height={112} />
          <h1 className="wt-landing__title">Test your AI idea before you build it.</h1>
          <p className="wt-landing__sub">
            Sharpen a loose idea into a clear outline, then run it through a college of specialists
            that stress-test it against the DTA&rsquo;s AI impact assessment. You finish holding a
            draft assessment for your subject-matter experts to review.
          </p>
        </div>

        <div className="wt-landing__actions">
          <button
            type="button"
            className="wt-btn wt-btn--primary wt-landing__start"
            onClick={start}
            disabled={starting}
          >
            {starting ? "Starting…" : "Start a new idea"}
          </button>
          <button
            type="button"
            className="wt-btn wt-btn--quiet"
            onClick={() => navigate("/resume")}
          >
            Resume a run
          </button>
        </div>

        <div className="wt-landing__status" aria-live="polite">
          {error ? (
            <p className="wt-landing__error" role="alert">
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
