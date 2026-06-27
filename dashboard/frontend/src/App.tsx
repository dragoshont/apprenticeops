import { useEffect, useState } from "react";
import { usePipeline } from "./usePipeline";
import { useTheme } from "./useTheme";
import { fetchConfig } from "./api";
import { RunControlCenter } from "./components/RunControlCenter";
import { ThemeToggle } from "./components/ThemeToggle";
import { RunProgress } from "./components/RunProgress";
import { SessionsTable } from "./components/SessionsTable";
import { PipelineFlow } from "./components/PipelineFlow";
import { InputInspector } from "./components/InputInspector";
import { NodeCards } from "./components/NodeCards";
import { ModelBars } from "./components/ModelBars";
import { ParetoChart } from "./components/ParetoChart";
import {
  QualityLeaderboard,
  ScoreDistribution,
  ClassQuality,
  ParetoLeaderboard,
  PowerLeaderboard,
  RunSummaryCard,
} from "./components/Charts";
import { ActivityFeed, SkipsFeed } from "./components/Feed";
import { Bar, StatePill, fmtAgo, Hint } from "./components/ui";
import { Radio, AlertTriangle, Terminal, Lock, LockOpen, ListChecks } from "lucide-react";
import type { AnalyticsScope, PersistenceStatus, RunBatch, RunBatchItem, SelectedScope } from "./types";

export default function App() {
  const { status, error, loading, refresh } = usePipeline(4000);
  const { theme, toggle } = useTheme();
  const [auth, setAuth] = useState<{ auth_enabled: boolean; user: string | null } | null>(null);
  const [controlSelection, setControlSelection] = useState({ modelSet: "", scenarioSet: "", memoryContext: "", memoryContexts: [] as string[], inferenceStrategy: "baseline" });
  const [sessionScope, setSessionScope] = useState<"matching" | "all">("matching");
  const [sessionSearch, setSessionSearch] = useState("");
  const [sessionStatus, setSessionStatus] = useState("all");
  const [sessionDate, setSessionDate] = useState<"today" | "week" | "month" | "all">("today");

  useEffect(() => {
    fetchConfig().then(setAuth).catch(() => setAuth(null));
  }, []);

  const state = status?.state ?? "idle";
  const runMatrix = status?.run_matrix;
  const models = status?.models ?? [];
  const modelProgress = status?.model_progress ?? [];
  const sessions = status?.sessions ?? [];
  const runBatches = status?.run_batches ?? [];
  const hasRun = !!status?.run_id;
  const live = state === "running";
  const selected = sessions.find((s) => s.run_id === status?.run_id);
  // A run "owns" the single ai node while it is running OR paused (the backend
  // rejects a new start in both states — app.py /api/control/start), so the guard
  // and the Follow control must cover both, not just live.
  const activeSession = sessions.find((s) => s.state === "running" || s.state === "paused");
  const busyElsewhere = !!activeSession && activeSession.run_id !== status?.run_id;
  const matchingSessions = sessions.filter(
    (session) =>
      session.model_set === controlSelection.modelSet &&
      session.scenario_set === controlSelection.scenarioSet &&
      (session.inference_strategy ?? "baseline") === (controlSelection.inferenceStrategy || "baseline") &&
      (controlSelection.memoryContexts.length
        ? controlSelection.memoryContexts.includes(session.memory_context ?? "none")
        : (session.memory_context ?? "none") === (controlSelection.memoryContext || "none")),
  );
  const scopedSessions = sessionScope === "matching" ? matchingSessions : sessions;
  const visibleSessions = scopedSessions.filter((session) => {
    const query = sessionSearch.trim().toLowerCase();
    const text = [session.run_id, session.model_set, session.scenario_set, session.memory_context, session.inference_strategy, session.state, session.user]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const matchesText = !query || text.includes(query);
    const matchesStatus = sessionStatus === "all" || session.state === sessionStatus;
    const matchesDate = inDateScope(session.started_at, sessionDate);
    return matchesText && matchesStatus && matchesDate;
  });
  const selectedBatch = runBatches.find((batch) => batch.runs.some((run) => run.run_id === status?.run_id));
  const activeBatch = runBatches.find((batch) => batch.status === "running" || batch.status === "starting");
  const displayBatch = selectedBatch ?? activeBatch;
  const selectedScope = status?.selected_scope;
  const analyticsScope = status?.analytics_scope ?? {
    kind: "selected_run",
    source: "selected_run",
    run_id: status?.run_id ?? null,
    model_set: status?.meta?.model_set ?? null,
    scenario_set: status?.meta?.scenario_set ?? null,
    memory_context: status?.meta?.memory_context ?? "none",
    inference_strategy: status?.meta?.inference_strategy ?? "baseline",
  };
  const selectedRunInBatch = displayBatch?.runs.find((run) => run.run_id === status?.run_id);
  const batchStillRunning = !!selectedBatch && !!selectedRunInBatch && selectedBatch.status === "running" && status?.state === "done";
  const batchNotice = batchStillRunning
    ? `Selected child is complete; parent memory batch is still running ${selectedBatch.progress?.current_memory_context ?? "the next context"}.`
    : null;
  const selectedInputSelection = {
    modelSet: analyticsScope.model_set ?? controlSelection.modelSet,
    scenarioSet: analyticsScope.scenario_set ?? controlSelection.scenarioSet,
    memoryContext: analyticsScope.memory_context ?? controlSelection.memoryContext ?? "none",
    inferenceStrategy: analyticsScope.inference_strategy ?? controlSelection.inferenceStrategy ?? "baseline",
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8">
      {/* Header */}
      <header className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-accent/15 p-2 text-accent ring-1 ring-accent/30">
            <Radio className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-fg">
              ApprenticeOps · Mission Control
            </h1>
            <p className="text-xs text-faint">
              two-node CPU-only benchmark · {sessions.length} runs · updated {fmtAgo(status?.ts)}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {(live || state === "paused") && <StatePill state={state} />}
          {busyElsewhere && activeSession && (
            <button
              onClick={() => refresh(activeSession.run_id)}
              className={`pill ring-1 transition focus:outline-none focus-visible:ring-2 ${
                activeSession.state === "paused"
                  ? "bg-warn/15 text-warn ring-warn/30 hover:bg-warn/25 focus-visible:ring-warn"
                  : "bg-good/15 text-good ring-good/30 hover:bg-good/25 focus-visible:ring-good"
              }`}
              title={`A run is ${activeSession.state}: ${activeSession.run_id} — click to follow it`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  activeSession.state === "paused" ? "bg-warn" : "bg-good motion-safe:animate-pulse"
                }`}
              />
              run {activeSession.state === "paused" ? "paused" : "live"} · Follow
            </button>
          )}
          {auth?.auth_enabled ? (
            <span className="pill bg-good/15 text-good" title={`signed in as ${auth.user ?? "?"}`}>
              <Lock className="h-3 w-3" />
              {auth.user ?? "auth"}
            </span>
          ) : (
            <span className="pill bg-muted/15 text-muted" title="no authentication (open on the LAN)">
              <LockOpen className="h-3 w-3" />
              user
            </span>
          )}
          <Hint
            align="end"
            text={
              auth?.auth_enabled
                ? "You are signed in via Authentik SSO; runs you start are attributed to your username."
                : "No sign-in is required — the dashboard is open on your LAN, so runs are attributed to 'user'. Enable Authentik SSO to require login and record who launched each run."
            }
          />
          <ThemeToggle theme={theme} onToggle={toggle} />
        </div>
      </header>

      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-bad/40 bg-bad/10 px-4 py-3 text-sm text-bad">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <div className="font-medium">Backend unreachable or status failed</div>
            <div className="mt-0.5 font-mono text-xs opacity-80">{error}</div>
          </div>
        </div>
      )}

      {loading && !status ? (
        <div className="py-24 text-center text-sm text-faint">Connecting to home…</div>
      ) : (
        <div className="space-y-4">
          <RunControlCenter
            runMatrix={runMatrix}
            runBatches={runBatches}
            activeSession={activeSession ?? null}
            onSelectionChange={setControlSelection}
            onAfter={refresh}
          />

          {displayBatch && <BatchOverview batch={displayBatch} selectedRunId={status?.run_id ?? null} onSelect={refresh} />}

          <section className="rounded-xl border border-line bg-panel2/30 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-sm font-medium text-fg">Sessions</div>
              <div className="inline-flex overflow-hidden rounded-lg border border-line bg-panel text-xs">
                <button
                  type="button"
                  onClick={() => setSessionScope("matching")}
                  className={`px-2.5 py-1.5 transition ${sessionScope === "matching" ? "bg-accent/15 text-accent" : "text-muted hover:text-fg"}`}
                >
                  Matching selection · {matchingSessions.length}
                </button>
                <button
                  type="button"
                  onClick={() => setSessionScope("all")}
                  className={`border-l border-line px-2.5 py-1.5 transition ${sessionScope === "all" ? "bg-accent/15 text-accent" : "text-muted hover:text-fg"}`}
                >
                  All sessions · {sessions.length}
                </button>
              </div>
            </div>
            <div className="mt-3 grid gap-2 lg:grid-cols-[1fr_auto_auto]">
              <label>
                <span className="sr-only">Search sessions</span>
                <input
                  value={sessionSearch}
                  onChange={(event) => setSessionSearch(event.target.value)}
                  placeholder="Search by run, status, model, scenario, memory…"
                  className="w-full rounded-lg border border-line bg-panel px-3 py-2 text-xs text-fg outline-none transition placeholder:text-faint focus:border-accent/60"
                />
              </label>
              <select
                value={sessionStatus}
                onChange={(event) => setSessionStatus(event.target.value)}
                className="rounded-lg border border-line bg-panel px-3 py-2 text-xs text-fg outline-none transition focus:border-accent/60"
                aria-label="Filter sessions by status"
              >
                <option value="all">Any status</option>
                <option value="running">Running</option>
                <option value="done">Done</option>
                <option value="canceled">Canceled</option>
                <option value="failed">Failed</option>
                <option value="stopped">Stopped</option>
              </select>
              <div className="inline-flex overflow-hidden rounded-lg border border-line bg-panel text-xs">
                {(["today", "week", "month", "all"] as const).map((dateScope) => (
                  <button
                    key={dateScope}
                    type="button"
                    onClick={() => setSessionDate(dateScope)}
                    className={`px-2.5 py-2 capitalize transition ${sessionDate === dateScope ? "bg-accent/15 text-accent" : "text-muted hover:text-fg"}`}
                  >
                    {dateScope === "week" ? "This week" : dateScope === "month" ? "This month" : dateScope}
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-2 text-[11px] text-faint">Showing {visibleSessions.length} of {scopedSessions.length} sessions in this scope.</div>
          </section>
          <SessionsTable
            sessions={visibleSessions}
            activeRunId={status?.run_id ?? null}
            onSelect={refresh}
            emptyText={sessionScope === "matching" ? "No runs match the selected model, scenario, and memory context yet." : "No runs yet."}
          />

          {hasRun && (
            <div className="space-y-4">
              {/* selected-run header */}
              <ScopeHeader scope={selectedScope} analyticsScope={analyticsScope} persistence={status?.persistence} user={status?.user ?? selected?.user ?? "user"} selectedRunStatus={state} selectedBatchRun={selectedRunInBatch} batchNotice={batchNotice} />

              <RunProgress progress={status?.progress} live={live} scope={analyticsScope} persistence={status?.persistence} batchNotice={batchNotice} reliability={status?.reliability ?? null} />

              <InputInspector selection={selectedInputSelection} title="Current experiment inputs" />

              {/* live-only: progress hero + judge line + pipeline */}
              {live && (
                <>
                  {status?.consumer?.status && (
                    <div className="flex items-center gap-2 rounded-xl border border-line bg-panel/50 px-4 py-2 font-mono text-xs text-muted">
                      <Terminal className="h-3.5 w-3.5 text-good" />
                      <span className="truncate">{status.consumer.status}</span>
                    </div>
                  )}
                  <PipelineFlow
                    models={models}
                    producerAlive={status?.producer?.run_py_alive ?? false}
                    consumerAlive={status?.consumer?.alive ?? false}
                  />
                </>
              )}

              {/* roll-up stats for the selected run */}
              <RunSummaryCard summary={status?.summary} scope={analyticsScope} />

              {/* models + (nodes/activity when live) */}
              <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
                <ModelBars models={modelProgress} />
                <div className="space-y-4">
                  <NodeCards nodes={status?.nodes} />
                  {live && <ActivityFeed consumer={status?.consumer} />}
                </div>
              </div>

              {/* Pareto (3-objective) + frontier table */}
              <div className="grid gap-4 lg:grid-cols-2">
                <ParetoChart data={status?.pareto ?? []} scope={analyticsScope} />
                <ParetoLeaderboard pareto={status?.pareto ?? []} scope={analyticsScope} />
              </div>

              {/* quality + power leaderboards */}
              <div className="grid gap-4 lg:grid-cols-2">
                <QualityLeaderboard pareto={status?.pareto ?? []} scope={analyticsScope} />
                <PowerLeaderboard pareto={status?.pareto ?? []} scope={analyticsScope} />
              </div>

              {/* score distribution + per-class quality */}
              <div className="grid gap-4 lg:grid-cols-2">
                <ScoreDistribution scores={status?.scores} scope={analyticsScope} />
                <ClassQuality scores={status?.scores} scope={analyticsScope} />
              </div>

              <SkipsFeed consumer={status?.consumer} />
            </div>
          )}

          {!hasRun && <NodeCards nodes={status?.nodes} />}

          {runMatrix && (
            <section className="card card-pad">
              <header className="mb-3 flex items-center justify-between">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-fg">
                  <ListChecks className="h-4 w-4 text-muted" />
                  Scenarios
                </h2>
                <span className="text-xs text-faint">
                  {runMatrix.scenarios.length} unique · {runMatrix.scenario_sets.length} sets
                </span>
              </header>
              <div className="grid gap-4 lg:grid-cols-2">
                {runMatrix.scenario_sets.map((set) => {
                  const rows = runMatrix.scenarios.filter((scenario) => scenario.sets.includes(set.id));
                  return (
                    <div key={set.id} className="rounded-xl border border-line bg-panel2/30 p-3">
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <div>
                          <div className="text-sm font-medium text-fg">{set.label}</div>
                          <div className="text-[11px] text-faint">{set.description}</div>
                        </div>
                        <span className="pill bg-muted/15 text-muted">{set.scenario_count ?? rows.length}</span>
                      </div>
                      <div className="max-h-72 space-y-1 overflow-auto pr-1">
                        {rows.map((scenario) => (
                          <div key={`${set.id}-${scenario.id}`} className="rounded-lg border border-line/50 bg-panel/50 px-2.5 py-2">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="font-mono text-[11px] text-fg">{scenario.id}</span>
                              {scenario.class && <span className="pill bg-accent/10 px-1.5 py-0 text-[10px] text-accent">{scenario.class}</span>}
                              {scenario.difficulty && <span className="pill bg-muted/15 px-1.5 py-0 text-[10px] text-muted">{scenario.difficulty}</span>}
                              {scenario.grounding && <span className="pill bg-info/10 px-1.5 py-0 text-[10px] text-info">{scenario.grounding}</span>}
                            </div>
                            {scenario.brief && <div className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-muted">{scenario.brief}</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          <footer className="pt-2 text-center text-[11px] text-faint">
            ApprenticeOps mission-control · polls home over SSH every 4s · read the logs, not the vibes
          </footer>
        </div>
      )}
    </div>
  );
}

function inDateScope(ts: number | null, scope: "today" | "week" | "month" | "all") {
  if (scope === "all") return true;
  if (!ts) return false;
  const date = new Date(ts * 1000);
  const now = new Date();
  const start = new Date(now);
  if (scope === "today") {
    start.setHours(0, 0, 0, 0);
  } else if (scope === "week") {
    const day = (start.getDay() + 6) % 7;
    start.setDate(start.getDate() - day);
    start.setHours(0, 0, 0, 0);
  } else {
    start.setDate(1);
    start.setHours(0, 0, 0, 0);
  }
  return date >= start;
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
