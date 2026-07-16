/**
 * Run-code format — the one unavoidable TS copy of `pipeline/runcode.py`
 * (CLAUDE.md §6: "The frontend keeps the one unavoidable TS copy"). The resume
 * input (§7.5) validates locally before hitting the network, so this must match
 * the Python owner exactly. If `runcode.py` changes the alphabet or shape, change
 * this in the same breath.
 *
 * The alphabet excludes easily-confused glyphs (0/O, 1/I/L, U/V) so a code
 * survives being read aloud across a demo room or retyped (design §7.5).
 */

export const ALPHABET = "ABCDEFGHJKMNPQRSTWXYZ23456789";
export const PREFIX = "WT";
const GROUP1_LEN = 4;
const GROUP2_LEN = 2;

// ^WT-XXXX-XX over the alphabet. Anchored; uppercase only.
const RUN_CODE_RE = new RegExp(
  `^${PREFIX}-[${ALPHABET}]{${GROUP1_LEN}}-[${ALPHABET}]{${GROUP2_LEN}}$`,
);

/** Uppercase and trim a candidate code (mirrors runcode.normalize). */
export function normalize(raw: string): string {
  return raw.trim().toUpperCase();
}

/** True iff `code` is exactly a normalised, well-formed run code. Strict — does
 * not normalise first (mirrors runcode.is_valid). */
export function isValid(code: string): boolean {
  return RUN_CODE_RE.test(code);
}

/**
 * Normalise `raw` and return the canonical code, or null if malformed. The
 * resume path normalises first, then reports an invalid *normalised* code
 * (design §7.5 gives a plain error, never a raw failure).
 */
export function validate(raw: string): string | null {
  const code = normalize(raw);
  return isValid(code) ? code : null;
}
