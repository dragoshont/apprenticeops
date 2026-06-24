import { useEffect, useState } from "react";
import { usePipeline } from "./usePipeline";
import { useTheme } from "./useTheme";
import { fetchConfig } from "./api";
import { Controls } from "./components/Controls";
import { ThemeToggle } from "./components/ThemeToggle";
import { RunProgress } from "./components/RunProgress";
import { SessionsTable } from "./components/SessionsTable";
import { PipelineFlow } from "./components/PipelineFlow";
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
import { StatePill, fmtAgo } from "./components/ui";
import { Radio, AlertTriangle, Terminal, Lock, LockOpen } from "lucide-react";

export default function App() {
  const { status, error, loading, refresh } = usePipeline(4000);
  const { theme, toggle } = useTheme();
  const [auth, setAuth] = useState<{ auth_enabled: boolean; user: string | null } | null>(null);

  useEffect(() => {
    fetchConfig().then(setAuth).catch(() => setAuth(null));
  }, []);

  const state = status?.state ?? "idle";
  const batches = status?.batches ?? [];
  const models = status?.models ?? [];
  const modelProgress = status?.model_progress ?? [];
  const sessions = status?.sessions ?? [];
  const hasRun = !!status?.run_id;
  const live = state === "running";
  const selected = sessions.find((s) => s.run_id === status?.run_id);

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
          <Controls state={state} runId={status?.run_id ?? null} batches={batches} onAfter={refresh} />
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
          {/* Runs are the focus: the table on top, click a row to load its detail below */}
          <SessionsTable sessions={sessions} activeRunId={status?.run_id ?? null} onSelect={refresh} />

          {hasRun && (
            <div className="space-y-4">
              {/* selected-run header */}
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-1 text-sm">
                <span className="font-mono text-fg">{status!.run_id}</span>
                <StatePill state={state} size="sm" />
                {status?.meta?.batch && <span className="text-xs text-muted">{status.meta.batch}</span>}
                <span className="text-xs text-faint">
                  by {status?.user ?? selected?.user ?? "user"}
                </span>
              </div>

              {/* live-only: progress hero + judge line + pipeline */}
              {live && (
                <>
                  <RunProgress progress={status?.progress} live={live} />
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
              <RunSummaryCard summary={status?.summary} />

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
                <ParetoChart data={status?.pareto ?? []} />
                <ParetoLeaderboard pareto={status?.pareto ?? []} />
              </div>

              {/* quality + power leaderboards */}
              <div className="grid gap-4 lg:grid-cols-2">
                <QualityLeaderboard pareto={status?.pareto ?? []} />
                <PowerLeaderboard pareto={status?.pareto ?? []} />
              </div>

              {/* score distribution + per-class quality */}
              <div className="grid gap-4 lg:grid-cols-2">
                <ScoreDistribution scores={status?.scores} />
                <ClassQuality scores={status?.scores} />
              </div>

              <SkipsFeed consumer={status?.consumer} />
            </div>
          )}

          {!hasRun && <NodeCards nodes={status?.nodes} />}

          <footer className="pt-2 text-center text-[11px] text-faint">
            ApprenticeOps mission-control · polls home over SSH every 4s · read the logs, not the vibes
          </footer>
        </div>
      )}
    </div>
  );
}
