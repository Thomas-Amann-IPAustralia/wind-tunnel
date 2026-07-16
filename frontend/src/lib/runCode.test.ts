import { describe, expect, it } from "vitest";
import { ALPHABET, isValid, normalize, validate } from "./runCode";

// This TS module is a hand-kept duplicate of pipeline/runcode.py (CLAUDE.md §6).
// These tests pin the shape so the copy can't silently drift from the Python
// owner — the resume path (§7.5) relies on them agreeing.

describe("runCode", () => {
  it("accepts a well-formed code", () => {
    expect(isValid("WT-7K3D-Q2")).toBe(true);
  });

  it("normalises case and surrounding whitespace", () => {
    expect(normalize("  wt-7k3d-q2 ")).toBe("WT-7K3D-Q2");
    expect(validate("  wt-7k3d-q2 ")).toBe("WT-7K3D-Q2");
  });

  it("rejects the confusable glyphs excluded from the alphabet", () => {
    for (const glyph of ["0", "O", "1", "I", "L", "U", "V"]) {
      expect(ALPHABET.includes(glyph)).toBe(false);
    }
    // A code using an excluded glyph is not valid.
    expect(isValid("WT-0O1I-LV")).toBe(false);
  });

  it("rejects wrong shapes", () => {
    expect(isValid("WT-7K3-Q2")).toBe(false); // group 1 too short
    expect(isValid("WT-7K3D-Q23")).toBe(false); // group 2 too long
    expect(isValid("XX-7K3D-Q2")).toBe(false); // wrong prefix
    expect(isValid("7K3D-Q2")).toBe(false); // no prefix
    expect(validate("nonsense")).toBeNull();
  });
});
