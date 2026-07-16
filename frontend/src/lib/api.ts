/**
 * The typed backend client (backend/app.py, TECH_SPEC §7). Every call is a plain
 * fetch against BACKEND_URL; the SPA is stateless and the repo is the durable
 * store, so nothing is cached here beyond the per-run status ETag the caller
 * threads through for cheap polling (§7).
 *
 * Cold start (design §5): the Render backend sleeps when idle and the first
 * request can take ~60s. `warmUp` pings /api/health so the UI can show an honest
 * "warming up the tunnel" panel instead of a hidden delay.
 */

import { BACKEND_URL } from "../config";
import type {
  BrainstormMessageResponse,
  CreateRunResponse,
  EditOutlineResponse,
  ResumeResponse,
  RouteResponse,
  StatusDoc,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** A network failure (backend unreachable / cold / offline) — distinct from an
 * ApiError, which is a real HTTP response the backend chose to send. */
export class NetworkError extends Error {
  constructor(message = "Could not reach the backend.") {
    super(message);
    this.name = "NetworkError";
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  init?: { signal?: AbortSignal },
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}${path}`, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: init?.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new NetworkError();
  }
  if (!res.ok) {
    throw new ApiError(res.status, await errorDetail(res));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** FastAPI puts the human message under `detail`; fall back to the status text. */
async function errorDetail(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
    if (data.detail) return JSON.stringify(data.detail);
  } catch {
    /* not JSON — fall through */
  }
  return res.statusText || `Request failed (${res.status}).`;
}

// -- Cold-start warm-up (design §5) -------------------------------------------

/**
 * Ping /api/health until it answers, so the UI can honestly show the ~60s Render
 * cold start warming up. Resolves when the backend is awake; rejects only if it
 * stays unreachable past `deadlineMs`. `onSlow` fires once we cross ~45s so the
 * copy can add "still warming up — nearly there" (design §5).
 */
export async function warmUp(opts?: {
  deadlineMs?: number;
  onSlow?: () => void;
  signal?: AbortSignal;
}): Promise<void> {
  const deadline = Date.now() + (opts?.deadlineMs ?? 90_000);
  const slowAt = Date.now() + 45_000;
  let firedSlow = false;
  for (let attempt = 0; ; attempt++) {
    if (opts?.signal?.aborted) throw new DOMException("aborted", "AbortError");
    if (!firedSlow && Date.now() >= slowAt) {
      firedSlow = true;
      opts?.onSlow?.();
    }
    try {
      await request<{ ok: boolean }>("GET", "/api/health", undefined, { signal: opts?.signal });
      return;
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") throw err;
      if (err instanceof ApiError) throw err; // a real HTTP error is not "cold"
      if (Date.now() >= deadline) throw new NetworkError("The backend did not wake in time.");
      // NetworkError: still cold/asleep — back off and retry.
      await sleep(Math.min(3000, 500 * 2 ** attempt));
    }
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

// -- Run lifecycle ------------------------------------------------------------

export function createRun(): Promise<CreateRunResponse> {
  return request<CreateRunResponse>("POST", "/api/runs");
}

/** Resume by code (§7.5). A well-formed but unknown code surfaces a plain 404. */
export function resumeRun(runCode: string): Promise<ResumeResponse> {
  return request<ResumeResponse>("POST", `/api/runs/${runCode}/resume`);
}

/**
 * The primary poll (§7). Passes the caller's last ETag as If-None-Match; on 304
 * returns `{ notModified: true }` so the caller keeps its current doc, else the
 * fresh doc plus the new ETag to thread into the next poll.
 */
export async function getStatus(
  runCode: string,
  etag?: string,
): Promise<{ notModified: true } | { notModified: false; doc: StatusDoc; etag: string | null }> {
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/api/runs/${runCode}/status`, {
      headers: etag ? { "If-None-Match": etag } : undefined,
    });
  } catch {
    throw new NetworkError();
  }
  if (res.status === 304) return { notModified: true };
  if (!res.ok) throw new ApiError(res.status, await errorDetail(res));
  const doc = (await res.json()) as StatusDoc;
  return { notModified: false, doc, etag: res.headers.get("ETag") };
}

// -- Brainstorm ---------------------------------------------------------------

export function brainstormMessage(
  runCode: string,
  message: string,
): Promise<BrainstormMessageResponse> {
  return request<BrainstormMessageResponse>("POST", `/api/runs/${runCode}/brainstorm/message`, {
    message,
  });
}

export function editOutline(
  runCode: string,
  patch: { sections?: Record<string, string>; title?: string; summary?: string },
): Promise<EditOutlineResponse> {
  return request<EditOutlineResponse>(
    "POST",
    `/api/runs/${runCode}/brainstorm/edit-outline`,
    patch,
  );
}

export function submitRun(runCode: string): Promise<{ run_id: string; dispatched: boolean }> {
  return request("POST", `/api/runs/${runCode}/submit`);
}

export function thresholdRoute(
  runCode: string,
  outcome: "conclude" | "full",
): Promise<RouteResponse> {
  return request<RouteResponse>("POST", `/api/runs/${runCode}/threshold/route`, { outcome });
}

/** The download proxy URL for an allow-listed artefact (§7). */
export function artefactUrl(runCode: string, name: string): string {
  return `${BACKEND_URL}/api/runs/${runCode}/artefact/${name}`;
}
