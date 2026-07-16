/**
 * Parse the outline markdown the backend serves (`outline_md`) into the shape the
 * canvas renders. The backend (`backend/outline.py`) is the single source of truth
 * for the outline format (§7.1); this is the frontend's *read* of it, never a
 * second writer — every mutation goes back through `/brainstorm/message` or
 * `/edit-outline`, which re-render the file.
 *
 * The nine sections and their ids are the fixed registry (§7.1); we mirror it here
 * (the one unavoidable TS copy, like `runCode.ts` mirrors `runcode.py`) so the
 * canvas can render every section in order even if a section anchor is somehow
 * absent. `resolved` is read from the front-matter — the single deterministic
 * record of completeness (§7.1) — never inferred from the body text.
 */

/** id → heading title, in document order. Mirrors `SECTION_REGISTRY` in
 * `backend/outline.py`; a test pins the ids so the two cannot drift. */
export const SECTION_REGISTRY: ReadonlyArray<readonly [string, string]> = [
  ["problem", "Problem"],
  ["solution", "Proposed solution"],
  ["users_stakeholders", "Users and stakeholders"],
  ["data", "Data"],
  ["happy_path", "Happy path"],
  ["alternatives", "Alternatives considered"],
  ["ux_ui", "UX and interface"],
  ["constraints", "Constraints and preferences"],
  ["success_criteria", "Success criteria"],
];

export const SECTION_IDS: readonly string[] = SECTION_REGISTRY.map(([id]) => id);

export interface OutlineSection {
  id: string;
  /** The section's ordinal (1-based) in the registry — the "§N" the interface shows. */
  n: number;
  /** The registry heading (e.g. "Proposed solution"). */
  title: string;
  /** The body markdown between this section's anchor and the next. For a resolved
   * section this is the user's content; for an unresolved one it is the template's
   * italic guidance prompt. */
  body: string;
  /** True iff the id is in the front-matter `resolved` list (§7.1). */
  resolved: boolean;
}

export interface ParsedOutline {
  title: string;
  summary: string;
  resolved: string[];
  sections: OutlineSection[];
}

const ANCHOR_RE = /^<!-- section: ([a-z_]+) -->[ \t]*$/gm;

/**
 * Parse `outline_md`. Robust to both the canonical rendered form (what the backend
 * always serves — front-matter values are JSON) and the raw template form
 * (values with trailing `# …` comments), and to a missing anchor (that section
 * falls back to an empty, unresolved body rather than vanishing).
 */
export function parseOutline(md: string): ParsedOutline {
  const { frontmatter, rest } = splitFrontmatter(md);
  const title = readString(frontmatter, "title");
  const summary = readString(frontmatter, "summary");
  const resolved = readResolved(frontmatter);
  const resolvedSet = new Set(resolved);

  const bodies = extractBodies(rest);

  const sections: OutlineSection[] = SECTION_REGISTRY.map(([id, sectionTitle], i) => ({
    id,
    n: i + 1,
    title: sectionTitle,
    body: (bodies.get(id) ?? "").trim(),
    resolved: resolvedSet.has(id),
  }));

  return { title, summary, resolved, sections };
}

// -- front-matter -------------------------------------------------------------

/** Split the leading `---\n…\n---\n` block from the section body. Anything before
 * the first `---` (the template's lead comment) is discarded. */
function splitFrontmatter(md: string): { frontmatter: Record<string, string>; rest: string } {
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/m.exec(md);
  if (!match) return { frontmatter: {}, rest: md };
  const frontmatter: Record<string, string> = {};
  for (const line of match[1].split(/\r?\n/)) {
    const kv = /^([A-Za-z_]+):\s?(.*)$/.exec(line);
    if (kv) frontmatter[kv[1]] = kv[2];
  }
  return { frontmatter, rest: md.slice(match.index + match[0].length) };
}

/** Values are emitted by the backend as `json.dumps(...)`, so they are JSON. Fall
 * back to a comment-stripped raw string for the template form (`""  # comment`). */
function readString(fm: Record<string, string>, key: string): string {
  const raw = fm[key];
  if (raw === undefined) return "";
  const parsed = tryJson(raw);
  if (typeof parsed === "string") return parsed;
  return stripComment(raw).replace(/^"|"$/g, "");
}

function readResolved(fm: Record<string, string>): string[] {
  const raw = fm["resolved"];
  if (raw === undefined) return [];
  const parsed = tryJson(stripComment(raw));
  if (Array.isArray(parsed)) {
    // Sanitise to known ids in registry order (mirrors the backend's `resolved`
    // accessor) so a malformed list can never surface an unknown id.
    const present = new Set(parsed.map((s) => String(s)));
    return SECTION_IDS.filter((id) => present.has(id));
  }
  return [];
}

function tryJson(raw: string): unknown {
  try {
    return JSON.parse(raw.trim());
  } catch {
    return undefined;
  }
}

/** Drop a trailing ` # …` comment (template front-matter carries them). Only used
 * on the fallback path — a JSON string that happens to contain `#` is parsed as
 * JSON first and never reaches here. */
function stripComment(raw: string): string {
  return raw.replace(/\s+#.*$/, "").trim();
}

// -- section bodies -----------------------------------------------------------

/** id → the markdown between that section's anchor and the next anchor (the
 * heading line stripped). */
function extractBodies(rest: string): Map<string, string> {
  const bodies = new Map<string, string>();
  const anchors: Array<{ id: string; contentStart: number; matchStart: number }> = [];
  ANCHOR_RE.lastIndex = 0;
  for (let m = ANCHOR_RE.exec(rest); m !== null; m = ANCHOR_RE.exec(rest)) {
    anchors.push({ id: m[1], contentStart: m.index + m[0].length, matchStart: m.index });
  }
  anchors.forEach((anchor, i) => {
    // The body runs to the *start* of the next anchor, so the next anchor comment
    // is never swallowed into this body.
    const end = i + 1 < anchors.length ? anchors[i + 1].matchStart : rest.length;
    const block = rest.slice(anchor.contentStart, end);
    // Strip the leading `## N. …` heading line; keep the rest as the body.
    bodies.set(anchor.id, block.replace(/^\s*##[^\n]*\n?/, ""));
  });
  return bodies;
}
