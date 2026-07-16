/**
 * Wire types — the shapes the backend actually returns (backend/app.py) and
 * writes into status.json (pipeline/status.py §6). Kept faithful to those owners;
 * this is the frontend's read of the contract, not a second source of truth.
 */

// -- status.json (§6, design §7.2.6) ------------------------------------------

/** Node state over the fixed topology (§6.2). One poll sets the whole graph. */
export type NodeState = "pending" | "active" | "waiting_user" | "complete" | "failed";

/** The controlled event-type vocabulary (design §7.2.6, status.py §6.3). */
export type EventType =
  | "stage_started"
  | "retrieval"
  | "drafting"
  | "question_raised"
  | "revision"
  | "review_finding"
  | "stage_complete"
  | "heartbeat"
  | "error";

export interface StatusEvent {
  id: string; // stable, monotonic evt_NNNNNN — the frontend dedupes on this
  ts: string;
  agent: string; // a node id or its friendly name
  type: EventType;
  detail: string;
  ref?: Record<string, unknown>;
}

export type OverallState = "created" | "running" | "paused" | "failed" | "complete";
export type Phase = "brainstorm" | "threshold" | "full";

/** One batched checkpoint question (§6.4, design §7.3). Faithful to what the
 * pipeline writes (stages/full.py `_build_questions_payload`, specialist.py): the
 * field is `text`, and `options` may be null (a free-text-only question). */
export interface CheckpointQuestion {
  question_id: string;
  text: string;
  options?: string[] | null;
}

/** A specialist's batch of questions — grouped by the asking node, with its
 * friendly name and the one-line *why* the design surfaces as the trust moment. */
export interface CheckpointGroup {
  node_id: string;
  friendly: string;
  why: string;
  items: CheckpointQuestion[];
}

/** The `questions` payload the pipeline attaches while paused at the checkpoint.
 * Grouping key is `specialists` (status.py / stages/full.py — the owners); this
 * mirrors them, it is not a second source of truth (CLAUDE.md §3). */
export interface QuestionsPayload {
  batch_id?: string;
  specialists?: CheckpointGroup[];
  counts?: Record<string, number>;
}

/** The failure payload (§6.5, design §7.2.4) — `technical` is behind a disclosure. */
export interface FailurePayload {
  stage: string;
  message: string;
  run_code?: string;
  technical?: string;
}

export interface StatusDoc {
  schema_version: number;
  run_id: string;
  run_code: string;
  phase: Phase;
  overall_state: OverallState;
  updated_at: string;
  nodes: Record<string, NodeState>;
  log: StatusEvent[];
  log_cursor?: number;
  questions: QuestionsPayload | null;
  failure: FailurePayload | null;
  /** Per-phase `[low, high]` second ranges (status.py `load_expected_ranges`),
   * keyed by phase (`threshold` | `full`) — the honest wait copy (§7.2.5). */
  expected_ranges: Record<string, [number, number]> | null;
}

// -- Brainstorm / outline (§7.1) ----------------------------------------------

export interface SufficiencyIssue {
  section_id: string;
  reason: string;
}

/** `{ready, missing:[{section_id, reason}]}` (sufficiency.py). */
export interface Sufficiency {
  ready: boolean;
  missing: SufficiencyIssue[];
}

/** The canvas delta the outline animates (`outline.py` OutlineUpdate.delta). */
export interface OutlineDelta {
  updated: string[];
  newly_resolved: string[];
  title_changed: boolean;
}

// -- Endpoint responses -------------------------------------------------------

export interface CreateRunResponse {
  run_id: string;
  run_code: string;
}

/** One line of the interview transcript (`backend/brainstorm/transcript.py`). */
export interface TranscriptTurn {
  role: "user" | "assistant";
  text: string;
  ts: string;
}

/** The feasibility verdict (backend/brainstorm/feasibility.py) — whether a static
 * PoC would help, and the honest reason shown either way (§6.1 conditional stage). */
export interface FeasibilityVerdict {
  feasible: boolean;
  reason: string;
}

/** GET /brainstorm `artefacts` — which optional artefacts (§6.3/§6.4) already exist,
 * so a page load / resume restores the focus track and re-displays them (§7.5). Only
 * present while the run is still at BRAINSTORM (a submitted run redirects). */
export interface BrainstormArtefacts {
  poc: boolean;
  flow_map: boolean;
  flow_map_svg: boolean;
  feasibility: FeasibilityVerdict | null;
}

/** GET /brainstorm — the co-design state a page load / resume restores (§7.1).
 * `sufficiency` is null once the run has left BRAINSTORM (the outline is frozen);
 * `stage` then tells the SPA to redirect the stale link on to the Chamber.
 * `artefacts` is absent on that frozen branch (the SPA redirects before reading it). */
export interface BrainstormState {
  outline_md: string;
  transcript: TranscriptTurn[];
  sufficiency: Sufficiency | null;
  stage: string;
  artefacts?: BrainstormArtefacts;
}

/** POST /poc — the feasibility gate, then either a PoC (`produced: "poc"`) or, if a
 * static mock is not a fit, the flow map instead (`produced: "map"`, with `mermaid`
 * source to render). Either way `reason` is the honest one-line why (§6.1). */
export interface PocResponse {
  produced: "poc" | "map";
  reason: string;
  mermaid?: string;
}

/** POST /flow-map — Mermaid source for the SPA to render client-side (CLAUDE.md §9). */
export interface FlowMapResponse {
  produced: "map";
  mermaid: string;
}

/** POST /flow-map/svg — the SPA's client-rendered SVG, committed for the report. */
export interface FlowMapSvgResponse {
  run_id: string;
  committed: boolean;
}

export interface BrainstormMessageResponse {
  assistant_message: string;
  outline_md: string;
  outline_delta: OutlineDelta | null;
  sufficiency: Sufficiency;
  stage: string;
}

export interface EditOutlineResponse {
  outline_md: string;
  outline_delta: OutlineDelta | null;
  sufficiency: Sufficiency;
  stage: string;
}

export interface ResumeResponse {
  run_id: string;
  stage: string;
  stage_status: string;
  phase: string;
  status: StatusDoc;
}

export interface RouteResponse {
  run_id: string;
  outcome: "conclude" | "full";
  stage: string;
  dispatched?: boolean;
}

/** One answered checkpoint question — the shape POST /answers expects
 * (backend AnswerItem: `question_id` + free-text/MC `value`). */
export interface AnswerItem {
  question_id: string;
  value: string;
}

export interface AnswersResponse {
  run_id: string;
  answered: number;
  skipped: number;
  dispatched: boolean;
}

export interface ReviseResponse {
  run_id: string;
  revision: number;
  dispatched: boolean;
}
