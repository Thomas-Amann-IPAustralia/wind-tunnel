import { useRef } from "react";

import "./BrainstormTabs.css";

/** The three ways a public servant can externalise their idea on the Brainstorm
 * canvas. Each is a genuine input surface, not a downstream artefact of the
 * others — the conversation is one way to say what you want; a proof of concept
 * and a flow map are more expressive ways to say the same thing (design §6.2–6.4). */
export type BrainstormTab = "conversation" | "poc" | "map";

type TabState = "idle" | "ready" | "not-a-fit";

const ORDER: BrainstormTab[] = ["conversation", "poc", "map"];

const LABELS: Record<BrainstormTab, string> = {
  conversation: "Conversation",
  poc: "Proof of concept",
  map: "Flow map",
};

/**
 * The top-of-page tab strip that switches the working surface (design §6.2). The
 * conversation, the proof of concept, and the flow map sit side by side as equal,
 * selectable ways to elaborate the idea — the PoC and the map are promoted here from
 * the foot of the page, so they read as things you *do*, not leftovers you scroll to.
 * The outline canvas stays put on the right whichever tab is active.
 *
 * A standard accessible tablist: arrow keys move between tabs, each tab points at its
 * panel, and the two optional tabs carry a quiet state glyph (a check once produced,
 * an "adjusted" dot when a PoC turned out not to fit) — never colour alone (§9).
 */
export function BrainstormTabs({
  active,
  onChange,
  pocState,
  mapState,
}: {
  active: BrainstormTab;
  onChange: (tab: BrainstormTab) => void;
  pocState: TabState;
  mapState: TabState;
}) {
  const state: Record<BrainstormTab, TabState> = {
    conversation: "idle",
    poc: pocState,
    map: mapState,
  };
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const i = ORDER.indexOf(active);
    const next =
      e.key === "ArrowRight" ? (i + 1) % ORDER.length : (i - 1 + ORDER.length) % ORDER.length;
    const tab = ORDER[next];
    onChange(tab);
    refs.current[tab]?.focus();
  }

  return (
    <div
      className="wt-tabs"
      role="tablist"
      aria-label="How to work on your idea"
      onKeyDown={onKeyDown}
    >
      {ORDER.map((tab) => {
        const selected = tab === active;
        return (
          <button
            key={tab}
            ref={(el) => {
              refs.current[tab] = el;
            }}
            type="button"
            role="tab"
            id={`wt-tab-${tab}`}
            aria-selected={selected}
            aria-controls={`wt-panel-${tab}`}
            tabIndex={selected ? 0 : -1}
            className={`wt-tabs__tab${selected ? " wt-tabs__tab--active" : ""}`}
            onClick={() => onChange(tab)}
          >
            <span className="wt-tabs__label">{LABELS[tab]}</span>
            <Glyph state={state[tab]} />
          </button>
        );
      })}
    </div>
  );
}

function Glyph({ state }: { state: TabState }) {
  if (state === "ready") {
    return (
      <span className="wt-tabs__glyph wt-tabs__glyph--ready" title="Ready">
        <span aria-hidden="true">✓</span>
        <span className="visually-hidden"> — ready</span>
      </span>
    );
  }
  if (state === "not-a-fit") {
    return (
      <span className="wt-tabs__glyph wt-tabs__glyph--adjusted" title="Adjusted">
        <span aria-hidden="true">◇</span>
        <span className="visually-hidden"> — not a fit</span>
      </span>
    );
  }
  return null;
}
