import { Terminal } from "lucide-react";
import type { AnalyticsScope, Consumer, ModelProgress, ModelStage, PersistenceStatus, Progress, ReliabilityReport, RunBatch, RunBatchItem, RunSummary, Scores, SelectedScope, NodeInfo, ParetoPoint } from "../types";
import { ActivityFeed, SkipsFeed } from "./Feed";
import { ClassQuality, ParetoLeaderboard, PowerLeaderboard, QualityLeaderboard, RunSummaryCard, ScoreDistribution } from "./Charts";
import { InputInspector } from "./InputInspector";
import { ModelBars } from "./ModelBars";
import { NodeCards } from "./NodeCards";
import { ParetoChart } from "./ParetoChart";
import { PipelineFlow } from "./PipelineFlow";
import { RunProgress } from "./RunProgress";
import { Bar, StatePill } from "./ui";

export function CurrentRunSection({
  title,
  description,
  state,
  live,
  displayBatch,
  selectedRunId,
  selectedRunInBatch,
  batchNotice,
  selectedScope,
  analyticsScope,
  persistence,
  user,
  progress,
  reliability,
  inputSelection,
  consumer,
  producerAlive,
  models,
  modelProgress,
  nodes,
  summary,
  pareto,
  scores,
  backToLatestRunId,
  onBackToLatest,
  onSelectRun,
}: {
  title: string;
  description: string;
  state: string;
  live: boolean;
  displayBatch?: RunBatch | null;
  selectedRunId: string | null;
  selectedRunInBatch?: RunBatchItem;
  batchNotice?: string | null;
  selectedScope?: SelectedScope;
  analyticsScope?: AnalyticsScope;
  persistence?: PersistenceStatus;
  user: string;
  progress?: Progress;
  reliability?: ReliabilityReport | null;
  inputSelection: { modelSet: string; scenarioSet: string; memoryContext: string; inferenceStrategy?: string };
  consumer?: Consumer;
  producerAlive: boolean;
  models: ModelStage[];
  modelProgress: ModelProgress[];
  nodes?: { home: NodeInfo; ai: NodeInfo };
  summary?: RunSummary;
  pareto: ParetoPoint[];
  scores?: Scores;
  backToLatestRunId?: string | null;
  onBackToLatest: (runId?: string | null) => void;
  onSelectRun: (runId?: string | null) => void;
}) {
  return (
    <section id="current-run" className="scroll-mt-24 space-y-4 rounded-xl border border-line bg-panel2/20 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <div>
          <h2 className="text-sm font-semibold text-fg">{title}</h2>
          <p className="mt-0.5 text-[11px] text-faint">{description}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {backToLatestRunId && (
            <button
              type="button"
              onClick={() => onBackToLatest(backToLatestRunId)}
              className="btn rounded-lg px-3 py-1.5 text-xs"
            >
              Back to latest
            </button>
          )}
          <StatePill state={state} size="sm" />
        </div>
      </div>

      {displayBatch && <BatchOverview batch={displayBatch} selectedRunId={selectedRunId} onSelect={onSelectRun} />}

      <ScopeHeader scope={selectedScope} analyticsScope={analyticsScope} persistence={persistence} user={user} selectedRunStatus={state} selectedBatchRun={selectedRunInBatch} batchNotice={batchNotice} />

      <RunProgress progress={progress} live={live} scope={analyticsScope} persistence={persistence} batchNotice={batchNotice} reliability={reliability ?? null} />

      <InputInspector selection={inputSelection} title={`${title} inputs`} />

      {live && (
        <>
          {consumer?.status && (
            <div className="flex items-center gap-2 rounded-xl border border-line bg-panel/50 px-4 py-2 font-mono text-xs text-muted">
              <Terminal className="h-3.5 w-3.5 text-good" />
              <span className="truncate">{consumer.status}</span>
            </div>
          )}
          <PipelineFlow models={models} producerAlive={producerAlive} consumerAlive={consumer?.alive ?? false} />
        </>
      )}

      <RunSummaryCard summary={summary} scope={analyticsScope} />

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <ModelBars models={modelProgress} />
        <div className="space-y-4">
          <NodeCards nodes={nodes} />
          {live && <ActivityFeed consumer={consumer} />}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ParetoChart data={pareto} scope={analyticsScope} />
        <ParetoLeaderboard pareto={pareto} scope={analyticsScope} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <QualityLeaderboard pareto={pareto} scope={analyticsScope} />
        <PowerLeaderboard pareto={pareto} scope={analyticsScope} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ScoreDistribution scores={scores} scope={analyticsScope} />
        <ClassQuality scores={scores} scope={analyticsScope} />
      </div>

      <SkipsFeed consumer={consumer} />
    </section>
  );
}

function persistenceLabel(persistence?: PersistenceStatus) {
  if (!persistence) return "persistence unknown";
  if (persistence.status === "clean") return `persisted ${persistence.committed_count}/${persistence.committed_total}`;
  if (persistence.status === "retrying_push") return `push retrying · ${persistence.push_pending_count} pending`;
  if (persistence.status === "not_expected") return "persistence not expected";
  return `${persistence.status} · ${persistence.committed_count}/${persistence.committed_total} pushed`;
}

function ScopeHeader({
  scope,
  analyticsScope,
  persistence,
  user,
  selectedRunStatus,
  selectedBatchRun,
  batchNotice,
}: {
  scope?: SelectedScope;
  analyticsScope?: AnalyticsScope;
  persistence?: PersistenceStatus;
  user: string;
  selectedRunStatus: string;
  selectedBatchRun?: RunBatchItem;
  batchNotice?: string | null;
}) {
  return (
    <div className="rounded-xl border border-line bg-panel/60 px-4 py-3" aria-live="polite">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-mono text-fg">{scope?.run_id ?? analyticsScope?.run_id ?? "selected run"}</span>
        <StatePill state={selectedRunStatus} size="sm" />
        {selectedBatchRun?.persistence_status && <StatePill state={selectedBatchRun.persistence_status} size="sm" />}
      </div>
      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
        {scope?.batch_id && (
          <span>
            batch child {scope.batch_index}/{scope.batch_total} · batch {scope.batch_status}
          </span>
        )}
        <span>{scope?.model_set ?? analyticsScope?.model_set ?? "models"} × {scope?.scenario_set ?? analyticsScope?.scenario_set ?? "scenarios"}</span>
        <span className="font-mono">memory_context={scope?.memory_context ?? analyticsScope?.memory_context ?? "none"}</span>
        <span className="font-mono">inference_strategy={scope?.inference_strategy ?? analyticsScope?.inference_strategy ?? "baseline"}</span>
        <span>{persistenceLabel(persistence)}</span>
        <span className="text-faint">by {user}</span>
      </div>
      <div className="mt-1 text-[11px] text-faint">
        Analytics below are scoped to this selected child run, not to the whole memory batch.
      </div>
      {batchNotice && <div className="mt-1 text-[11px] text-warn">{batchNotice}</div>}
    </div>
  );
}

function BatchOverview({ batch, selectedRunId, onSelect }: { batch: RunBatch; selectedRunId: string | null; onSelect: (runId?: string | null) => void }) {
  const progress = batch.progress;
  return (
    <section className="rounded-xl border border-line bg-panel2/40 p-4" role="status" aria-atomic="true">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-fg">
            Current experiment
            <StatePill state={batch.status} size="sm" />
          </div>
          <div className="mt-1 font-mono text-[11px] text-faint">{batch.batch_id}</div>
          <div className="mt-1 text-xs text-muted">
            {batch.model_set} × {batch.scenario_set} × {batch.inference_strategy ?? "baseline"} · {progress?.completed_runs ?? 0}/{progress?.total_runs ?? batch.runs.length} memory contexts complete
            {progress?.current_memory_context ? ` · current memory_context=${progress.current_memory_context}` : ""}
          </div>
        </div>
        <div className="min-w-40 text-right">
          <div className="font-mono text-lg font-semibold text-fg">{Math.round(progress?.pct ?? 0)}%</div>
          <div className="text-[11px] text-faint">experiment progress</div>
        </div>
      </div>
      <Bar value={progress?.units_done ?? 0} max={progress?.units_total ?? 0} tone="accent" live={batch.status === "running"} className="mb-3 h-2" />
      <div className="grid gap-2 md:grid-cols-2">
        {batch.runs.map((run) => {
          const selected = run.run_id === selectedRunId;
          const selectable = !!run.started_at || ["running", "done", "failed", "error", "canceled"].includes(run.status);
          const classes = `rounded-lg border p-3 text-left transition ${selected ? "border-accent/60 bg-accent/10" : "border-line/60 bg-panel/50"} ${selectable ? "hover:border-accent/40" : "cursor-not-allowed opacity-70"}`;
          return (
            <button
              type="button"
              key={run.run_id}
              disabled={!selectable}
              onClick={() => selectable && onSelect(run.run_id)}
              aria-current={selected ? "true" : undefined}
              title={selectable ? `View ${run.run_id}` : "This child run has not started yet."}
              className={classes}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-mono text-[10px] text-faint">JOB {run.ordinal ?? "?"}</div>
                  <div className="truncate text-xs font-medium text-fg">{run.run_id}</div>
                  <div className="mt-0.5 font-mono text-[10px] text-muted">memory_context={run.memory_context}</div>
                  <div className="mt-0.5 font-mono text-[10px] text-faint">inference_strategy={run.inference_strategy ?? batch.inference_strategy ?? "baseline"}</div>
                </div>
                <StatePill state={run.status} size="sm" />
              </div>
              <div className="mt-2 flex items-center gap-2">
                <Bar value={run.units_done ?? 0} max={run.units_total ?? 0} tone={run.status === "done" ? "good" : "info"} live={run.status === "running"} className="h-1.5 flex-1" />
                <span className="font-mono text-[10px] text-faint">{Math.round(run.progress_pct ?? run.work_pct ?? 0)}%</span>
              </div>
              <div className="mt-1 text-[10px] text-faint">persistence={run.persistence_status ?? "unknown"}{!selectable ? " · not started" : ""}</div>
            </button>
          );
        })}
      </div>
      {batch.error && <div className="mt-2 text-xs text-bad">{batch.error}</div>}
    </section>
  );
}