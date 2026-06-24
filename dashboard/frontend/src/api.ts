import type { Status } from "./types";

async function jpost(path: string, body?: unknown) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

export async function fetchStatus(runId?: string | null): Promise<Status> {
  const q = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  const res = await fetch(`/api/status${q}`);
  if (!res.ok) throw new Error(`status → ${res.status}`);
  return res.json();
}

export const control = {
  start: (batch: string) => jpost("/api/control/start", { batch }),
  stop: () => jpost("/api/control/stop"),
  pause: () => jpost("/api/control/pause"),
  resume: (runId?: string | null) => jpost("/api/control/resume", { run_id: runId ?? null }),
};
