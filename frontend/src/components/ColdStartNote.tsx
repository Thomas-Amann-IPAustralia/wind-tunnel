import { useBackendStatus } from "../context/BackendStatus";
import "./ColdStartNote.css";

/**
 * Honest warm-up copy for the Render cold start (design §5). Not a fake spinner
 * implying imminence — it names the ~60s first-time wait, and after ~45s adds
 * "still warming up". Renders nothing once the backend is ready or was never cold.
 */
export function ColdStartNote() {
  const { state } = useBackendStatus();
  if (state !== "warming" && state !== "slow" && state !== "error") return null;

  if (state === "error") {
    return (
      <p className="wt-coldstart wt-coldstart--error" role="status">
        Can&rsquo;t reach the tunnel right now. Check your connection and try again in a moment.
      </p>
    );
  }

  return (
    <p className="wt-coldstart" role="status">
      <span className="wt-coldstart__pip" aria-hidden="true" />
      {state === "slow"
        ? "Still warming up — nearly there."
        : "Warming up the tunnel — this can take up to a minute the first time."}
    </p>
  );
}
