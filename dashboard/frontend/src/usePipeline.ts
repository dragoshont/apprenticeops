import { useCallback, useEffect, useRef, useState } from "react";
import { fetchStatus } from "./api";
import type { Status } from "./types";

/**
 * Polls /api/status on a fixed cadence. Simple by design — no websockets, no
 * cache library. Once a run is detected, it pins to that run_id so the view does
 * not jump between runs mid-poll.
 */
export function usePipeline(intervalMs = 4000) {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const pinned = useRef<string | null>(null);
  const busy = useRef(false);

  const tick = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      const s = await fetchStatus(pinned.current);
      if (s.run_id) pinned.current = s.run_id;
      setStatus(s);
      setError(s.state === "error" ? s.error ?? "unknown error" : null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      busy.current = false;
    }
  }, []);

  // Allow controls to force an immediate refresh and re-pin (e.g. after Start).
  const refresh = useCallback(
    (runId?: string | null) => {
      if (runId !== undefined) pinned.current = runId;
      return tick();
    },
    [tick],
  );

  useEffect(() => {
    tick();
    const id = setInterval(() => {
      if (document.visibilityState === "visible") tick();
    }, intervalMs);
    return () => clearInterval(id);
  }, [tick, intervalMs]);

  return { status, error, loading, refresh };
}
