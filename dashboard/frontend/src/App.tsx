import { useEffect, useState } from "react";
import { usePipeline } from "./usePipeline";
import { useTheme } from "./useTheme";
import { fetchConfig } from "./api";
import { RunControlCenter } from "./components/RunControlCenter";
import { ThemeToggle } from "./components/ThemeToggle";
import { NodeCards } from "./components/NodeCards";
import { DashboardMenu } from "./components/DashboardMenu";
import { RunLibrary } from "./components/RunLibrary";
import { CurrentRunSection } from "./components/CurrentRunSection";
import { StatePill, fmtAgo, Hint } from "./components/ui";
import { Radio, AlertTriangle, Lock, LockOpen, ListChecks } from "lucide-react";

export default function App() {
  const { status, error, loading, refresh } = usePipeline(4000);
  const { theme, toggle } = useTheme();
  const [auth, setAuth] = useState<{ auth_enabled: boolean; user: string | null } | null>(null);
  const [controlSelection, setControlSelection] = useState({ modelSet: "", scenarioSet: "", memoryContext: "", memoryContexts: [] as string[], inferenceStrategy: "baseline" });
  const [sessionScope, setSessionScope] = useState<"matching" | "all">("matching");
  const [sessionSearch, setSessionSearch] = useState("");
  const [sessionSearchOpen, setSessionSearchOpen] = useState(false);
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
  const displayBatch = selectedBatch ?? null;
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
  const latestSession = sessions[0] ?? null;
  const activeRunId = activeSession?.run_id ?? null;
  const selectedRunId = status?.run_id ?? null;
  const viewingLatest = !!selectedRunId && !!latestSession?.run_id && selectedRunId === latestSession.run_id;
  const viewingActive = !!selectedRunId && !!activeRunId && selectedRunId === activeRunId;
  const runViewTitle = viewingActive ? "Current Run" : viewingLatest ? "Latest Run" : "Selected Past Run";
  const runViewDescription = viewingActive
    ? "The active experiment that owns the AI node right now. Pause and cancel controls apply here only."
    : viewingLatest
      ? "The newest completed, stopped, or canceled run."
      : "A historical run selected from Run History below.";
  const runDetailLabel = viewingActive ? "Current Run" : "Run Detail";

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8">
      {/* Header */}
      <header id="home" className="mb-5 scroll-mt-24 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
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

      <DashboardMenu
        hasRun={hasRun}
        hasRunMatrix={!!runMatrix}
        runDetailLabel={runDetailLabel}
        search={sessionSearch}
        searchOpen={sessionSearchOpen}
        onToggleSearch={() => setSessionSearchOpen((open) => !open)}
        onSearch={setSessionSearch}
        onClearSearch={() => setSessionSearch("")}
      />

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
          <section id="start" className="scroll-mt-24">
            <RunControlCenter
              runMatrix={runMatrix}
              runBatches={runBatches}
              activeSession={activeSession ?? null}
              onSelectionChange={setControlSelection}
              onAfter={refresh}
            />
          </section>

          {hasRun && (
            <CurrentRunSection
              title={runViewTitle}
              description={runViewDescription}
              state={state}
              live={live}
              displayBatch={displayBatch}
              selectedRunId={status?.run_id ?? null}
              selectedRunInBatch={selectedRunInBatch}
              batchNotice={batchNotice}
              selectedScope={selectedScope}
              analyticsScope={analyticsScope}
              persistence={status?.persistence}
              user={status?.user ?? selected?.user ?? "user"}
              progress={status?.progress}
              reliability={status?.reliability ?? null}
              inputSelection={selectedInputSelection}
              consumer={status?.consumer}
              producerAlive={status?.producer?.run_py_alive ?? false}
              models={models}
              modelProgress={modelProgress}
              nodes={status?.nodes}
              summary={status?.summary}
              pareto={status?.pareto ?? []}
              scores={status?.scores}
              backToLatestRunId={!viewingLatest ? latestSession?.run_id ?? null : null}
              onBackToLatest={refresh}
              onSelectRun={refresh}
            />
          )}

          <RunLibrary
            sessions={visibleSessions}
            scopedCount={scopedSessions.length}
            matchingCount={matchingSessions.length}
            totalCount={sessions.length}
            activeRunId={status?.run_id ?? null}
            scope={sessionScope}
            search={sessionSearch}
            status={sessionStatus}
            date={sessionDate}
            onScope={setSessionScope}
            onSearch={setSessionSearch}
            onStatus={setSessionStatus}
            onDate={setSessionDate}
            onSelect={refresh}
          />

          {!hasRun && <NodeCards nodes={status?.nodes} />}

          {runMatrix && (
            <section id="scenarios" className="card card-pad scroll-mt-24">
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
