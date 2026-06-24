// Mirrors the JSON emitted by scripts/pipeline-status.py.

export type PipelineState = "idle" | "running" | "paused" | "done" | "error";

export const STAGE_ORDER = [
  "lock",
  "reset",
  "infer",
  "emit",
  "collect",
  "judge",
  "persist",
] as const;
export type Stage = (typeof STAGE_ORDER)[number];

export interface Batch {
  id: string;
  label: string;
  models: string;
  kind?: string;
  desc?: string;
  count?: number | null;
}

export interface NodeInfo {
  reachable: boolean;
  lines: string[];
}

export interface Producer {
  rows: number;
  models_emitted: number;
  run_py_alive: boolean;
  done_models: string[];
  driver_tail: string[];
}

export interface LedgerEvent {
  model?: string;
  stage?: string;
  ts?: number;
  ok?: number | boolean;
  detail?: string;
}

export interface Consumer {
  alive: boolean;
  status: string;
  judged_rows: number;
  judged_models: string[];
  committed_models: string[];
  ledger_tail: LedgerEvent[];
  skips: string[];
  skip_count: number;
}

export interface ModelStage {
  model: string;
  stage: Stage | string;
}

export interface ParetoPoint {
  model: string;
  quality: number | null;
  tok_s: number | null;
  wh: number | null;
  n: number;
}

export interface Status {
  run_id: string | null;
  ts: number;
  state: PipelineState;
  expect?: number;
  error?: string;
  meta?: { run_id?: string; models?: string; batch?: string; expect?: number; started_at?: number };
  producer?: Producer;
  consumer?: Consumer;
  stages?: string[];
  models?: ModelStage[];
  pareto?: ParetoPoint[];
  batches?: Batch[];
  nodes?: { home: NodeInfo; ai: NodeInfo };
  runs?: string[];
}
