import { useEffect, useRef, useState } from "react";

import { ApiError, getStatus, NetworkError } from "../lib/api";
import type { StatusDoc } from "../lib/types";

/**
 * The Chamber's poll (design §7.2). One poll fully determines the visible state
 * (CLAUDE.md §3) — the status doc carries the whole-graph `nodes` map and the whole
 * log every time — so this hook simply holds the latest doc; there is nothing to
 * accumulate across polls. It threads the ETag for cheap 304s, tracks how long
 * since the state actually changed (the honest-staleness backbone, §7.2.5), and
 * keeps the last good doc through a transient network blip rather than blanking.
 *
 * Polling stops once the run is terminal (`complete` / `failed`) — the state can't
 * change again, so continuing would be dishonest churn.
 */
export interface StatusPoll {
  doc: StatusDoc | null;
  /** A hard error (a real 4xx like an unknown code) — distinct from a transient
   * network blip, which is swallowed so the last good doc stays on screen. */
  error: string | null;
  /** Seconds since the status last actually changed (client wall-clock). Drives
   * "still working — last update Ns ago" (§7.2.5). Null until the first doc. */
  staleSeconds: number | null;
  /** True while a network blip is being ridden out (backend cold / offline). */
  offline: boolean;
}

const POLL_MS = 4000;

export function useStatusPoll(runCode: string | undefined, active: boolean): StatusPoll {
  const [doc, setDoc] = useState<StatusDoc | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [staleSeconds, setStaleSeconds] = useState<number | null>(null);

  const etag = useRef<string | undefined>(undefined);
  const lastChange = useRef<number | null>(null);

  useEffect(() => {
    if (!runCode || !active) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function poll() {
      try {
        const res = await getStatus(runCode!, etag.current);
        if (cancelled) return;
        setOffline(false);
        if (!res.notModified) {
          etag.current = res.etag ?? undefined;
          lastChange.current = Date.now();
          setDoc(res.doc);
        }
        const terminal = res.notModified
          ? isTerminal(doc)
          : res.doc.overall_state === "complete" || res.doc.overall_state === "failed";
        if (!terminal) schedule();
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError) {
          setError(err.message); // a real HTTP error (e.g. unknown code) — stop.
          return;
        }
        if (err instanceof NetworkError) {
          setOffline(true); // cold/offline — keep the last doc and retry.
          schedule();
          return;
        }
        setError("Something went wrong while watching this run.");
      }
    }

    function schedule() {
      timer = setTimeout(poll, POLL_MS);
    }

    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
    // `doc` is intentionally excluded: it changes on every fresh poll and would
    // otherwise restart the loop. The closure reads the latest via the terminal
    // check on the freshly-fetched res, so correctness does not depend on it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runCode, active]);

  // Tick the staleness clock once a second while a doc is on screen (§7.2.5).
  useEffect(() => {
    if (lastChange.current === null) return;
    const tick = () =>
      setStaleSeconds(Math.floor((Date.now() - (lastChange.current ?? Date.now())) / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [doc]);

  return { doc, error, staleSeconds, offline };
}

function isTerminal(doc: StatusDoc | null): boolean {
  return doc?.overall_state === "complete" || doc?.overall_state === "failed";
}
