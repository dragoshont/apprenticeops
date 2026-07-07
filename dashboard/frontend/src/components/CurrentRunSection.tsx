import { useState } from "react";
import { AlertTriangle, CheckCircle2, GitBranch, Loader2, Pause, RotateCw, Server, Square, Terminal } from "lucide-react";
import { control } from "../api";
import type { AnalyticsScope, Consumer, ModelProgress, ModelStage, PersistenceStatus, Producer, Progress, ReliabilityReport, RunBatch, RunBatchItem, RunSummary, Scores, SelectedScope, NodeInfo, ParetoPoint } from "../types";
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
  producer,
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
  inputSelection: { modelSet: string; scenarioSet: string; memoryContext: string; inferenceStrategy?: string; inferenceRuntime?: string };
  consumer?: Consumer;
  producer?: Producer;
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
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [confirmAction, setConfirmAction] = useState<null | { action: "pause" | "cancel"; title: string; body: string }>(null);
  const canPause = state === "running" && !!selectedRunId;
  const canResume = state === "paused" && !!selectedRunId;
  const canCancel = (state === "running" || state === "paused") && !!selectedRunId;

  async function runControl(action: "pause" | "resume" | "cancel") {
    if (!selectedRunId) return;
    setBusy(action);
    setMessage(null);
    try {
      if (action === "pause") {
        await control.pause(selectedRunId);
      } else if (action === "resume") {
        await control.resume(selectedRunId);
      } else {
        await control.stop(selectedRunId);
      }
      setMessage({ tone: "good", text: `${action} accepted for ${selectedRunId}` });
      onSelectRun(selectedRunId);
    } catch (error) {
      setMessage({ tone: "bad", text: error instanceof Error ? error.message : String(error) });
    } finally {
      setBusy(null);
    }
  }

  function confirmLifecycleAction() {
    if (!confirmAction) return;
    const action = confirmAction.action;
    setConfirmAction(null);
    void runControl(action);
  }

  const spin = (key: string, icon: React.ReactNode) => (busy === key ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : icon);

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
          {canPause && (
            <button
              type="button"
              disabled={busy != null}
              onClick={() => setConfirmAction({
                action: "pause",
                title: "Pause this experiment?",
                body: "Pause stops the active producer and judge for this run. Resume continues the same selected run.",
              })}
              className="btn rounded-lg border-warn/50 bg-warn/10 px-3 py-1.5 text-xs text-warn disabled:cursor-not-allowed disabled:opacity-40"
            >
              {spin("pause", <Pause className="h-3.5 w-3.5" />)}
              Pause
            </button>
          )}
          {canResume && (
            <button
              type="button"
              disabled={busy != null}
              onClick={() => void runControl("resume")}
              className="btn rounded-lg border-accent/50 bg-accent/15 px-3 py-1.5 text-xs text-accent disabled:cursor-not-allowed disabled:opacity-40"
            >
              {spin("resume", <RotateCw className="h-3.5 w-3.5" />)}
              Resume
            </button>
          )}
          {canCancel && (
            <button
              type="button"
              disabled={busy != null}
              onClick={() => setConfirmAction({
                action: "cancel",
                title: "Cancel this experiment?",
                body: "Cancel is terminal. The active child and queued memory contexts are marked canceled; completed pushed evidence remains untouched.",
              })}
              className="btn btn-danger rounded-lg px-3 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-40"
            >
              {spin("cancel", <Square className="h-3.5 w-3.5" />)}
              Cancel
            </button>
          )}
        </div>
      </div>

      {message && (
        <div className={`rounded-lg border px-3 py-2 text-xs ${message.tone === "bad" ? "border-bad/40 bg-bad/10 text-bad" : "border-good/40 bg-good/10 text-good"}`}>
          {message.text}
        </div>
      )}

      {displayBatch && <BatchOverview batch={displayBatch} selectedRunId={selectedRunId} onSelect={onSelectRun} />}

      <ScopeHeader scope={selectedScope} analyticsScope={analyticsScope} persistence={persistence} user={user} selectedRunStatus={state} selectedBatchRun={selectedRunInBatch} batchNotice={batchNotice} />

      <RunAtAGlance
        state={state}
        progress={progress}
        persistence={persistence}
        reliability={reliability ?? null}
        producer={producer}
        producerAlive={producerAlive}
        consumer={consumer}
      />

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
      {confirmAction && (
        <ConfirmDialog
          title={confirmAction.title}
          body={confirmAction.body}
          tone={confirmAction.action === "pause" ? "warn" : "bad"}
          confirmLabel={confirmAction.action === "pause" ? "Pause experiment" : "Cancel experiment"}
          busy={busy === confirmAction.action}
          onCancel={() => setConfirmAction(null)}
          onConfirm={confirmLifecycleAction}
        />
      )}
    </section>
  );
}

function RunAtAGlance({
  state,
  progress,
  persistence,
  reliability,
  producer,
  producerAlive,
  consumer,
}: {
  state: string;
  progress?: Progress;
  persistence?: PersistenceStatus;
  reliability?: ReliabilityReport | null;
  producer?: Producer;
  producerAlive: boolean;
  consumer?: Consumer;
}) {
  const latest = producer?.latest_result;
  const gitHealthy = (persistence?.push_pending_count ?? 0) === 0;
  return (
    <div className="card card-pad space-y-4 border-accent/20 bg-panel/70">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="label flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-good" /> Run at a glance
          </div>
          <div className="mt-1 text-xs text-muted">
            Live operational truth for this run: work done, reliability, process health, and latest answer row.
          </div>
        </div>
        <StatePill state={state} size="sm" />
      </div>

      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <GlanceItem label="Progress" value={formatPct(progress?.pct)} sub="inference + judging work" />
        <GlanceItem label="Inference" value={formatRatio(progress?.inf_done, progress?.inf_total)} sub="AI answer rows" />
        <GlanceItem label="Judging" value={formatRatio(progress?.judge_done, progress?.judge_total)} sub="frontier judge rows" />
        <GlanceItem label="Models persisted" value={formatRatio(persistence?.committed_count, persistence?.committed_total)} sub="committed and pushed" />
        <GlanceItem label="Push pending" value={formatCount(persistence?.push_pending_count)} sub={gitHealthy ? "Git persistence healthy" : "waiting on git push"} tone={gitHealthy ? "text-good" : "text-warn"} />
        <GlanceItem label="ETA" value={progress?.eta_human ? `about ${progress.eta_human}` : "calculating"} sub="current run-rate estimate" />
        <GlanceItem label="Rate" value={progress?.rate_per_min != null ? `${progress.rate_per_min} units/min` : "—"} sub="recent throughput" />
        <GlanceItem label="State" value={state || "unknown"} sub="pipeline state" tone={state === "running" ? "text-good" : "text-muted"} />
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr_1.2fr]">
        <div className="rounded-xl border border-line/60 bg-panel/50 p-3">
          <div className="label mb-2">Reliability so far</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-3">
            <InlineMetric label="DNF" value={formatCount(reliability?.dnf)} tone={reliability?.dnf ? "text-warn" : "text-good"} />
            <InlineMetric label="Length" value={formatCount(reliability?.length)} tone={reliability?.length ? "text-warn" : "text-good"} />
            <InlineMetric label="Zero stalls" value={formatCount(reliability?.zero_output_stalls)} tone={reliability?.zero_output_stalls ? "text-bad" : "text-good"} />
            <InlineMetric label="Judge empty" value={formatCount(reliability?.judge_empty)} tone={reliability?.judge_empty ? "text-bad" : "text-good"} />
            <InlineMetric label="No-answer judgements" value={formatCount(reliability?.empty_answer_judgements)} tone={reliability?.empty_answer_judgements ? "text-warn" : "text-good"} />
            <InlineMetric label="Judge parse failures" value={formatCount(reliability?.judge_response_parse_failures)} tone={reliability?.judge_response_parse_failures ? "text-bad" : "text-good"} />
          </div>
        </div>

        <div className="rounded-xl border border-line/60 bg-panel/50 p-3">
          <div className="label mb-2">Both sides</div>
          <div className="space-y-2 text-xs">
            <ProcessLine icon={<Server className="h-3.5 w-3.5" />} label="AI producer" detail="run-roster.sh + run.py" alive={producerAlive} />
            <ProcessLine icon={<GitBranch className="h-3.5 w-3.5" />} label="Home consumer" detail="judge-scheduler.sh" alive={consumer?.alive ?? false} />
          </div>
        </div>

        <div className="rounded-xl border border-line/60 bg-panel/50 p-3">
          <div className="label mb-2">Latest row</div>
          {latest ? (
            <div className="grid gap-2 text-xs sm:grid-cols-2">
              <InlineMetric label="Model" value={latest.model || "—"} wide />
              <InlineMetric label="Scenario" value={latest.scenario || "—"} wide />
              <InlineMetric label="Repeat" value={latest.rep == null ? "—" : String(latest.rep)} />
              <InlineMetric label="Finish" value={latest.finish || "—"} tone={latest.finish === "stop" ? "text-good" : "text-warn"} />
            </div>
          ) : (
            <div className="text-xs text-faint">Waiting for the first mirrored answer row.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function GlanceItem({ label, value, sub, tone = "text-fg" }: { label: string; value: string; sub: string; tone?: string }) {
  return (
    <div className="rounded-xl border border-line/60 bg-panel/50 px-3 py-2.5">
      <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-faint">{label}</div>
      <div className={`mt-1 font-mono text-base font-semibold tabular-nums ${tone}`}>{value}</div>
      <div className="mt-0.5 truncate text-[10px] text-muted" title={sub}>{sub}</div>
    </div>
  );
}

function InlineMetric({ label, value, tone = "text-fg", wide = false }: { label: string; value: string; tone?: string; wide?: boolean }) {
  return (
    <div className={wide ? "sm:col-span-2" : undefined}>
      <div className="text-[10px] uppercase tracking-[0.12em] text-faint">{label}</div>
      <div className={`mt-0.5 truncate font-mono text-xs font-semibold ${tone}`} title={value}>{value}</div>
    </div>
  );
}

function ProcessLine({ icon, label, detail, alive }: { icon: React.ReactNode; label: string; detail: string; alive: boolean }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-line/50 bg-bg/30 px-2.5 py-2">
      <div className="flex min-w-0 gap-2">
        <span className={alive ? "text-good" : "text-warn"}>{icon}</span>
        <div className="min-w-0">
          <div className="font-medium text-fg">{label}</div>
          <div className="truncate font-mono text-[10px] text-faint" title={detail}>{detail}</div>
        </div>
      </div>
      <span className={`shrink-0 font-mono text-[10px] uppercase tracking-[0.12em] ${alive ? "text-good" : "text-warn"}`}>
        {alive ? "alive" : "down"}
      </span>
    </div>
  );
}

function formatRatio(done?: number, total?: number) {
  return `${formatCount(done)} / ${formatCount(total)}`;
}

function formatCount(value?: number | null) {
  return value == null ? "—" : value.toLocaleString();
}

function formatPct(value?: number | null) {
  return value == null ? "—" : `${value.toFixed(value >= 10 ? 1 : 2)}%`;
}

function ConfirmDialog({
  title,
  body,
  tone,
  confirmLabel,
  busy,
  onCancel,
  onConfirm,
}: {
  title: string;
  body: string;
  tone: "warn" | "bad";
  confirmLabel: string;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-bg/70 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-line bg-panel p-5 shadow-2xl">
        <div className="flex items-start gap-3">
          <div className={`rounded-xl p-2 ${tone === "warn" ? "bg-warn/15 text-warn" : "bg-bad/15 text-bad"}`}>
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <div className="text-base font-semibold text-fg">{title}</div>
            <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>
          </div>
        </div>
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button type="button" className="btn" onClick={onCancel} disabled={busy}>Keep running</button>
          <button type="button" className={`btn ${tone === "warn" ? "border-warn/50 bg-warn/10 text-warn" : "btn-danger border-bad/50 bg-bad/10 text-bad"}`} onClick={onConfirm} disabled={busy}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
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
        <span className="font-mono">inference_runtime={scope?.inference_runtime ?? analyticsScope?.inference_runtime ?? "ollama"}</span>
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