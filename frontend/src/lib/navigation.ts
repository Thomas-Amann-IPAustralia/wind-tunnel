/**
 * Where a run belongs on screen, given its stage. The resume flow (§7.5) drops
 * the user back at the exact checkpoint: a run still in Brainstorm returns to the
 * canvas; everything past submission lives on the Chamber (which itself routes to
 * the threshold-review / checkpoint Console screens as those land — next phase).
 *
 * Keyed on the run.json Stage value (statefile.Stage, a StrEnum), so it stays
 * correct regardless of phase.
 */
export function routeForStage(runCode: string, stage: string): string {
  if (stage === "BRAINSTORM") return `/run/${runCode}/brainstorm`;
  return `/run/${runCode}/chamber`;
}
