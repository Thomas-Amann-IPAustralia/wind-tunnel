import { useState } from "react";

import type { OutlineSection, ParsedOutline } from "../lib/outline";
import "./OutlineCanvas.css";

/**
 * The live outline canvas (design §6.2) — the right pane. The concept resolving
 * section by section as the conversation proceeds: nine sections, each either
 * resolved (the user's words) or still open (the template's guidance, ghosted).
 * A newly-resolved or amended section settles with a brief highlight (§3.6). Any
 * section is click-to-edit; an edit is tagged `you` (§3.7 provenance).
 *
 * `resolved` is read straight from the outline front-matter — the single
 * deterministic record of completeness (§7.1). The canvas never guesses.
 */
export function OutlineCanvas({
  outline,
  resolvingIds,
  youEdited,
  editingId,
  savingId,
  editError,
  onStartEdit,
  onCancelEdit,
  onSave,
}: {
  outline: ParsedOutline;
  resolvingIds: ReadonlySet<string>;
  youEdited: ReadonlySet<string>;
  editingId: string | null;
  savingId: string | null;
  editError: string | null;
  onStartEdit: (id: string) => void;
  onCancelEdit: () => void;
  onSave: (id: string, body: string) => void;
}) {
  const resolvedCount = outline.resolved.length;
  return (
    <section className="wt-canvas wt-panel" aria-label="Your outline">
      <header className="wt-canvas__head">
        <div>
          <h2 className="wt-canvas__title">{outline.title || "Your idea, taking shape"}</h2>
          {outline.summary ? <p className="wt-canvas__summary">{outline.summary}</p> : null}
        </div>
        <p className="wt-canvas__count wt-mono" aria-live="polite">
          {resolvedCount} / {outline.sections.length} sections
        </p>
      </header>

      <ol className="wt-canvas__sections">
        {outline.sections.map((section) => (
          <SectionCard
            key={section.id}
            section={section}
            resolving={resolvingIds.has(section.id)}
            edited={youEdited.has(section.id)}
            editing={editingId === section.id}
            saving={savingId === section.id}
            error={editingId === section.id ? editError : null}
            onStartEdit={() => onStartEdit(section.id)}
            onCancelEdit={onCancelEdit}
            onSave={(body) => onSave(section.id, body)}
          />
        ))}
      </ol>
    </section>
  );
}

function SectionCard({
  section,
  resolving,
  edited,
  editing,
  saving,
  error,
  onStartEdit,
  onCancelEdit,
  onSave,
}: {
  section: OutlineSection;
  resolving: boolean;
  edited: boolean;
  editing: boolean;
  saving: boolean;
  error: string | null;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSave: (body: string) => void;
}) {
  const classes = [
    "wt-section",
    section.resolved ? "wt-section--resolved" : "wt-section--open",
    resolving ? "wt-section--resolving" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <li className={classes} aria-current={resolving ? "true" : undefined}>
      <div className="wt-section__head">
        <span className="wt-section__marker" aria-hidden="true" />
        <span className="wt-section__label">
          <span className="wt-section__n wt-mono">§{section.n}</span> {section.title}
        </span>
        <span className="wt-section__tags">
          {edited ? <span className="wt-section__you">you</span> : null}
          <span
            className={`wt-section__status wt-section__status--${
              section.resolved ? "resolved" : "open"
            }`}
          >
            {section.resolved ? "resolved" : "not yet"}
          </span>
        </span>
      </div>

      {editing ? (
        <SectionEditor
          initial={section.resolved ? section.body : ""}
          saving={saving}
          error={error}
          onCancel={onCancelEdit}
          onSave={onSave}
        />
      ) : (
        <button
          type="button"
          className="wt-section__body"
          onClick={onStartEdit}
          aria-label={`Edit section ${section.n}: ${section.title}`}
        >
          {section.resolved ? (
            <span className="wt-section__text">{section.body}</span>
          ) : (
            <span className="wt-section__guidance">{stripGuidance(section.body)}</span>
          )}
        </button>
      )}
    </li>
  );
}

function SectionEditor({
  initial,
  saving,
  error,
  onCancel,
  onSave,
}: {
  initial: string;
  saving: boolean;
  error: string | null;
  onCancel: () => void;
  onSave: (body: string) => void;
}) {
  const [value, setValue] = useState(initial);
  return (
    <div className="wt-section__editor">
      <label className="visually-hidden" htmlFor="wt-section-input">
        Section content
      </label>
      <textarea
        id="wt-section-input"
        className="wt-section__input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        rows={3}
        autoFocus
        disabled={saving}
      />
      {error ? (
        <p className="wt-section__error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="wt-section__actions">
        <button
          type="button"
          className="wt-btn wt-btn--primary wt-section__save"
          onClick={() => onSave(value.trim())}
          disabled={saving || value.trim().length === 0}
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <button type="button" className="wt-btn wt-btn--quiet" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
      </div>
    </div>
  );
}

/** The template guidance is wrapped in `*…*`; show it as plain ghosted prose. */
function stripGuidance(body: string): string {
  const trimmed = body.trim();
  const inner = /^\*(.*)\*$/s.exec(trimmed);
  return (inner ? inner[1] : trimmed) || "Not discussed yet.";
}
