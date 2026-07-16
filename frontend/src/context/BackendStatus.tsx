/**
 * Backend warm-state, shared so any screen can honestly show the Render cold
 * start (design §5) rather than each hiding it behind its own spinner. `ensureWarm`
 * is idempotent — the gate fires it the instant the user accepts, and screens can
 * re-call it without stacking pings.
 */

import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import { warmUp } from "../lib/api";

export type WarmState = "unknown" | "warming" | "slow" | "ready" | "error";

interface BackendStatus {
  state: WarmState;
  ensureWarm: () => void;
}

const Ctx = createContext<BackendStatus | null>(null);

export function BackendStatusProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WarmState>("unknown");
  const inFlight = useRef(false);

  const ensureWarm = useCallback(() => {
    if (inFlight.current || state === "ready") return;
    inFlight.current = true;
    setState("warming");
    warmUp({ onSlow: () => setState((s) => (s === "warming" ? "slow" : s)) })
      .then(() => setState("ready"))
      .catch(() => setState("error"))
      .finally(() => {
        inFlight.current = false;
      });
  }, [state]);

  const value = useMemo(() => ({ state, ensureWarm }), [state, ensureWarm]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useBackendStatus(): BackendStatus {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useBackendStatus must be used within BackendStatusProvider.");
  return ctx;
}
