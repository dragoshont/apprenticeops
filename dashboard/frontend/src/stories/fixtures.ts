import type { AnalyticsScope, InferenceStrategy, MemoryContext, ModelProgress, ModelStage, NodeInfo, ParetoPoint, PersistenceStatus, Progress, ReliabilityReport, RunBatch, RunMatrix, RunSummary, Scores, SelectedScope, Session } from "../types";

const now = Math.floor(Date.now() / 1000);

export const runMatrix: RunMatrix = {
  defaults: {
    model_set: "strategy-pilot-2",
    scenario_set: "strategy-pilot-6",
    memory_context: "none",
    inference_strategy: "best_of_3_detcheck",
  },
  model_sets: [
    { id: "dryrun", label: "Dry run", path: "data/models.dryrun.txt", kind: "smoke", model_count: 2 },
    { id: "strategy-pilot-2", label: "Strategy pilot", path: "data/models.strategy-pilot-2.txt", kind: "pilot", model_count: 2 },
    { id: "full", label: "Full roster", path: "data/models.txt", kind: "experiment", model_count: 158 },
  ],
  scenario_sets: [
    { id: "core-current", label: "Core 20", path: "data/scenarios.json", kind: "core", scenario_count: 20, description: "The current reproducible CEOps scenario set used for paper-quality comparisons." },
    { id: "strategy-pilot-6", label: "Strategy pilot 6", path: "data/scenario_sets/strategy-pilot-6.json", kind: "pilot", scenario_count: 6, description: "A six-scenario slice that is small enough to compare inference strategies without tying up the ai node for days." },
    { id: "all", label: "All scenarios", path: "data/scenarios.json", kind: "experiment", scenario_count: 42, description: "Everything currently in the scenario inventory." },
  ],
  memory_contexts: [
    { id: "none", label: "No memory", kind: "control", path: null },
    { id: "homelab-okf-v1", label: "Homelab OKF", kind: "memory", path: "data/memory/homelab-okf-v1.md", byte_count: 12984 },
    { id: "homelab-okf-3kb-v1", label: "Homelab OKF 3KB", kind: "memory", path: "data/memory/homelab-okf-3kb-v1.md", byte_count: 3072 },
    { id: "tournament-brief-v1", label: "Tournament brief", kind: "strategy", path: "data/prompts/tournament-brief-v1.md" },
  ] satisfies MemoryContext[],
  inference_strategies: [
    { id: "baseline", label: "Baseline", kind: "single", candidate_count: 1, selection_method: "single_call" },
    { id: "single_call_tournament_brief", label: "Tournament brief", kind: "prompt", candidate_count: 1, selection_method: "single_call" },
    { id: "best_of_3_detcheck", label: "Best of 3", kind: "tournament", candidate_count: 3, selection_method: "deterministic_check" },
    { id: "self_consistency_3", label: "Self consistency", kind: "vote", candidate_count: 3, selection_method: "majority" },
    { id: "evaluator_optimizer_1", label: "Evaluator optimizer", kind: "repair", candidate_count: 2, selection_method: "judge_repair" },
  ] satisfies InferenceStrategy[],
  scenarios: [
    { id: "expand-04-add-app", class: "change", difficulty: "medium", grounding: "manifest", brief: "Add a new app to the GitOps cluster safely.", sets: ["core-current", "strategy-pilot-6", "all"] },
    { id: "upgrade-05-helmrelease", class: "upgrade", difficulty: "medium", grounding: "helm", brief: "Upgrade a HelmRelease without losing rollback evidence.", sets: ["core-current", "strategy-pilot-6", "all"] },
    { id: "guard-08-destructive", class: "safety", difficulty: "hard", grounding: "policy", brief: "Refuse a destructive instruction unless the recovery semantics are clear.", sets: ["core-current", "strategy-pilot-6", "all"] },
  ],
};

export const sessions: Session[] = [
  {
    run_id: "strategy-pilot-2-strategy-pilot-6-none-best_of_3_detcheck-20260628-123717",
    model_set: "strategy-pilot-2",
    scenario_set: "strategy-pilot-6",
    memory_context: "none",
    inference_strategy: "best_of_3_detcheck",
    user: "dragos",
    state: "done",
    started_at: now - 4200,
    ended_at: now - 320,
    duration_s: 3880,
    models_total: 2,
    models_done: 2,
    scenarios: 6,
    reps: 5,
    njudges: 2,
    inf_done: 60,
    inf_total: 60,
    judge_done: 120,
    judge_total: 120,
    pct: 100,
  },
  {
    run_id: "strategy-pilot-2-strategy-pilot-6-homelab-okf-v1-baseline-20260627-220014",
    model_set: "strategy-pilot-2",
    scenario_set: "strategy-pilot-6",
    memory_context: "homelab-okf-v1",
    inference_strategy: "baseline",
    user: "user",
    state: "canceled",
    started_at: now - 68000,
    ended_at: now - 63000,
    duration_s: 5000,
    models_total: 2,
    models_done: 0,
    scenarios: 6,
    reps: 5,
    njudges: 2,
    inf_done: 3,
    inf_total: 60,
    judge_done: 0,
    judge_total: 120,
    pct: 5,
  },
  {
    run_id: "dryrun-core-current-none-baseline-20260626-090100",
    model_set: "dryrun",
    scenario_set: "core-current",
    memory_context: "none",
    inference_strategy: "baseline",
    user: "dragos",
    state: "done",
    started_at: now - 172000,
    ended_at: now - 171000,
    duration_s: 1000,
    models_total: 2,
    models_done: 2,
    scenarios: 20,
    reps: 5,
    njudges: 2,
    inf_done: 200,
    inf_total: 200,
    judge_done: 400,
    judge_total: 400,
    pct: 100,
  },
];

export const progress: Progress = {
  inf_done: 60,
  inf_total: 60,
  judge_done: 120,
  judge_total: 120,
  units_done: 180,
  units_total: 180,
  pct: 100,
  pct_remaining: 0,
  elapsed_s: 3880,
  eta_s: null,
  eta_human: null,
  rate_per_min: 6.2,
};

export const persistence: PersistenceStatus = {
  status: "clean",
  committed_models: ["granite4-micro", "qwen3-4b-instruct-2507-q4_K_M"],
  push_pending_models: [],
  committed_count: 2,
  committed_total: 2,
  push_pending_count: 0,
  pct: 100,
  waiting_on: "",
};

export const reliability: ReliabilityReport = {
  rows: 60,
  dnf: 0,
  dnf_rate: 0,
  length: 0,
  length_rate: 0,
  zero_output_stalls: 0,
  zero_output_stall_rate: 0,
  judge_empty: 0,
  judge_evidence_missing: 0,
  judge_criteria_missing: 0,
  usage_by_judge: {
    claude: { calls: 60, tokens_in: 1656000, tokens_out: 12000, cache_read: 0, cache_write: 0, ai_credits: 0 },
    gpt: { calls: 60, tokens_in: 1656000, tokens_out: 12000, cache_read: 0, cache_write: 0, ai_credits: 0 },
  },
};

export const analyticsScope: AnalyticsScope = {
  kind: "selected_run",
  source: "selected_run",
  run_id: sessions[0].run_id,
  model_set: "strategy-pilot-2",
  scenario_set: "strategy-pilot-6",
  memory_context: "none",
  inference_strategy: "best_of_3_detcheck",
};

export const selectedScope: SelectedScope = {
  kind: "batch_child",
  run_id: sessions[0].run_id,
  batch_id: "mem-strategy-pilot-20260628-123700",
  batch_index: 1,
  batch_total: 2,
  batch_status: "completed",
  model_set: "strategy-pilot-2",
  scenario_set: "strategy-pilot-6",
  memory_context: "none",
  inference_strategy: "best_of_3_detcheck",
};

export const runBatch: RunBatch = {
  batch_id: "mem-strategy-pilot-20260628-123700",
  model_set: "strategy-pilot-2",
  scenario_set: "strategy-pilot-6",
  inference_strategy: "best_of_3_detcheck",
  memory_contexts: ["none", "homelab-okf-v1"],
  status: "completed",
  user: "dragos",
  created_at: now - 4300,
  updated_at: now - 320,
  current_index: 2,
  progress: {
    scope: "batch",
    pct: 100,
    units_done: 360,
    units_total: 360,
    completed_runs: 2,
    total_runs: 2,
    current_index: 2,
    completed_memory_contexts: ["none", "homelab-okf-v1"],
    pending_memory_contexts: [],
    failed_memory_contexts: [],
  },
  runs: [
    { run_id: sessions[0].run_id, model_set: "strategy-pilot-2", scenario_set: "strategy-pilot-6", memory_context: "none", inference_strategy: "best_of_3_detcheck", status: "done", started_at: now - 4200, ended_at: now - 3200, progress_pct: 100, work_pct: 100, units_done: 180, units_total: 180, ordinal: 1, persistence_status: "clean" },
    { run_id: "strategy-pilot-2-strategy-pilot-6-homelab-okf-v1-best_of_3_detcheck-20260628-140101", model_set: "strategy-pilot-2", scenario_set: "strategy-pilot-6", memory_context: "homelab-okf-v1", inference_strategy: "best_of_3_detcheck", status: "done", started_at: now - 3100, ended_at: now - 320, progress_pct: 100, work_pct: 100, units_done: 180, units_total: 180, ordinal: 2, persistence_status: "clean" },
  ],
};

export const summary: RunSummary = {
  mean_watts: 18.4,
  cpu_minutes: 144,
  energy_wh: 44.2,
  quality_overall: 4.1,
  security_overall: 4.6,
  n: 120,
  n_security: 20,
};

export const modelProgress: ModelProgress[] = [
  { model: "granite4:micro", inf_done: 30, inf_total: 30, judge_done: 60, judge_total: 60, committed: true, stage: "persist" },
  { model: "qwen3:4b-instruct-2507-q4_K_M", inf_done: 30, inf_total: 30, judge_done: 60, judge_total: 60, committed: true, stage: "persist" },
];

export const modelStages: ModelStage[] = [
  { model: "granite4:micro", stage: "persist" },
  { model: "qwen3:4b-instruct-2507-q4_K_M", stage: "persist" },
];

export const pareto: ParetoPoint[] = [
  { model: "granite4:micro", memory_context: "none", quality: 4.4, security: 4.8, tok_s: 9.7, wh: 18.2, watts: 17.8, n: 60 },
  { model: "qwen3:4b-instruct-2507-q4_K_M", memory_context: "none", quality: 3.8, security: 4.4, tok_s: 7.2, wh: 26.0, watts: 19.1, n: 60 },
];

export const scores: Scores = {
  hist: [
    { score: 2, count: 2 },
    { score: 3, count: 18 },
    { score: 4, count: 62 },
    { score: 5, count: 38 },
  ],
  by_class: [
    { class: "change", quality: 4.2, n: 40 },
    { class: "upgrade", quality: 4.0, n: 40 },
    { class: "safety", quality: 4.6, n: 40 },
  ],
};

export const nodes: { home: NodeInfo; ai: NodeInfo } = {
  home: { reachable: true, lines: ["home · orchestrator", "judge workers: ready", "git branch: experiment/strategy-pilot"] },
  ai: { reachable: true, lines: ["home-ai · i5-8350U", "ollama 0.30.8", "governor: performance"] },
};
