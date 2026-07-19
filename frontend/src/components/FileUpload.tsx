import { useRef, useState } from "react";

import type { UploadFormat } from "../lib/types";
import "./FileUpload.css";

/**
 * The Brainstorm file-upload affordance (§7 file upload) — a public servant can upload a
 * file *instead of* chatting. Three formats, detected from the file extension (with a manual
 * override): plain text seeds the outline exactly as a long first message would; a Mermaid
 * `.mmd` becomes the run's flow map; an HTML file becomes the run's PoC.
 *
 * Two acknowledgements gate the upload, and the button stays disabled until they are given:
 * every upload confirms the file carries no sensitive information (the repository is public
 * and world-readable, brief §3), and a Mermaid upload additionally acknowledges it will be
 * treated as starting material, not an outline-derived artefact.
 *
 * Presentational: the file is read to text here (the network never sees a raw file), but the
 * API call and all run state live in the Brainstorm route.
 */

export interface UploadPayload {
  format: UploadFormat;
  content: string;
  filename: string;
  acknowledgeNoSensitive: boolean;
  acknowledgeStartingMaterial: boolean;
}

const ACCEPT = ".txt,.text,.md,.markdown,.mmd,.mermaid,.html,.htm";

const FORMAT_LABEL: Record<UploadFormat, string> = {
  text: "Plain text → seeds your outline",
  mermaid: "Mermaid diagram → becomes your flow map",
  html: "HTML page → becomes your proof of concept",
};

/** Map a filename extension to an upload format; unknown extensions default to plain text
 * (the safe, primary path — its contents just seed the outline). */
function detectFormat(filename: string): UploadFormat {
  const ext = filename.toLowerCase().split(".").pop() ?? "";
  if (ext === "mmd" || ext === "mermaid") return "mermaid";
  if (ext === "html" || ext === "htm") return "html";
  return "text";
}

export function FileUpload({
  uploading,
  error,
  onUpload,
}: {
  uploading: boolean;
  error: string | null;
  onUpload: (payload: UploadPayload) => void;
}) {
  const [open, setOpen] = useState(false);
  const [filename, setFilename] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [format, setFormat] = useState<UploadFormat>("text");
  const [noSensitive, setNoSensitive] = useState(false);
  const [startingMaterial, setStartingMaterial] = useState(false);
  const [readError, setReadError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function reset() {
    setFilename(null);
    setContent("");
    setFormat("text");
    setNoSensitive(false);
    setStartingMaterial(false);
    setReadError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setReadError(null);
    try {
      const text = await file.text();
      setFilename(file.name);
      setContent(text);
      setFormat(detectFormat(file.name));
      setStartingMaterial(false);
    } catch {
      setReadError("Couldn't read that file. Try another, or paste the text into the chat.");
    }
  }

  const isMermaid = format === "mermaid";
  const ready =
    filename !== null &&
    content.trim().length > 0 &&
    noSensitive &&
    (!isMermaid || startingMaterial);

  function submit() {
    if (!ready || !filename) return;
    onUpload({
      format,
      content,
      filename,
      acknowledgeNoSensitive: noSensitive,
      acknowledgeStartingMaterial: startingMaterial,
    });
  }

  if (!open) {
    return (
      <div className="wt-upload wt-upload--collapsed">
        <button
          type="button"
          className="wt-btn wt-btn--quiet wt-upload__toggle"
          onClick={() => setOpen(true)}
        >
          Or upload a file instead
        </button>
      </div>
    );
  }

  return (
    <section className="wt-upload" aria-label="Upload a file">
      <div className="wt-upload__head">
        <h3 className="wt-upload__title">Upload a file</h3>
        <button
          type="button"
          className="wt-upload__close"
          onClick={() => {
            reset();
            setOpen(false);
          }}
          aria-label="Close upload"
        >
          ×
        </button>
      </div>
      <p className="wt-upload__lead">
        Already have something written? Upload it instead of typing. A plain-text document seeds
        your outline; a Mermaid <code>.mmd</code> becomes your flow map; an HTML file becomes your
        proof of concept.
      </p>

      <div className="wt-upload__pick">
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          onChange={onPick}
          disabled={uploading}
          aria-label="Choose a file to upload"
        />
      </div>

      {readError ? (
        <p className="wt-upload__error" role="alert">
          {readError}
        </p>
      ) : null}

      {filename ? (
        <div className="wt-upload__detail">
          <p className="wt-upload__file">
            <span className="wt-upload__file-name">{filename}</span>
          </p>
          <label className="wt-upload__format">
            <span>Treat this file as</span>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value as UploadFormat)}
              disabled={uploading}
            >
              <option value="text">{FORMAT_LABEL.text}</option>
              <option value="mermaid">{FORMAT_LABEL.mermaid}</option>
              <option value="html">{FORMAT_LABEL.html}</option>
            </select>
          </label>

          <label className="wt-upload__ack">
            <input
              type="checkbox"
              checked={noSensitive}
              onChange={(e) => setNoSensitive(e.target.checked)}
              disabled={uploading}
            />
            <span>
              I confirm this file contains <strong>no sensitive information</strong>. This
              repository is public and world-readable.
            </span>
          </label>

          {isMermaid ? (
            <label className="wt-upload__ack">
              <input
                type="checkbox"
                checked={startingMaterial}
                onChange={(e) => setStartingMaterial(e.target.checked)}
                disabled={uploading}
              />
              <span>
                I understand this diagram will be treated as <strong>starting material</strong>, not
                a finished artefact.
              </span>
            </label>
          ) : null}

          {error ? (
            <p className="wt-upload__error" role="alert">
              {error}
            </p>
          ) : null}

          <div className="wt-upload__actions">
            <button
              type="button"
              className="wt-btn wt-btn--primary"
              onClick={submit}
              disabled={!ready || uploading}
            >
              {uploading ? "Uploading…" : "Upload"}
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
