import { Navigate, useParams } from "react-router-dom";

import { FocusTrack } from "../components/FocusTrack";
import type { FocusStage } from "../components/FocusTrack";
import { RunCodeChip } from "../components/RunCodeChip";
import { Surface } from "../components/Surface";
import { isValid } from "../lib/runCode";
import "./PhasePlaceholder.css";

/**
 * The Brainstorm shell (design §6). This phase establishes the Console surface,
 * the run-code chip and the focus track (§6.1); the co-design conversation + live
 * outline canvas (§6.2) is the next phase and slots into the marked region below.
 */
export function Brainstorm() {
  const { code } = useParams();
  if (!code || !isValid(code)) return <Navigate to="/" replace />;

  const stages: FocusStage[] = [
    { n: 1, label: "Scoping interview", artefact: "→ a structured outline", state: "current" },
    {
      n: 2,
      label: "Proof of concept",
      artefact: "→ an HTML preview",
      state: "upcoming",
      optional: true,
    },
    {
      n: 3,
      label: "Flow map",
      artefact: "→ an architecture map",
      state: "upcoming",
      optional: true,
    },
  ];

  return (
    <Surface kind="console" subtitle="Brainstorm" header={<RunCodeChip code={code} />}>
      <div className="wt-phase">
        <FocusTrack stages={stages} />
        <section className="wt-phase__placeholder wt-panel" aria-label="Scoping interview">
          <h2 className="wt-phase__title">Your co-design space</h2>
          <p className="wt-phase__lead">
            This is where the scoping conversation and your live outline canvas will sit — a
            conversation on the left, your outline resolving section by section on the right (design
            §6.2). The interview and sufficiency backends are already built; wiring this canvas to
            them is the next phase of work.
          </p>
          <p className="wt-phase__meta wt-mono">brainstorm · run {code}</p>
        </section>
      </div>
    </Surface>
  );
}
