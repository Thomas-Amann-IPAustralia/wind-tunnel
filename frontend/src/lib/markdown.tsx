import type { ReactNode } from "react";

/**
 * A minimal, **safe** markdown renderer — builds React elements, never
 * `dangerouslySetInnerHTML`, so pipeline-authored artefact text (derived from
 * untrusted user content, §9.2) can never inject markup. It covers exactly the
 * subset the threshold artefact uses (stages/threshold.py `render_*_markdown`):
 * ATX headings, pipe tables, unordered lists, horizontal rules, blank-line
 * paragraphs, and inline `**bold**` / `*italic*` / `` `code` ``.
 *
 * Risk-rating table cells (Low/Medium/High/Extreme) render as the §3.2 risk chip —
 * colour **plus** label plus shape, so the rating reads in greyscale too.
 */
const RISK_WORDS = new Set(["low", "medium", "high", "extreme"]);

export function Markdown({ source }: { source: string }): ReactNode {
  return <div className="wt-md">{renderBlocks(source)}</div>;
}

function renderBlocks(md: string): ReactNode[] {
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const out: ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (line.trim() === "") {
      i++;
      continue;
    }
    // Horizontal rule
    if (/^\s*---+\s*$/.test(line)) {
      out.push(<hr key={key++} className="wt-md__hr" />);
      i++;
      continue;
    }
    // Heading
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      const level = h[1].length;
      const Tag = `h${Math.min(level + 1, 6)}` as "h2" | "h3" | "h4" | "h5" | "h6";
      out.push(
        <Tag key={key++} className={`wt-md__h wt-md__h--${level}`}>
          {inline(h[2])}
        </Tag>,
      );
      i++;
      continue;
    }
    // Table: a header row followed by a |---| separator
    if (line.includes("|") && i + 1 < lines.length && /^\s*\|?[\s:|-]+\|?\s*$/.test(lines[i + 1])) {
      const start = i;
      const rows: string[] = [];
      while (i < lines.length && lines[i].includes("|")) rows.push(lines[i++]);
      out.push(renderTable(rows, key++));
      if (i === start) i++; // safety: never stall
      continue;
    }
    // List
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ""));
        i++;
      }
      out.push(
        <ul key={key++} className="wt-md__ul">
          {items.map((it, n) => (
            <li key={n}>{inline(it)}</li>
          ))}
        </ul>,
      );
      continue;
    }
    // Paragraph (gather until a blank line or a block starter)
    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !/^(#{1,4}\s|\s*[-*]\s|\s*---+\s*$)/.test(lines[i])
    ) {
      para.push(lines[i]);
      i++;
    }
    out.push(
      <p key={key++} className="wt-md__p">
        {inline(para.join(" "))}
      </p>,
    );
  }
  return out;
}

function renderTable(rows: string[], key: number): ReactNode {
  const cells = (row: string): string[] =>
    row
      .trim()
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((c) => c.trim());
  const header = cells(rows[0]);
  const body = rows.slice(2).map(cells);
  const riskCol = header.findIndex((h) => /risk rating/i.test(h));

  return (
    <div key={key} className="wt-md__table-wrap">
      <table className="wt-md__table">
        <thead>
          <tr>
            {header.map((h, n) => (
              <th key={n}>{inline(h)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((r, ri) => (
            <tr key={ri}>
              {r.map((c, ci) => (
                <td key={ci}>{ci === riskCol ? riskChip(c) : inline(c)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A §3.2 risk chip: the word is the label; a per-level class carries colour and a
 * shape marker, so the rating is never signalled by colour alone (§9). */
function riskChip(text: string): ReactNode {
  const level = text.trim().toLowerCase();
  if (!RISK_WORDS.has(level)) return inline(text);
  return <span className={`wt-chip wt-chip--${level}`}>{text.trim()}</span>;
}

/** Inline spans: `**bold**`, `*italic*`, `` `code` ``. Split on the first match
 * class at a time; the artefact never nests these, so a single pass suffices. */
function inline(text: string): ReactNode {
  const parts: ReactNode[] = [];
  const re = /(\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    if (m[2] !== undefined) parts.push(<strong key={key++}>{m[2]}</strong>);
    else if (m[3] !== undefined) parts.push(<em key={key++}>{m[3]}</em>);
    else if (m[4] !== undefined)
      parts.push(
        <code key={key++} className="wt-mono">
          {m[4]}
        </code>,
      );
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts.length === 1 ? parts[0] : parts;
}
