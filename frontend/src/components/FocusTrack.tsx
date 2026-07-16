import "./FocusTrack.css";

export type FocusStageState = "current" | "upcoming" | "done" | "unavailable";

export interface FocusStage {
  n: number;
  label: string;
  artefact: string; // "→ a structured outline"
  state: FocusStageState;
  optional?: boolean;
  note?: string; // e.g. the conditional-stage "not a fit" line (§6.1)
}

/**
 * The focus track (design §6.1) — the persistent stage progression at the top of
 * the Console. Real numbering because the stages are a real sequence. The current
 * stage is crisp and forward; upcoming stages are present but quiet (at AA, never
 * illegible). Each node states its artefact, so telegraphing covers where you
 * are, what it's for, and what it produces in one glance.
 */
export function FocusTrack({ stages }: { stages: FocusStage[] }) {
  return (
    <ol className="wt-track" aria-label="Brainstorm stages">
      {stages.map((s) => (
        <li key={s.n} className={`wt-track__stage wt-track__stage--${s.state}`}>
          <span className="wt-track__marker" aria-hidden="true" />
          <span className="wt-track__body">
            <span className="wt-track__label">
              {s.n} · {s.label}
              {s.optional ? <span className="wt-track__optional"> optional</span> : null}
            </span>
            <span className="wt-track__artefact">{s.note ?? s.artefact}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}
