import { useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { StandingDisclaimer } from "./components/StandingDisclaimer";
import { UsageWarningGate } from "./components/UsageWarningGate";
import { BackendStatusProvider, useBackendStatus } from "./context/BackendStatus";
import { Brainstorm } from "./routes/Brainstorm";
import { Chamber } from "./routes/Chamber";
import { Landing } from "./routes/Landing";
import { ResumeScreen } from "./routes/ResumeScreen";

const GATE_KEY = "wt.gate.acknowledged";

/**
 * The app shell. The usage-warning gate (design §4.1) stands before any input,
 * once per session; passing it warms the backend (design §5) so the cold start is
 * honestly surfaced rather than hidden. The standing disclaimer (§4.2) is a
 * permanent, never-dismissible footer on every surface.
 */
export default function App() {
  return (
    <BackendStatusProvider>
      <Gated />
      <StandingDisclaimer />
    </BackendStatusProvider>
  );
}

function Gated() {
  const { ensureWarm } = useBackendStatus();
  const [acknowledged, setAcknowledged] = useState(() => sessionStorage.getItem(GATE_KEY) === "1");

  if (!acknowledged) {
    return (
      <UsageWarningGate
        onAccept={() => {
          sessionStorage.setItem(GATE_KEY, "1");
          setAcknowledged(true);
          // Trigger the Render cold-start wake the instant the gate is passed
          // (design §5) — the health ping is cheap and screens read the warm state.
          ensureWarm();
        }}
      />
    );
  }

  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/resume" element={<ResumeScreen />} />
      <Route path="/run/:code/brainstorm" element={<Brainstorm />} />
      <Route path="/run/:code/chamber" element={<Chamber />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
