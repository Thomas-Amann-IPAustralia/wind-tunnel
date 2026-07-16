import type { ParsedOutline } from "../lib/outline";
import type { Sufficiency } from "../lib/types";
import "./SufficiencyBanner.css";

const SECTION_TITLES: Record<string, string> = {
  problem: "Problem",
  solution: "Proposed solution",
  users_stakeholders: "Users and stakeholders",
  data: "Data",
  happy_path: "Happy path",
  alternatives: "Alternatives considered",
  ux_ui: "UX and interface",
  constraints: "Constraints and preferences",
  success_criteria: "Success criteria",
};

/**
 * The sufficiency banner (design §6.2) — unlocking, not gating. It tells the user
 * how ready the outline is and what would sharpen it, but never blocks submission:
 * a public servant can test whenever they like, and a fuller outline simply yields
 * a sharper assessment. When ready, it turns encouraging and points at Submit.
 */
export function SufficiencyBanner({
  sufficiency,
  outline,
}: {
  sufficiency: Sufficiency | null;
  outline: ParsedOutline;
}) {
  if (!sufficiency) return null;

  if (sufficiency.ready) {
    return (
      <div className="wt-suff wt-suff--ready" role="status">
        <span className="wt-suff__mark" aria-hidden="true">
          ✓
        </span>
        <p className="wt-suff__lead">
          Your outline looks ready to test. Submit it whenever you like, or keep refining —
          it&rsquo;s up to you.
        </p>
      </div>
    );
  }

  const missing = sufficiency.missing;
  return (
    <div className="wt-suff wt-suff--refining" role="status">
      <p className="wt-suff__lead">
        {outline.resolved.length === 0
          ? "Start by describing your idea — the interviewer will help the outline take shape."
          : "A few areas would sharpen the assessment. You can test now, but these are worth a moment:"}
      </p>
      {missing.length > 0 ? (
        <ul className="wt-suff__list">
          {missing.map((m) => (
            <li key={`${m.section_id}:${m.reason}`} className="wt-suff__item">
              <span className="wt-suff__section">
                {SECTION_TITLES[m.section_id] ?? m.section_id}
              </span>
              {m.reason !== "unresolved" ? (
                <span className="wt-suff__reason"> — {m.reason}</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
