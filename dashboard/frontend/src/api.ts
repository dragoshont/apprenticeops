import type { InputDetails, Status } from "./types";

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

export async function fetchInputs(modelSet: string, scenarioSet: string, memoryContext: string): Promise<InputDetails> {
  const q = new URLSearchParams({ model_set: modelSet, scenario_set: scenarioSet, memory_context: memoryContext });
  const res = await fetch(`/api/inputs?${q.toString()}`);
  if (!res.ok) throw new Error(`inputs → ${res.status}`);
  return res.json();
}

export const control = {
  start: (modelSet: string, scenarioSet: string, memoryContext: string) =>
    jpost("/api/control/start", { model_set: modelSet, scenario_set: scenarioSet, memory_context: memoryContext }),
  startPhase: (planId: string, phaseId: string, modelSet: string, scenarioSet: string, experimentId?: string | null) =>
    jpost("/api/control/start-phase", { plan_id: planId, phase_id: phaseId, model_set: modelSet, scenario_set: scenarioSet, experiment_id: experimentId ?? null }),
  stop: (runId?: string | null) => jpost("/api/control/stop", { run_id: runId ?? null }),
  pause: (runId?: string | null) => jpost("/api/control/pause", { run_id: runId ?? null }),
  resume: (runId?: string | null) => jpost("/api/control/resume", { run_id: runId ?? null }),
};
