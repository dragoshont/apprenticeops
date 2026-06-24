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
  security: number | null;
  tok_s: number | null;
  wh: number | null;
  watts: number | null;
  n: number;
}

export interface RunSummary {
  mean_watts: number | null;
  cpu_minutes: number | null;
  energy_wh: number | null;
  quality_overall: number | null;
  security_overall: number | null;
}

export interface ScoreBucket {
  score: number;
  count: number;
}

export interface ClassQuality {
  class: string;
  quality: number;
  n: number;
}

export interface Scores {
  hist: ScoreBucket[];
  by_class: ClassQuality[];
}

export interface AppConfig {
  auth_enabled: boolean;
  user: string | null;
}

export interface Progress {
  inf_done: number;
  inf_total: number;
  judge_done: number;
  judge_total: number;
  units_done: number;
  units_total: number;
  pct: number;
  pct_remaining: number;
  elapsed_s: number | null;
  eta_s: number | null;
  eta_human: string | null;
  rate_per_min: number | null;
}

export interface ModelProgress {
  model: string;
  inf_done: number;
  inf_total: number;
  judge_done: number;
  judge_total: number;
  committed: boolean;
  stage: string;
}

export interface Session {
  run_id: string;
  batch: string;
  user?: string;
  state: PipelineState | string;
  started_at: number | null;
  ended_at: number | null;
  duration_s: number | null;
  models_total: number;
  models_done: number;
  scenarios: number;
  reps: number;
  njudges: number;
  inf_done: number;
  inf_total: number;
  judge_done: number;
  judge_total: number;
  pct: number;
  eta_s?: number | null;
  eta_human?: string | null;
}

export interface Status {
  run_id: string | null;
  ts: number;
  state: PipelineState;
  expect?: number;
  error?: string;
  user?: string;
  markers?: { canceled: boolean; paused: boolean };
  meta?: { run_id?: string; models?: string; batch?: string; expect?: number; started_at?: number };
  progress?: Progress;
  summary?: RunSummary;
  producer?: Producer;
  consumer?: Consumer;
  stages?: string[];
  models?: ModelStage[];
  model_progress?: ModelProgress[];
  pareto?: ParetoPoint[];
  scores?: Scores;
  batches?: Batch[];
  sessions?: Session[];
  nodes?: { home: NodeInfo; ai: NodeInfo };
  runs?: string[];
}

