import { Navigate, useParams } from "react-router-dom";

import { RunCodeChip } from "../components/RunCodeChip";
import { Surface } from "../components/Surface";
import { isValid } from "../lib/runCode";
import "./PhasePlaceholder.css";

/**
 * The Chamber shell (design §7). This phase establishes the dark governance
 * surface and the persistent run-code chip (§7.5). The flagship transparency
 * animation (§7.2) — the pipeline graph + activity log driven by status.json
 * polling — is the next phase and lands in the marked region below, along with
 * the threshold-review (§7.4) and question-checkpoint (§7.3) Console screens the
 * run pauses out to.
 */
export function Chamber() {
  const { code } = useParams();
  if (!code || !isValid(code)) return <Navigate to="/" replace />;

  return (
    <Surface kind="chamber" subtitle="Governance" header={<RunCodeChip code={code} />}>
      <div className="wt-phase">
        <section
          className="wt-phase__placeholder wt-phase__placeholder--chamber"
          aria-label="Pipeline"
        >
          <h2 className="wt-phase__title">The test chamber</h2>
          <p className="wt-phase__lead">
            Your idea goes through the tunnel here — a live graph of the specialist college at work,
            beside a plain-language activity log (design §7.2). The whole governance pipeline is
            built and driven end-to-end on the backend; the animation that renders its status.json
            is the next phase of work.
          </p>
          <p className="wt-phase__meta wt-mono">governance · run {code}</p>
        </section>
      </div>
    </Surface>
  );
}
