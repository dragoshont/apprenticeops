import { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  ChevronDown,
  Database,
  FlaskConical,
  Loader2,
  Pause,
  Play,
  RotateCw,
  ShieldCheck,
  Square,
  Zap,
} from "lucide-react";
import { control } from "../api";
import type { ExperimentState, RunMatrix, Session } from "../types";
import { Card, StatePill } from "./ui";

export function RunControlCenter({
  state,
  runId,
  runMatrix,
  sessions,
  experiments,
  activeSession,
  onSelectionChange,
  onAfter,
}: {
  state: string;
  runId: string | null;
  runMatrix?: RunMatrix | null;
  sessions: Session[];
  experiments: ExperimentState[];
  activeSession?: Session | null;
  onSelectionChange?: (selection: { modelSet: string; scenarioSet: string; memoryContext: string }) => void;
  onAfter: (runId?: string | null) => void;
}) {
  const [modelSet, setModelSet] = useState("");
  const [scenarioSet, setScenarioSet] = useState("");
  const [memoryContext, setMemoryContext] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const modelSets = runMatrix?.model_sets ?? [];
  const scenarioSets = runMatrix?.scenario_sets ?? [];
  const memoryContexts = runMatrix?.memory_contexts ?? [];
  const plans = runMatrix?.experiment_plans ?? [];

  useEffect(() => {
    if (modelSets.length && !modelSets.some((item) => item.id === modelSet)) {
      setModelSet(runMatrix?.defaults?.model_set ?? modelSets[0].id);
    }
    if (scenarioSets.length && !scenarioSets.some((item) => item.id === scenarioSet)) {
      setScenarioSet(runMatrix?.defaults?.scenario_set ?? scenarioSets[0].id);
    }
    if (memoryContexts.length && !memoryContexts.some((item) => item.id === memoryContext)) {
      setMemoryContext(runMatrix?.defaults?.memory_context ?? memoryContexts[0].id);
    }
  }, [
    modelSets,
    scenarioSets,
    memoryContexts,
    modelSet,
    scenarioSet,
    memoryContext,
    runMatrix?.defaults?.model_set,
    runMatrix?.defaults?.scenario_set,
    runMatrix?.defaults?.memory_context,
  ]);

  const chosenModel = modelSets.find((item) => item.id === modelSet) ?? modelSets[0];
  const chosenScenario = scenarioSets.find((item) => item.id === scenarioSet) ?? scenarioSets[0];
  const chosenMemory = memoryContexts.find((item) => item.id === memoryContext) ?? memoryContexts[0];
  const modelCount = chosenModel?.model_count ?? 0;
  const scenarioCount = chosenScenario?.scenario_count ?? 0;
  const inferenceUnits = modelCount * scenarioCount * 5;
  const judgeUnits = inferenceUnits * 2;
  const activeLocked = !!activeSession;
  const running = state === "running";
  const paused = state === "paused";
  const stopped = state === "stopped";
  const currentRunActive = !!runId && activeSession?.run_id === runId;
  const matchingRuns = sessions.filter(
    (session) =>
      session.model_set === modelSet &&
      session.scenario_set === scenarioSet &&
      (session.memory_context ?? "none") === (memoryContext || "none"),
  );

  useEffect(() => {
    onSelectionChange?.({ modelSet, scenarioSet, memoryContext });
  }, [modelSet, scenarioSet, memoryContext, onSelectionChange]);

  async function run(action: string, fn: () => Promise<{ run_id?: string }>) {
    setBusy(action);
    setMsg(null);
    try {
      const result = await fn();
      setMsg(null);
      onAfter(result?.run_id ?? undefined);
    } catch (error) {
      setMsg(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  function startSingleRun() {
    if (!chosenModel || !chosenScenario || !chosenMemory) return;
    if (chosenModel.kind === "experiment") {
      const ok = window.confirm(
        `${chosenModel.label} can run for a long time on the ai node. Start ${chosenModel.id} × ${chosenScenario.id} × ${chosenMemory.id}?`,
      );
      if (!ok) return;
    }
    void run("start", () => control.start(chosenModel.id, chosenScenario.id, chosenMemory.id));
  }

  function cancelCurrentRun() {
    const ok = window.confirm(`Cancel run ${runId ?? ""}? This stops the current pipeline and leaves the run marked canceled.`);
    if (!ok) return;
    void run("stop", () => control.stop(runId));
  }

  async function startPhase(planId: string, phaseId: string) {
    if (!chosenModel || !chosenScenario) return;
    const existing = experiments.find(
      (item) => item.plan_id === planId && item.model_set === chosenModel.id && item.scenario_set === chosenScenario.id,
    );
    await run(`${planId}:${phaseId}`, () => control.startPhase(planId, phaseId, chosenModel.id, chosenScenario.id, existing?.experiment_id));
  }

  const spin = (key: string, icon: React.ReactNode) =>
    busy === key ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : icon;

  const startDisabled = !chosenModel || !chosenScenario || !chosenMemory || busy != null || activeLocked;
  const startTitle = activeLocked
    ? "A run is already running or paused. Only one run can own the ai node."
    : undefined;

  return (
    <Card
      title="Experiment Control"
      icon={<Activity className="h-4 w-4 text-muted" />}
      right={<span className="text-xs text-faint">model × scenario × memory</span>}
    >
      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <Selector
              label="Model set"
              value={modelSet}
              onChange={setModelSet}
              options={modelSets.map((item) => ({
                id: item.id,
                label: item.label,
                meta: item.model_count != null ? `${item.model_count} models` : item.kind,
              }))}
            />
            <Selector
              label="Scenario set"
              value={scenarioSet}
              onChange={setScenarioSet}
              options={scenarioSets.map((item) => ({
                id: item.id,
                label: item.label,
                meta: item.scenario_count != null ? `${item.scenario_count} scenarios` : item.kind,
              }))}
            />
            <Selector
              label="Memory context"
              value={memoryContext}
              onChange={setMemoryContext}
              options={memoryContexts.map((item) => ({
                id: item.id,
                label: item.label,
                meta: item.byte_count ? `${Math.ceil(item.byte_count / 1024)}KB` : item.kind,
              }))}
            />
          </div>

          <div className="grid gap-3 lg:grid-cols-[1.05fr_0.95fr]">
            <div className="rounded-xl border border-line bg-panel2/30 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-fg">Run Intent</div>
                <span className="rounded bg-panel px-2 py-1 font-mono text-[10px] text-faint">
                  {modelCount}m × {scenarioCount}s × 5 reps · {judgeUnits} judge rows
                </span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <Axis icon={<CheckCircle2 className="h-3.5 w-3.5" />} label="Quality" detail="judge score / frontier" />
                <Axis icon={<ShieldCheck className="h-3.5 w-3.5" />} label="Safety" detail="guard + secure refusal" />
                <Axis icon={<Zap className="h-3.5 w-3.5" />} label="Energy" detail="RAPL Wh / answer" />
                <Axis icon={<Database className="h-3.5 w-3.5" />} label="Memory" detail={chosenMemory?.id ?? "none"} />
              </div>
              {chosenScenario?.description && (
                <p className="mt-3 text-xs leading-relaxed text-muted">{chosenScenario.description}</p>
              )}
            </div>

            <div className="rounded-xl border border-line bg-panel2/30 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-fg">AI Node Ownership</div>
                {activeSession ? <StatePill state={activeSession.state} size="sm" /> : <StatePill state="idle" size="sm" />}
              </div>
              {activeSession ? (
                <div className="space-y-2">
                  <button
                    type="button"
                    className="block max-w-full truncate rounded-lg bg-panel px-2.5 py-1.5 text-left font-mono text-xs text-fg transition hover:bg-accent/10"
                    onClick={() => onAfter(activeSession.run_id)}
                    title={activeSession.run_id}
                  >
                    {activeSession.run_id}
                  </button>
                  <div className="flex flex-wrap gap-1.5">
                    {currentRunActive && running && (
                      <ActionButton busy={busy === "pause"} onClick={() => void run("pause", () => control.pause(runId))}>
                        {spin("pause", <Pause className="h-3.5 w-3.5" />)} Pause
                      </ActionButton>
                    )}
                    {currentRunActive && (paused || stopped) && (
                      <ActionButton busy={busy === "resume"} accent onClick={() => void run("resume", () => control.resume(runId))}>
                        {spin("resume", <RotateCw className="h-3.5 w-3.5" />)} {paused ? "Resume" : "Continue"}
                      </ActionButton>
                    )}
                    {currentRunActive && (running || paused) && (
                      <ActionButton busy={busy === "stop"} danger onClick={cancelCurrentRun}>
                        {spin("stop", <Square className="h-3.5 w-3.5" />)} Cancel
                      </ActionButton>
                    )}
                    {!currentRunActive && (
                      <ActionButton onClick={() => onAfter(activeSession.run_id)}>Follow active run</ActionButton>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-xs leading-relaxed text-muted">No run is holding the node. A new launch can start immediately.</p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={startDisabled}
              title={startTitle}
              onClick={startSingleRun}
              className="btn btn-primary disabled:cursor-not-allowed disabled:opacity-40"
            >
              {spin("start", <Play className="h-4 w-4" />)}
              Start Run
            </button>
            {msg && <span className="max-w-xl truncate text-xs text-bad" title={msg}>{msg}</span>}
          </div>
        </div>

        <div className="space-y-4">
          <PhaseControls
            plans={plans}
            sessions={sessions}
            experiments={experiments}
            memoryContexts={memoryContexts}
            modelSet={chosenModel?.id}
            scenarioSet={chosenScenario?.id}
            runActive={activeLocked}
            busy={busy}
            onStartPhase={startPhase}
            matchingRunCount={matchingRuns.length}
          />
        </div>
      </div>
    </Card>
  );
}

function Selector({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { id: string; label: string; meta?: string }[];
}) {
  return (
    <label className="block rounded-xl border border-line bg-panel2/30 p-3">
      <span className="label">{label}</span>
      <span className="relative mt-2 block">
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="w-full appearance-none rounded-lg border border-line bg-panel px-3 py-2 pr-8 text-sm text-fg outline-none transition focus:border-accent/70"
        >
          {options.map((option) => (
            <option key={option.id} value={option.id} className="bg-panel text-fg">
              {option.label}{option.meta ? ` · ${option.meta}` : ""}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
      </span>
    </label>
  );
}

function Axis({ icon, label, detail }: { icon: React.ReactNode; label: string; detail: string }) {
  return (
    <div className="rounded-lg border border-line/60 bg-panel/50 px-2.5 py-2">
      <div className="flex items-center gap-1.5 text-xs font-medium text-fg">
        <span className="text-accent">{icon}</span>
        {label}
      </div>
      <div className="mt-0.5 text-[11px] text-faint">{detail}</div>
    </div>
  );
}

function ActionButton({
  children,
  onClick,
  busy = false,
  accent = false,
  danger = false,
}: {
  children: React.ReactNode;
  onClick: () => void;
  busy?: boolean;
  accent?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={busy}
      onClick={onClick}
      className={`inline-flex items-center gap-1 rounded-lg border border-line bg-panel px-2.5 py-1.5 text-xs font-medium text-fg transition hover:border-accent/50 disabled:cursor-not-allowed disabled:opacity-40 ${
        accent ? "border-accent/50 bg-accent/15 text-accent" : ""
      } ${danger ? "hover:border-bad/60 hover:bg-bad/10 hover:text-bad" : ""}`}
    >
      {children}
    </button>
  );
}

function PhaseControls({
  plans,
  sessions,
  experiments,
  memoryContexts,
  modelSet,
  scenarioSet,
  runActive,
  busy,
  onStartPhase,
  matchingRunCount,
}: {
  plans: RunMatrix["experiment_plans"];
  sessions: Session[];
  experiments: ExperimentState[];
  memoryContexts: NonNullable<RunMatrix["memory_contexts"]>;
  modelSet?: string;
  scenarioSet?: string;
  runActive: boolean;
  busy: string | null;
  onStartPhase: (planId: string, phaseId: string) => Promise<void>;
  matchingRunCount: number;
}) {
  if (!plans?.length || !modelSet || !scenarioSet) return null;
  return (
    <div className="rounded-xl border border-line bg-panel2/30 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium text-fg">
          <FlaskConical className="h-4 w-4 text-muted" />
          Memory Comparison Workflow
        </div>
        <span className="font-mono text-[10px] text-faint">{modelSet} × {scenarioSet} · {matchingRunCount} matching</span>
      </div>
      <p className="mb-3 text-xs leading-relaxed text-muted">
        Run the baseline first, review the gate, then run the memory-conditioned comparison on the same model and scenario set.
      </p>
      <div className="space-y-3">
        {plans.map((plan) => {
          const existing = experiments.find(
            (item) => item.plan_id === plan.id && item.model_set === modelSet && item.scenario_set === scenarioSet,
          );
          return (
            <div key={plan.id} className="space-y-2">
              {plan.phases.map((phase, index) => {
                const phaseState = existing?.phases.find((item) => item.id === phase.id);
                const status = phaseState?.status ?? "pending";
                const phaseRun = phaseState?.run_id ? sessions.find((session) => session.run_id === phaseState.run_id) : undefined;
                const displayStatus =
                  status === "running" && phaseRun && phaseRun.state !== "running" && phaseRun.state !== "paused"
                    ? phaseRun.state
                    : status;
                const priorCompleted = plan.phases
                  .slice(0, index)
                  .every((prior) => existing?.phases.find((item) => item.id === prior.id)?.status === "completed");
                const actionKey = `${plan.id}:${phase.id}`;
                const canStart = status === "pending" && priorCompleted && !runActive && busy == null;
                const memory = memoryContexts.find((item) => item.id === phase.memory_context);
                const actionLabel = !priorCompleted
                  ? "Locked"
                  : status === "pending"
                    ? phase.memory_context === "none"
                      ? "Run baseline"
                      : "Run memory condition"
                    : displayStatus === "canceled"
                      ? "Canceled"
                      : "Started";
                return (
                  <div key={phase.id} className="rounded-lg border border-line/60 bg-panel/50 p-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="font-mono text-[10px] text-faint">PHASE {index + 1}</div>
                        <div className="text-xs font-medium text-fg">{phase.label}</div>
                        <div className="mt-0.5 text-[11px] text-muted">{memory?.label ?? phase.memory_context}</div>
                        {phaseRun && phaseRun.state !== status && (
                          <div className="mt-1 text-[10px] text-faint">run state: {phaseRun.state}</div>
                        )}
                      </div>
                      <StatePill state={displayStatus} size="sm" />
                    </div>
                    <button
                      type="button"
                      disabled={!canStart}
                      title={runActive ? "A run is already running or paused." : !priorCompleted ? "Complete and review the previous phase first." : undefined}
                      onClick={() => void onStartPhase(plan.id, phase.id)}
                      className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-line bg-panel2 px-2.5 py-1.5 text-xs font-medium text-fg transition hover:border-accent/50 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {busy === actionKey ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                      {actionLabel}
                    </button>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}