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

/** One batched checkpoint question, grouped by specialist (§6.4, design §7.3). */
export interface CheckpointQuestion {
  question_id: string;
  prompt: string;
  options?: string[];
}

export interface CheckpointGroup {
  node_id: string;
  friendly: string;
  why: string;
  items: CheckpointQuestion[];
}

export interface QuestionsPayload {
  batch_id?: string;
  groups?: CheckpointGroup[];
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
  expected_ranges: Record<string, unknown> | null;
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

/** GET /brainstorm — the co-design state a page load / resume restores (§7.1).
 * `sufficiency` is null once the run has left BRAINSTORM (the outline is frozen);
 * `stage` then tells the SPA to redirect the stale link on to the Chamber. */
export interface BrainstormState {
  outline_md: string;
  transcript: TranscriptTurn[];
  sufficiency: Sufficiency | null;
  stage: string;
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
