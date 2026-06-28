import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Database,
  Loader2,
  Pause,
  RotateCw,
  Rocket,
  Scale,
  ShieldCheck,
  Square,
  Timer,
  Zap,
  Workflow,
} from "lucide-react";
import { control } from "../api";
import type { RunBatch, RunMatrix, Session } from "../types";
import { Card, Hint } from "./ui";

export function RunControlCenter({
  runMatrix,
  runBatches,
  activeSession,
  onSelectionChange,
  onAfter,
}: {
  runMatrix?: RunMatrix | null;
  runBatches: RunBatch[];
  activeSession?: Session | null;
  onSelectionChange?: (selection: { modelSet: string; scenarioSet: string; memoryContext: string; memoryContexts: string[]; inferenceStrategy: string }) => void;
  onAfter: (runId?: string | null) => void;
}) {
  const [modelSet, setModelSet] = useState("");
  const [scenarioSet, setScenarioSet] = useState("");
  const [inferenceStrategy, setInferenceStrategy] = useState("baseline");
  const [selectedMemoryContexts, setSelectedMemoryContexts] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<null | { action: "pause" | "cancel"; title: string; body: string }>(null);

  const modelSets = runMatrix?.model_sets ?? [];
  const scenarioSets = runMatrix?.scenario_sets ?? [];
  const memoryContexts = runMatrix?.memory_contexts ?? [];
  const selectableMemoryContexts = memoryContexts.filter((item) => item.kind !== "strategy");
  const inferenceStrategies = runMatrix?.inference_strategies ?? [];

  useEffect(() => {
    if (modelSets.length && !modelSets.some((item) => item.id === modelSet)) {
      setModelSet(runMatrix?.defaults?.model_set ?? modelSets[0].id);
    }
    if (scenarioSets.length && !scenarioSets.some((item) => item.id === scenarioSet)) {
      setScenarioSet(runMatrix?.defaults?.scenario_set ?? scenarioSets[0].id);
    }
    if (selectableMemoryContexts.length) {
      const valid = new Set(selectableMemoryContexts.map((item) => item.id));
      const next = selectedMemoryContexts.filter((id) => valid.has(id));
      if (!next.length) next.push(runMatrix?.defaults?.memory_context ?? selectableMemoryContexts[0].id);
      if (next.length !== selectedMemoryContexts.length || next.some((id, index) => id !== selectedMemoryContexts[index])) {
        setSelectedMemoryContexts(next);
      }
    }
    if (inferenceStrategies.length && !inferenceStrategies.some((item) => item.id === inferenceStrategy)) {
      setInferenceStrategy(runMatrix?.defaults?.inference_strategy ?? inferenceStrategies[0].id);
    }
  }, [
    modelSets,
    scenarioSets,
    memoryContexts,
    inferenceStrategies,
    modelSet,
    scenarioSet,
    inferenceStrategy,
    selectedMemoryContexts,
    runMatrix?.defaults?.model_set,
    runMatrix?.defaults?.scenario_set,
    runMatrix?.defaults?.memory_context,
    runMatrix?.defaults?.inference_strategy,
  ]);

  const chosenModel = modelSets.find((item) => item.id === modelSet) ?? modelSets[0];
  const chosenScenario = scenarioSets.find((item) => item.id === scenarioSet) ?? scenarioSets[0];
  const chosenStrategy = inferenceStrategies.find((item) => item.id === inferenceStrategy) ?? inferenceStrategies[0];
  const orderedMemoryContexts = selectableMemoryContexts.filter((item) => selectedMemoryContexts.includes(item.id));
  const orderedMemoryContextIds = orderedMemoryContexts.map((item) => item.id);
  const memorySelectionKey = orderedMemoryContextIds.join("|");
  const primaryMemoryContext = orderedMemoryContexts[0]?.id ?? "";
  const modelCount = chosenModel?.model_count ?? 0;
  const scenarioCount = chosenScenario?.scenario_count ?? 0;
  const candidateCount = Math.max(chosenStrategy?.candidate_count ?? 1, 1);
  const memoryCount = Math.max(orderedMemoryContexts.length, 1);
  const answerRows = modelCount * scenarioCount * 5 * memoryCount;
  const inferenceUnits = answerRows * candidateCount;
  const judgeUnits = answerRows * 2;
  const totalWorkUnits = inferenceUnits + judgeUnits;
  const estimate = buildRunEstimate(totalWorkUnits);
  const judgeTokenEstimate = buildJudgeTokenEstimate(answerRows);
  const activeLocked = !!activeSession;
  const activeBatch = runBatches.find((batch) => ["running", "starting", "paused"].includes(batch.status));
  const activeRunId = activeBatch?.progress?.current_run_id ?? activeSession?.run_id ?? null;
  const activeState = activeBatch?.status === "paused" || activeSession?.state === "paused" ? "paused" : activeBatch || activeSession ? "running" : "idle";

  useEffect(() => {
    onSelectionChange?.({ modelSet, scenarioSet, memoryContext: primaryMemoryContext, memoryContexts: orderedMemoryContextIds, inferenceStrategy });
  }, [modelSet, scenarioSet, primaryMemoryContext, memorySelectionKey, inferenceStrategy, onSelectionChange]);

  async function run(action: string, fn: () => Promise<{ run_id?: string | null; batch_id?: string | null }>) {
    setBusy(action);
    setMsg(null);
    try {
      const result = await fn();
      setMsg(null);
      onAfter(result?.run_id ?? activeRunId ?? undefined);
    } catch (error) {
      setMsg(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  function startSingleRun() {
    if (!chosenModel || !chosenScenario || !orderedMemoryContexts.length) return;
    if (orderedMemoryContexts.length > 1) {
      startMemoryBatch();
      return;
    }
    const chosenMemory = orderedMemoryContexts[0];
    if (chosenModel.kind === "experiment") {
      const ok = window.confirm(
        `${chosenModel.label} can run for a long time on the ai node. Start ${chosenModel.id} × ${chosenScenario.id} × ${chosenMemory.id}?`,
      );
      if (!ok) return;
    }
    void run("start", () => control.start(chosenModel.id, chosenScenario.id, chosenMemory.id, inferenceStrategy));
  }

  function startMemoryBatch() {
    if (!chosenModel || !chosenScenario || orderedMemoryContexts.length < 2) return;
    if (chosenModel.kind === "experiment") {
      const ok = window.confirm(
        `${chosenModel.label} can run for a long time on the ai node. Queue ${orderedMemoryContexts.length} memory runs for ${chosenModel.id} × ${chosenScenario.id}?`,
      );
      if (!ok) return;
    }
    void run("batch", () => control.startBatch(chosenModel.id, chosenScenario.id, orderedMemoryContextIds, inferenceStrategy));
  }

  function requestPause() {
    if (!activeRunId) return;
    setConfirmAction({
      action: "pause",
      title: "Pause this experiment?",
      body: "Pause stops the active producer and judge, discards the current incomplete model, and leaves completed models intact. Resume will restart that model from its first scenario.",
    });
  }

  function requestCancel() {
    if (!activeRunId) return;
    setConfirmAction({
      action: "cancel",
      title: "Cancel this experiment?",
      body: "Cancel is terminal. The active child and queued memory contexts will be marked canceled; completed pushed evidence is left untouched.",
    });
  }

  function confirmLifecycleAction() {
    if (!confirmAction || !activeRunId) return;
    const action = confirmAction.action;
    setConfirmAction(null);
    if (action === "pause") {
      void run("pause", () => control.pause(activeRunId));
    } else {
      void run("cancel", () => control.stop(activeRunId));
    }
  }

  function resumeActive() {
    if (!activeRunId) return;
    void run("resume", () => control.resume(activeRunId));
  }

  const spin = (key: string, icon: React.ReactNode) =>
    busy === key ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : icon;

  function toggleMemoryContext(id: string) {
    setSelectedMemoryContexts((current) => {
      if (current.includes(id)) {
        return current.length === 1 ? current : current.filter((item) => item !== id);
      }
      return [...current, id];
    });
  }

  const startDisabled = !chosenModel || !chosenScenario || !chosenStrategy || !orderedMemoryContexts.length || busy != null || activeLocked || !!activeBatch;
  const startTitle = activeLocked || activeBatch
    ? "A run or memory batch is already active. Only one job can own the ai node."
    : undefined;
  const startLabel = orderedMemoryContexts.length > 1 ? `Start queued memory runs (${orderedMemoryContexts.length})` : "Start selected run";
  const compactSummary = `${modelCount} models · ${scenarioCount} scenarios · ${memoryCount} memory ${memoryCount === 1 ? "run" : "runs"} · ${chosenStrategy?.id ?? "baseline"} · ${judgeUnits.toLocaleString()} judge rows`;

  return (
    <Card
      title="Start New Experiment"
      icon={<Activity className="h-4 w-4 text-muted" />}
      right={<span className="text-xs text-faint">configure run axes</span>}
    >
      <div className="space-y-4">
        <div className="grid gap-3 lg:grid-cols-2">
          <RunShapePicker
            modelSets={modelSets}
            modelSet={modelSet}
            onModelSet={setModelSet}
            scenarioSets={scenarioSets}
            scenarioSet={scenarioSet}
            onScenarioSet={setScenarioSet}
          />
          <StrategyMemoryPicker
            strategies={inferenceStrategies}
            strategy={inferenceStrategy}
            onStrategy={setInferenceStrategy}
            contexts={selectableMemoryContexts}
            selected={selectedMemoryContexts}
            onToggle={toggleMemoryContext}
          />
        </div>

        {chosenScenario?.description && <p className="text-xs leading-relaxed text-muted">{chosenScenario.description}</p>}

        <div className="grid gap-1.5 rounded-xl border border-line bg-panel2/30 p-2 sm:grid-cols-2 md:grid-cols-5">
          <EstimateMetric
            icon={<Scale className="h-3.5 w-3.5" />}
            label="Answer rows"
            value={answerRows.toLocaleString()}
            sub={`${modelCount} models × ${scenarioCount} scenarios × 5 reps × ${memoryCount} memory`}
          />
          <EstimateMetric
            icon={<Timer className="h-3.5 w-3.5" />}
            label="Judge rows"
            value={judgeUnits.toLocaleString()}
            sub="2 judges for every answer row"
          />
          <EstimateMetric
            icon={<Workflow className="h-3.5 w-3.5" />}
            label="Inference calls"
            value={inferenceUnits.toLocaleString()}
            sub={`${candidateCount} candidate call${candidateCount === 1 ? "" : "s"} per answer`}
          />
          <EstimateMetric
            icon={<Clock className="h-3.5 w-3.5" />}
            label="Rough duration"
            value={estimate.duration}
            sub={estimate.assumption}
            hint="This is a launch estimate, not a live ETA. It uses the selected matrix size and the recent CEOps observed range of about 5-7 combined answer/judge units per minute."
          />
          <EstimateMetric
            icon={<Scale className="h-3.5 w-3.5" />}
            label="Frontier judge tokens"
            value={judgeTokenEstimate.input}
            sub={judgeTokenEstimate.detail}
            hint="Estimated Copilot frontier judge token volume. The input estimate uses about 27.6k input tokens per judge call; output is estimated at about 200 output tokens per judge JSON. Cache percentages are measured after the run from the Copilot CLI footer."
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-line bg-panel2/30 p-3">
          <span className="rounded bg-panel px-2 py-1 font-mono text-[10px] text-faint">{compactSummary}</span>
          <span className="inline-flex items-center gap-1 rounded border border-accent/30 bg-accent/10 px-2 py-1 font-mono text-[10px] font-semibold text-accent">
            <Clock className="h-3 w-3" />
            est {estimate.duration}
          </span>
          <span className="inline-flex items-center gap-1 rounded border border-info/30 bg-info/10 px-2 py-1 font-mono text-[10px] font-semibold text-info">
            <Scale className="h-3 w-3" />
            {judgeTokenEstimate.input}
          </span>
          <span className="hidden text-[11px] text-muted lg:inline-flex lg:items-center lg:gap-3">
            <span className="inline-flex items-center gap-1"><CheckCircle2 className="h-3 w-3 text-accent" />Quality</span>
            <span className="inline-flex items-center gap-1"><ShieldCheck className="h-3 w-3 text-accent" />Safety</span>
            <span className="inline-flex items-center gap-1"><Zap className="h-3 w-3 text-accent" />Energy</span>
            <span className="inline-flex items-center gap-1"><Workflow className="h-3 w-3 text-accent" />{inferenceStrategy}</span>
            <span className="inline-flex items-center gap-1"><Database className="h-3 w-3 text-accent" />{orderedMemoryContexts.map((item) => item.id).join(" + ") || "none"}</span>
          </span>
          {msg && <span className="max-w-xl truncate text-xs text-bad" title={msg}>{msg}</span>}
          {activeState === "running" && activeRunId && (
            <button type="button" disabled={busy != null} onClick={requestPause} className="btn border-warn/50 bg-warn/10 text-warn disabled:cursor-not-allowed disabled:opacity-40">
              {spin("pause", <Pause className="h-4 w-4" />)}
              Pause
            </button>
          )}
          {activeState === "paused" && activeRunId && (
            <button type="button" disabled={busy != null} onClick={resumeActive} className="btn border-accent/50 bg-accent/15 text-accent disabled:cursor-not-allowed disabled:opacity-40">
              {spin("resume", <RotateCw className="h-4 w-4" />)}
              Resume
            </button>
          )}
          {activeRunId && activeState !== "idle" && (
            <button type="button" disabled={busy != null} onClick={requestCancel} className="btn btn-danger disabled:cursor-not-allowed disabled:opacity-40">
              {spin("cancel", <Square className="h-4 w-4" />)}
              Cancel
            </button>
          )}
          <button
            type="button"
            disabled={startDisabled}
            title={startTitle}
            onClick={startSingleRun}
            className="btn btn-primary ml-auto disabled:cursor-not-allowed disabled:opacity-40"
          >
            {spin("start", <Rocket className="h-4 w-4" />)}
            {startLabel}
          </button>
        </div>
      </div>
      {confirmAction && (
        <ConfirmDialog
          title={confirmAction.title}
          body={confirmAction.body}
          tone={confirmAction.action === "pause" ? "warn" : "bad"}
          confirmLabel={confirmAction.action === "pause" ? "Pause and discard current model" : "Cancel experiment"}
          busy={busy === confirmAction.action}
          onCancel={() => setConfirmAction(null)}
          onConfirm={confirmLifecycleAction}
        />
      )}
    </Card>
  );
}

function EstimateMetric({
  icon,
  label,
  value,
  sub,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  hint?: string;
}) {
  return (
    <div className="min-w-0 rounded-lg border border-line/60 bg-panel/50 px-2.5 py-2">
      <div className="flex items-center gap-1 text-[9px] font-medium uppercase tracking-[0.1em] text-faint">
        {icon}
        {label}
        {hint && <Hint text={hint} align="end" />}
      </div>
      <div className="mt-0.5 truncate font-mono text-sm font-semibold tabular-nums text-fg" title={value}>{value}</div>
      <div className="mt-0.5 truncate text-[10px] text-muted" title={sub}>{sub}</div>
    </div>
  );
}

function buildRunEstimate(totalWorkUnits: number) {
  if (totalWorkUnits <= 0) return { duration: "—", assumption: "select a run shape" };
  const fastSeconds = (totalWorkUnits / 7) * 60;
  const slowSeconds = (totalWorkUnits / 5) * 60;
  return {
    duration: `${formatEstimateDuration(fastSeconds)}-${formatEstimateDuration(slowSeconds)}`,
    assumption: `${totalWorkUnits.toLocaleString()} combined units at 5-7/min`,
  };
}

function buildJudgeTokenEstimate(answerRows: number) {
  if (answerRows <= 0) return { input: "—", output: "—", detail: "select a run shape" };
  const perJudgeInputTokens = 27_600;
  const perJudgeOutputTokens = 200;
  const totalInput = answerRows * 2 * perJudgeInputTokens;
  const totalOutput = answerRows * 2 * perJudgeOutputTokens;
  return {
    input: formatTokenEstimate(totalInput),
    output: formatTokenEstimate(totalOutput),
    detail: `in ${formatTokenEstimate(totalInput)} · out ~${formatTokenEstimate(totalOutput)} · Claude ${answerRows.toLocaleString()} + GPT ${answerRows.toLocaleString()} calls`,
  };
}

function formatTokenEstimate(tokens: number) {
  if (tokens >= 1_000_000) return `${formatOneDecimal(tokens / 1_000_000)}M input tokens`;
  if (tokens >= 1_000) return `${formatOneDecimal(tokens / 1_000)}k input tokens`;
  return `${tokens} input tokens`;
}

function formatEstimateDuration(seconds: number) {
  const minutes = Math.max(1, Math.round(seconds / 60));
  if (minutes < 90) return `${minutes}m`;
  const hours = minutes / 60;
  if (hours < 24) return `${formatOneDecimal(hours)}h`;
  return `${formatOneDecimal(hours / 24)}d`;
}

function formatOneDecimal(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function RunShapePicker({
  modelSets,
  modelSet,
  onModelSet,
  scenarioSets,
  scenarioSet,
  onScenarioSet,
}: {
  modelSets: NonNullable<RunMatrix["model_sets"]>;
  modelSet: string;
  onModelSet: (id: string) => void;
  scenarioSets: NonNullable<RunMatrix["scenario_sets"]>;
  scenarioSet: string;
  onScenarioSet: (id: string) => void;
}) {
  return (
    <div className="rounded-xl border border-line bg-panel2/30 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="label">Model set / Scenario set</div>
        <span className="rounded bg-panel px-2 py-1 font-mono text-[10px] text-faint">run shape</span>
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        <OptionColumn
          label="Model set"
          value={modelSet}
          onChange={onModelSet}
          options={modelSets.map((item) => ({ id: item.id, label: item.label, meta: item.model_count != null ? `${item.model_count} models` : item.kind }))}
        />
        <OptionColumn
          label="Scenario set"
          value={scenarioSet}
          onChange={onScenarioSet}
          options={scenarioSets.map((item) => ({ id: item.id, label: item.label, meta: item.scenario_count != null ? `${item.scenario_count} scenarios` : item.kind }))}
        />
      </div>
    </div>
  );
}

function StrategyMemoryPicker({
  strategies,
  strategy,
  onStrategy,
  contexts,
  selected,
  onToggle,
}: {
  strategies: NonNullable<RunMatrix["inference_strategies"]>;
  strategy: string;
  onStrategy: (id: string) => void;
  contexts: NonNullable<RunMatrix["memory_contexts"]>;
  selected: string[];
  onToggle: (id: string) => void;
}) {
  return (
    <div className="rounded-xl border border-line bg-panel2/30 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="label">Inference strategy / Memory context</div>
        <span className="rounded bg-panel px-2 py-1 font-mono text-[10px] text-faint">strategy + memory</span>
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        <InferenceStrategyPicker strategies={strategies} value={strategy} onChange={onStrategy} />
        <MemoryContextPicker contexts={contexts} selected={selected} onToggle={onToggle} />
      </div>
    </div>
  );
}

function InferenceStrategyPicker({
  strategies,
  value,
  onChange,
}: {
  strategies: NonNullable<RunMatrix["inference_strategies"]>;
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-faint">Inference strategy</div>
        <span className="rounded bg-panel px-2 py-1 font-mono text-[10px] text-faint">{strategies.length} options</span>
      </div>
      <div className="max-h-[10.5rem] space-y-1.5 overflow-auto pr-1">
        {strategies.map((strategy) => {
          const checked = value === strategy.id;
          const calls = Math.max(strategy.candidate_count ?? 1, 1);
          return (
            <label key={strategy.id} className={`flex cursor-pointer items-center gap-2 rounded-lg border px-2.5 py-1.5 transition ${checked ? "border-accent/50 bg-accent/10" : "border-line/60 bg-panel/50 hover:border-accent/40"}`}>
              <input type="radio" checked={checked} onChange={() => onChange(strategy.id)} className="mt-0.5 h-4 w-4 border-line bg-panel text-accent focus:ring-accent" />
              <span className="min-w-0">
                <span className="flex flex-wrap items-center gap-1.5 text-xs font-medium text-fg">
                  {strategy.label}
                  {strategy.kind && <span className="rounded bg-info/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.08em] text-info">{strategy.kind}</span>}
                </span>
                <span className="mt-0.5 block font-mono text-[10px] text-faint">{strategy.id} · {calls} call{calls === 1 ? "" : "s"}/answer</span>
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

function OptionColumn({ label, value, onChange, options }: { label: string; value: string; onChange: (id: string) => void; options: { id: string; label: string; meta?: string }[] }) {
  return (
    <div>
      <div className="mb-1 text-[10px] font-medium uppercase tracking-[0.12em] text-faint">{label}</div>
      <div className="max-h-[10.5rem] space-y-1.5 overflow-auto pr-1">
        {options.map((option) => {
          const checked = value === option.id;
          return (
            <label key={option.id} className={`flex cursor-pointer items-center gap-2 rounded-lg border px-2.5 py-1.5 transition ${checked ? "border-accent/50 bg-accent/10" : "border-line/60 bg-panel/50 hover:border-accent/40"}`}>
              <input type="radio" checked={checked} onChange={() => onChange(option.id)} className="mt-0.5 h-4 w-4 border-line bg-panel text-accent focus:ring-accent" />
              <span className="min-w-0">
                <span className="block truncate text-xs font-medium text-fg">{option.label}</span>
                <span className="mt-0.5 block font-mono text-[10px] text-faint">{option.id}{option.meta ? ` · ${option.meta}` : ""}</span>
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

function MemoryContextPicker({
  contexts,
  selected,
  onToggle,
}: {
  contexts: NonNullable<RunMatrix["memory_contexts"]>;
  selected: string[];
  onToggle: (id: string) => void;
}) {
  const visibleContexts = contexts.filter((context) => context.kind !== "strategy").sort((left, right) => memorySortKey(left) - memorySortKey(right));
  const hasOverflow = visibleContexts.length > 3;
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-faint">Memory context</div>
        <span className="rounded bg-panel px-2 py-1 font-mono text-[10px] text-faint">
          {selected.length} selected · {visibleContexts.length} options{hasOverflow ? " · scroll" : ""}
        </span>
      </div>
      <div className="max-h-[10.5rem] space-y-1.5 overflow-auto pr-1">
        {visibleContexts.map((context) => {
          const checked = selected.includes(context.id);
          return (
            <label
              key={context.id}
              className={`flex cursor-pointer items-center gap-2 rounded-lg border px-2.5 py-1.5 transition ${
                checked ? "border-accent/50 bg-accent/10" : "border-line/60 bg-panel/50 hover:border-accent/40"
              }`}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => onToggle(context.id)}
                className="mt-0.5 h-4 w-4 rounded border-line bg-panel text-accent focus:ring-accent"
              />
              <span className="min-w-0">
                <span className="flex flex-wrap items-center gap-1.5 text-xs font-medium text-fg">
                  {context.label}
                  {context.kind === "strategy" && <span className="rounded bg-warn/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.08em] text-warn">strategy</span>}
                </span>
                <span className="mt-0.5 block font-mono text-[10px] text-faint">memory_context={context.id}</span>
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

function memorySortKey(context: NonNullable<RunMatrix["memory_contexts"]>[number]) {
  if (context.id === "none") return 0;
  if (context.kind === "strategy") return 1;
  if (context.id.includes("3kb")) return 2;
  return 3;
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