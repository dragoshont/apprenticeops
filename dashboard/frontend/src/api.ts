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

export async function fetchConfig(): Promise<{ auth_enabled: boolean; user: string | null }> {
  const res = await fetch("/api/config");
  if (!res.ok) throw new Error(`config → ${res.status}`);
  return res.json();
}

export const control = {
  start: (modelSet: string, scenarioSet: string) =>
    jpost("/api/control/start", { model_set: modelSet, scenario_set: scenarioSet }),
  stop: (runId?: string | null) => jpost("/api/control/stop", { run_id: runId ?? null }),
  pause: (runId?: string | null) => jpost("/api/control/pause", { run_id: runId ?? null }),
  resume: (runId?: string | null) => jpost("/api/control/resume", { run_id: runId ?? null }),
};
