import { useCallback, useEffect, useRef, useState } from "react";

import type { TranscriptTurn } from "../lib/types";
import "./Conversation.css";

/** Reveal cadence for the interviewer's replies — a few characters every frame-ish
 * tick, brisk enough to never feel slow but clearly *writing itself out*. */
const REVEAL_STEP = 2;
const REVEAL_INTERVAL_MS = 18;

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

  // Gradual reveal: the interviewer's newest reply writes itself out rather than
  // landing all at once. We animate only a *freshly arrived* reply — detected by the
  // `thinking` true→false transition — so restored history and earlier turns show in
  // full. `stream` holds { index, chars }; when it targets the last turn we render a
  // sliced body plus a caret.
  const [stream, setStream] = useState<{ index: number; chars: number } | null>(null);
  const wasThinking = useRef(thinking);
  const revealTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopReveal = useCallback(() => {
    if (revealTimer.current) {
      clearInterval(revealTimer.current);
      revealTimer.current = null;
    }
  }, []);

  useEffect(() => {
    const justAnswered = wasThinking.current && !thinking;
    wasThinking.current = thinking;
    if (!justAnswered) return;

    const index = turns.length - 1;
    const last = turns[index];
    if (!last || last.role !== "assistant") return;

    // Honour reduced-motion (and environments without matchMedia): show it whole.
    const reduce =
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;

    stopReveal();
    setStream({ index, chars: 0 });
    revealTimer.current = setInterval(() => {
      setStream((prev) => {
        if (!prev) return prev;
        const next = prev.chars + REVEAL_STEP;
        if (next >= last.text.length) {
          stopReveal();
          return null; // done — the bubble now renders its full text
        }
        return { index: prev.index, chars: next };
      });
    }, REVEAL_INTERVAL_MS);
  }, [thinking, turns, stopReveal]);

  useEffect(() => stopReveal, [stopReveal]);

  // Keep the newest message in view as the exchange grows or streams.
  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns, pendingUser, thinking, stream]);

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
          turns.map((t, i) => (
            <Bubble
              key={i}
              role={t.role}
              text={stream && stream.index === i ? t.text.slice(0, stream.chars) : t.text}
              streaming={Boolean(stream && stream.index === i)}
            />
          ))
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

function Bubble({
  role,
  text,
  pending,
  streaming,
}: {
  role: string;
  text: string;
  pending?: boolean;
  streaming?: boolean;
}) {
  const who = role === "user" ? "You" : "Interviewer";
  return (
    <div
      className={`wt-bubble wt-bubble--${role}${pending ? " wt-bubble--pending" : ""}`}
      aria-label={`${who} said`}
    >
      <span className="wt-bubble__who">{who}</span>
      <p className="wt-bubble__text">
        {text}
        {streaming ? <span className="wt-bubble__caret" aria-hidden="true" /> : null}
      </p>
    </div>
  );
}
