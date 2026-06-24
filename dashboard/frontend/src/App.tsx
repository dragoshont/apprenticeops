import { usePipeline } from "./usePipeline";
import { useTheme } from "./useTheme";
import { Controls } from "./components/Controls";
import { ThemeToggle } from "./components/ThemeToggle";
import { RunProgress } from "./components/RunProgress";
import { SessionsTable } from "./components/SessionsTable";
import { PipelineFlow } from "./components/PipelineFlow";
import { NodeCards } from "./components/NodeCards";
import { ModelBars } from "./components/ModelBars";
import { ParetoChart } from "./components/ParetoChart";
import { ActivityFeed, SkipsFeed } from "./components/Feed";
import { StatePill, fmtAgo } from "./components/ui";
import { Radio, AlertTriangle, Terminal } from "lucide-react";

export default function App() {
  const { status, error, loading, refresh } = usePipeline(4000);
  const { theme, toggle } = useTheme();

  const state = status?.state ?? "idle";
  const batches = status?.batches ?? [];
  const models = status?.models ?? [];
  const modelProgress = status?.model_progress ?? [];
  const sessions = status?.sessions ?? [];
  const hasRun = !!status?.run_id;
  const live = state === "running";

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
              {hasRun ? (
                <>
                  run <span className="font-mono text-muted">{status!.run_id}</span>
                  {status?.meta?.batch ? ` · ${status.meta.batch}` : ""} · updated {fmtAgo(status?.ts)}
                </>
              ) : (
                "two-node CPU-only benchmark"
              )}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <StatePill state={state} />
          <Controls state={state} runId={status?.run_id ?? null} batches={batches} onAfter={refresh} />
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
          {/* Hero: overall run progress */}
          {hasRun && <RunProgress progress={status?.progress} live={live} />}

          {/* Live judge status line */}
          {status?.consumer?.status && (
            <div className="flex items-center gap-2 rounded-xl border border-line bg-panel/50 px-4 py-2 font-mono text-xs text-muted">
              <Terminal className="h-3.5 w-3.5 text-good" />
              <span className="truncate">{status.consumer.status}</span>
            </div>
          )}

          {/* Compact pipeline strip */}
          {hasRun && (
            <PipelineFlow
              models={models}
              producerAlive={status?.producer?.run_py_alive ?? false}
              consumerAlive={status?.consumer?.alive ?? false}
            />
          )}

          {/* Sessions */}
          <SessionsTable sessions={sessions} activeRunId={status?.run_id ?? null} onSelect={refresh} />

          {/* Models + nodes */}
          {hasRun && (
            <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
              <ModelBars models={modelProgress} />
              <div className="space-y-4">
                <NodeCards nodes={status?.nodes} />
                <ActivityFeed consumer={status?.consumer} />
              </div>
            </div>
          )}
          {!hasRun && <NodeCards nodes={status?.nodes} />}

          {/* Pareto + skips */}
          {hasRun && (
            <div className="grid gap-4 lg:grid-cols-2">
              <ParetoChart data={status?.pareto ?? []} />
              <SkipsFeed consumer={status?.consumer} />
            </div>
          )}

          <footer className="pt-2 text-center text-[11px] text-faint">
            ApprenticeOps mission-control · polls home over SSH every 4s · read the logs, not the vibes
          </footer>
        </div>
      )}
    </div>
  );
}
