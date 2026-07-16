import { useMemo, useState } from "react";

import { ApiError, NetworkError, submitAnswers } from "../lib/api";
import type { AnswerItem, CheckpointGroup, QuestionsPayload } from "../lib/types";
import "./Checkpoint.css";

/**
 * The question checkpoint UI (design §7.3). Up to three questions per specialist,
 * all batched into one pause. Two design goals: make the *attribution* visible
 * (which specialist, and the one-line *why* — the machinery reasoning in the open),
 * and make *skipping* an honest, consequence-clear choice ("Skip this — note it as
 * a gap"). Answer input mirrors the interview: multiple choice with a free-text
 * escape, so the checkpoint feels continuous with the brainstorm. The whole thing
 * is a standard keyboard-navigable form; each specialist group is a labelled region
 * and nothing depends on the amber pause colour to be understood (§7.3, §9).
 *
 * On submit the pipeline resumes (each specialist revises its own sections once);
 * the Chamber's poll picks up the new running state, so this component just needs
 * to send the answers and surface any error.
 */
const SKIP = "__skip__";
const FREE = "__free__";

interface Choice {
  option: string; // an option value, SKIP, FREE, or "" (untouched)
  free: string;
}

export function Checkpoint({
  runCode,
  questions,
  onSubmitting,
}: {
  runCode: string;
  questions: QuestionsPayload;
  onSubmitting?: (busy: boolean) => void;
}) {
  const groups = questions.specialists ?? [];
  const [choices, setChoices] = useState<Record<string, Choice>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setChoice = (id: string, patch: Partial<Choice>) =>
    setChoices((prev) => {
      const base: Choice = prev[id] ?? { option: "", free: "" };
      return { ...prev, [id]: { ...base, ...patch } };
    });

  const { answered, skipped } = useMemo(() => tally(choices), [choices]);

  async function resume() {
    const answers: AnswerItem[] = [];
    const skips: string[] = [];
    for (const [id, c] of Object.entries(choices)) {
      const value = valueOf(c);
      if (c.option === SKIP) skips.push(id);
      else if (value) answers.push({ question_id: id, value });
      // untouched questions are omitted → treated as a gap downstream (§7.3)
    }
    setError(null);
    setBusy(true);
    onSubmitting?.(true);
    try {
      await submitAnswers(runCode, answers, skips);
      // Leave `busy` true: the pipeline is resuming and the Chamber's next poll
      // will swap this screen for the animation. Un-setting would flash the form.
    } catch (err) {
      setBusy(false);
      onSubmitting?.(false);
      setError(describe(err));
    }
  }

  return (
    <div className="wt-checkpoint">
      <header className="wt-checkpoint__head">
        <h2 className="wt-checkpoint__title">The specialists have a few questions</h2>
        <p className="wt-checkpoint__lead">
          Answer what you can. Skipping is fine — it just becomes a noted gap in your assessment.
        </p>
      </header>

      {groups.map((group) => (
        <SpecialistGroup key={group.node_id} group={group} choices={choices} onChoice={setChoice} />
      ))}

      <footer className="wt-checkpoint__foot">
        <p className="wt-checkpoint__tally" aria-live="polite">
          {answered} answered · {skipped} skipped
        </p>
        {error ? (
          <p className="wt-checkpoint__error" role="alert">
            {error}
          </p>
        ) : null}
        <button type="button" className="wt-btn wt-btn--primary" onClick={resume} disabled={busy}>
          {busy ? "Resuming the run…" : "Resume the run"}
        </button>
      </footer>
    </div>
  );
}

function SpecialistGroup({
  group,
  choices,
  onChoice,
}: {
  group: CheckpointGroup;
  choices: Record<string, Choice>;
  onChoice: (id: string, patch: Partial<Choice>) => void;
}) {
  return (
    <section className="wt-checkpoint__group" aria-label={group.friendly}>
      <h3 className="wt-checkpoint__specialist">{group.friendly}</h3>
      {group.why ? <p className="wt-checkpoint__why">{group.why}</p> : null}
      <ol className="wt-checkpoint__questions">
        {group.items.map((q) => {
          const choice = choices[q.question_id] ?? { option: "", free: "" };
          const name = `q-${q.question_id}`;
          return (
            <li key={q.question_id} className="wt-checkpoint__q">
              <p className="wt-checkpoint__prompt">{q.text}</p>
              <div className="wt-checkpoint__options" role="radiogroup" aria-label={q.text}>
                {(q.options ?? []).map((opt) => (
                  <label key={opt} className="wt-checkpoint__opt">
                    <input
                      type="radio"
                      name={name}
                      checked={choice.option === opt}
                      onChange={() => onChoice(q.question_id, { option: opt })}
                    />
                    <span>{opt}</span>
                  </label>
                ))}
                <label className="wt-checkpoint__opt">
                  <input
                    type="radio"
                    name={name}
                    checked={choice.option === FREE}
                    onChange={() => onChoice(q.question_id, { option: FREE })}
                  />
                  <span>Something else</span>
                </label>
                <input
                  type="text"
                  className="wt-checkpoint__free"
                  placeholder="Type your answer…"
                  value={choice.free}
                  onFocus={() => onChoice(q.question_id, { option: FREE })}
                  onChange={(e) => onChoice(q.question_id, { option: FREE, free: e.target.value })}
                  aria-label={`Free-text answer for: ${q.text}`}
                />
                <label className="wt-checkpoint__opt wt-checkpoint__opt--skip">
                  <input
                    type="radio"
                    name={name}
                    checked={choice.option === SKIP}
                    onChange={() => onChoice(q.question_id, { option: SKIP })}
                  />
                  <span>Skip this — note it as a gap</span>
                </label>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function valueOf(c: Choice): string {
  if (c.option === SKIP || c.option === "") return "";
  if (c.option === FREE) return c.free.trim();
  return c.option;
}

function tally(choices: Record<string, Choice>): { answered: number; skipped: number } {
  let answered = 0;
  let skipped = 0;
  for (const c of Object.values(choices)) {
    if (c.option === SKIP) skipped++;
    else if (valueOf(c)) answered++;
  }
  return { answered, skipped };
}

function describe(err: unknown): string {
  if (err instanceof NetworkError)
    return "Couldn't reach the tunnel to submit your answers. Give it a moment and try again.";
  if (err instanceof ApiError) return err.message;
  return "Something went wrong submitting your answers. Please try again.";
}
