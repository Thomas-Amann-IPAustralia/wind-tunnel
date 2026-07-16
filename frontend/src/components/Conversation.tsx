import { useEffect, useRef, useState } from "react";

import type { TranscriptTurn } from "../lib/types";
import "./Conversation.css";

/**
 * The scoping conversation (design §6.2) — the left pane of the Brainstorm canvas.
 * A plain, legible dialogue: the interviewer asks, the public servant answers, and
 * every answer flows to the outline on the right. The interviewer opens the
 * exchange only after the first message, so a fresh run shows a warm invitation
 * rather than an empty box.
 */
export function Conversation({
  turns,
  pendingUser,
  thinking,
  onSend,
  disabled,
  error,
}: {
  turns: TranscriptTurn[];
  pendingUser: string | null;
  thinking: boolean;
  onSend: (message: string) => void;
  disabled: boolean;
  error: string | null;
}) {
  const [draft, setDraft] = useState("");
  const logRef = useRef<HTMLDivElement>(null);
  const isEmpty = turns.length === 0 && pendingUser === null;

  // Keep the newest message in view as the exchange grows.
  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns, pendingUser, thinking]);

  function submit() {
    const message = draft.trim();
    if (!message || disabled) return;
    onSend(message);
    setDraft("");
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter inserts a newline (the usual composer idiom).
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <section className="wt-convo wt-panel" aria-label="Scoping conversation">
      <div className="wt-convo__log" ref={logRef} aria-live="polite">
        {isEmpty ? (
          <p className="wt-convo__intro">
            Describe your idea in your own words — what you&rsquo;re trying to do, and where you
            imagine AI helping. There are no wrong answers here; the interviewer will ask follow-up
            questions and your outline will fill in on the right as you go.
          </p>
        ) : (
          turns.map((t, i) => <Bubble key={i} role={t.role} text={t.text} />)
        )}
        {pendingUser !== null ? <Bubble role="user" text={pendingUser} pending /> : null}
        {thinking ? (
          <p className="wt-convo__thinking" aria-label="The interviewer is thinking">
            <span className="wt-convo__dot" />
            <span className="wt-convo__dot" />
            <span className="wt-convo__dot" />
          </p>
        ) : null}
      </div>

      {error ? (
        <p className="wt-convo__error" role="alert">
          {error}
        </p>
      ) : null}

      <div className="wt-convo__composer">
        <label className="visually-hidden" htmlFor="wt-convo-input">
          Your message
        </label>
        <textarea
          id="wt-convo-input"
          className="wt-convo__input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Tell the interviewer about your idea…"
          rows={2}
          disabled={disabled}
        />
        <button
          type="button"
          className="wt-btn wt-btn--primary wt-convo__send"
          onClick={submit}
          disabled={disabled || draft.trim().length === 0}
        >
          Send
        </button>
      </div>
    </section>
  );
}

function Bubble({ role, text, pending }: { role: string; text: string; pending?: boolean }) {
  const who = role === "user" ? "You" : "Interviewer";
  return (
    <div
      className={`wt-bubble wt-bubble--${role}${pending ? " wt-bubble--pending" : ""}`}
      aria-label={`${who} said`}
    >
      <span className="wt-bubble__who">{who}</span>
      <p className="wt-bubble__text">{text}</p>
    </div>
  );
}
