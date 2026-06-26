// Mirrors the JSON emitted by scripts/pipeline-status.py.

export type PipelineState = "idle" | "starting" | "pending" | "running" | "paused" | "stopped" | "done" | "canceled" | "failed" | "error";

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

export interface ModelSet {
  id: string;
  label: string;
  path: string;
  kind?: string;
  description?: string;
  model_count?: number | null;
  sha256?: string;
}

export interface ScenarioSet {
  id: string;
  label: string;
  path: string;
  kind?: string;
  description?: string;
  scenario_count?: number | null;
  class_counts?: Record<string, number>;
  difficulty_counts?: Record<string, number>;
  grounding_counts?: Record<string, number>;
  scenario_ids?: string[];
  sha256?: string;
}

export interface MemoryContext {
  id: string;
  label: string;
  path?: string | null;
  kind?: string;
  description?: string;
  byte_count?: number | null;
  sha256?: string | null;
}

export interface ExperimentPhase {
  id: string;
  label: string;
  memory_context: string;
  gate?: string;
}

export interface ExperimentPlan {
  id: string;
  label: string;
  description?: string;
  gate?: string;
  phases: ExperimentPhase[];
}

export interface ExperimentPhaseState extends ExperimentPhase {
  order?: number;
  run_id?: string;
  status?: string;
  started_at?: number;
  gate_checked_at?: number;
  gate_report?: string;
  review?: { verdict?: string; reviewer?: string; notes?: string; reviewed_at?: number };
}

export interface ExperimentState {
  experiment_id: string;
  plan_id: string;
  model_set: string;
  scenario_set: string;
  created_at?: number;
  gate?: string;
  phases: ExperimentPhaseState[];
}

export interface RunBatchItem {
  run_id: string;
  model_set: string;
  scenario_set: string;
  memory_context: string;
  memory_context_file?: string | null;
  status: string;
  started_at?: number | null;
  ended_at?: number | null;
  progress_pct?: number | null;
  work_pct?: number | null;
  units_done?: number | null;
  units_total?: number | null;
  last_progress_at?: number | null;
  ordinal?: number | null;
  persistence_status?: string | null;
}

export interface RunBatchProgress {
  scope: "batch";
  pct: number;
  units_done: number;
  units_total: number;
  completed_runs: number;
  total_runs: number;
  current_index: number;
  current_run_id?: string | null;
  current_memory_context?: string | null;
  completed_memory_contexts: string[];
  running_memory_context?: string | null;
  pending_memory_contexts: string[];
  failed_memory_contexts: string[];
}

export interface RunBatch {
  batch_id: string;
  model_set: string;
  scenario_set: string;
  memory_contexts: string[];
  status: string;
  user?: string;
  created_at?: number;
  updated_at?: number;
  current_index?: number;
  log?: string;
  error?: string;
  progress?: RunBatchProgress;
  runs: RunBatchItem[];
}

export interface ScenarioInventoryRow {
  id: string;
  class?: string | null;
  difficulty?: string | null;
  grounding?: string | null;
  brief?: string | null;
  sets: string[];
}

export interface RunMatrix {
  defaults?: { model_set?: string; scenario_set?: string; memory_context?: string };
  model_sets: ModelSet[];
  scenario_sets: ScenarioSet[];
  memory_contexts?: MemoryContext[];
  experiment_plans?: ExperimentPlan[];
  scenarios: ScenarioInventoryRow[];
}

export interface InputModelRow {
  id: string;
  bracket?: string | null;
}

export interface InputScenarioDetails {
  id: string;
  class?: string | null;
  difficulty?: string | null;
  grounding?: string | null;
  context: string;
  question: string;
  gold_answer: string;
  judge_rubric: string;
  deterministic_checks: Array<{ type?: string; patterns?: string[]; desc?: string }>;
  max_tokens?: number | null;
  timeout_s?: number | null;
  prompt: string;
  prompt_chars: number;
}

export interface InputDetails {
  model_set: ModelSet & { models: InputModelRow[] };
  scenario_set: ScenarioSet;
  memory_context: MemoryContext & { markdown: string; chars: number };
  scenarios: InputScenarioDetails[];
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
  run_id?: string | null;
  model_set?: string | null;
  scenario_set?: string | null;
  memory_context?: string | null;
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
  n: number;
  n_security: number;
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
  scope?: string;
  kind?: string;
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

export interface PersistenceStatus {
  status: "clean" | "retrying_push" | "in_progress" | "incomplete" | "not_expected" | string;
  committed_models: string[];
  push_pending_models: string[];
  committed_count: number;
  committed_total: number;
  push_pending_count: number;
  pct: number;
  waiting_on: string;
}

export interface AnalyticsScope {
  kind: "selected_run" | string;
  source?: "selected_run" | string;
  run_id?: string | null;
  model_set?: string | null;
  scenario_set?: string | null;
  memory_context?: string | null;
}

export interface SelectedScope {
  kind: "idle" | "run" | "batch_child" | string;
  run_id?: string | null;
  batch_id?: string | null;
  batch_index?: number | null;
  batch_total?: number | null;
  batch_status?: string | null;
  batch_current_run_id?: string | null;
  model_set?: string | null;
  scenario_set?: string | null;
  memory_context?: string | null;
  analytics_scope?: string | null;
  state?: string | null;
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
  model_set: string;
  scenario_set: string;
  memory_context?: string;
  historical?: boolean;
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
  meta?: { run_id?: string; models?: string; model_set?: string; scenarios?: string; scenario_set?: string; memory_context?: string; memory_context_file?: string | null; expect?: number; started_at?: number };
  selected_scope?: SelectedScope;
  analytics_scope?: AnalyticsScope;
  persistence?: PersistenceStatus;
  progress?: Progress;
  summary?: RunSummary;
  producer?: Producer;
  consumer?: Consumer;
  stages?: string[];
  models?: ModelStage[];
  model_progress?: ModelProgress[];
  pareto?: ParetoPoint[];
  scores?: Scores;
  run_matrix?: RunMatrix;
  experiments?: ExperimentState[];
  run_batches?: RunBatch[];
  sessions?: Session[];
  nodes?: { home: NodeInfo; ai: NodeInfo };
  runs?: string[];
}

