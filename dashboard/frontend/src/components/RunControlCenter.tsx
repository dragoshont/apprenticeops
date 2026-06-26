import { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  ChevronDown,
  Database,
  Loader2,
  Rocket,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { control } from "../api";
import type { RunBatch, RunMatrix, Session } from "../types";
import { Card } from "./ui";

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
  onSelectionChange?: (selection: { modelSet: string; scenarioSet: string; memoryContext: string; memoryContexts: string[] }) => void;
  onAfter: (runId?: string | null) => void;
}) {
  const [modelSet, setModelSet] = useState("");
  const [scenarioSet, setScenarioSet] = useState("");
  const [selectedMemoryContexts, setSelectedMemoryContexts] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const modelSets = runMatrix?.model_sets ?? [];
  const scenarioSets = runMatrix?.scenario_sets ?? [];
  const memoryContexts = runMatrix?.memory_contexts ?? [];

  useEffect(() => {
    if (modelSets.length && !modelSets.some((item) => item.id === modelSet)) {
      setModelSet(runMatrix?.defaults?.model_set ?? modelSets[0].id);
    }
    if (scenarioSets.length && !scenarioSets.some((item) => item.id === scenarioSet)) {
      setScenarioSet(runMatrix?.defaults?.scenario_set ?? scenarioSets[0].id);
    }
    if (memoryContexts.length) {
      const valid = new Set(memoryContexts.map((item) => item.id));
      const next = selectedMemoryContexts.filter((id) => valid.has(id));
      if (!next.length) next.push(runMatrix?.defaults?.memory_context ?? memoryContexts[0].id);
      if (next.length !== selectedMemoryContexts.length || next.some((id, index) => id !== selectedMemoryContexts[index])) {
        setSelectedMemoryContexts(next);
      }
    }
  }, [
    modelSets,
    scenarioSets,
    memoryContexts,
    modelSet,
    scenarioSet,
    selectedMemoryContexts,
    runMatrix?.defaults?.model_set,
    runMatrix?.defaults?.scenario_set,
    runMatrix?.defaults?.memory_context,
  ]);

  const chosenModel = modelSets.find((item) => item.id === modelSet) ?? modelSets[0];
  const chosenScenario = scenarioSets.find((item) => item.id === scenarioSet) ?? scenarioSets[0];
  const orderedMemoryContexts = memoryContexts.filter((item) => selectedMemoryContexts.includes(item.id));
  const orderedMemoryContextIds = orderedMemoryContexts.map((item) => item.id);
  const memorySelectionKey = orderedMemoryContextIds.join("|");
  const primaryMemoryContext = orderedMemoryContexts[0]?.id ?? "";
  const modelCount = chosenModel?.model_count ?? 0;
  const scenarioCount = chosenScenario?.scenario_count ?? 0;
  const memoryCount = Math.max(orderedMemoryContexts.length, 1);
  const inferenceUnits = modelCount * scenarioCount * 5 * memoryCount;
  const judgeUnits = inferenceUnits * 2;
  const activeLocked = !!activeSession;
  const activeBatch = runBatches.find((batch) => batch.status === "running" || batch.status === "starting");

  useEffect(() => {
    onSelectionChange?.({ modelSet, scenarioSet, memoryContext: primaryMemoryContext, memoryContexts: orderedMemoryContextIds });
  }, [modelSet, scenarioSet, primaryMemoryContext, memorySelectionKey, onSelectionChange]);

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
    void run("start", () => control.start(chosenModel.id, chosenScenario.id, chosenMemory.id));
  }

  function startMemoryBatch() {
    if (!chosenModel || !chosenScenario || orderedMemoryContexts.length < 2) return;
    if (chosenModel.kind === "experiment") {
      const ok = window.confirm(
        `${chosenModel.label} can run for a long time on the ai node. Queue ${orderedMemoryContexts.length} memory runs for ${chosenModel.id} × ${chosenScenario.id}?`,
      );
      if (!ok) return;
    }
    void run("batch", () => control.startBatch(chosenModel.id, chosenScenario.id, orderedMemoryContextIds));
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

  const startDisabled = !chosenModel || !chosenScenario || !orderedMemoryContexts.length || busy != null || activeLocked || !!activeBatch;
  const startTitle = activeLocked || activeBatch
    ? "A run or memory batch is already active. Only one job can own the ai node."
    : undefined;
  const startLabel = orderedMemoryContexts.length > 1 ? `Start queued memory runs (${orderedMemoryContexts.length})` : "Start selected run";

  return (
    <Card
      title="Experiment Control"
      icon={<Activity className="h-4 w-4 text-muted" />}
      right={<span className="text-xs text-faint">run axes</span>}
    >
      <div className="space-y-4">
          <div className="grid gap-3 lg:grid-cols-3">
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
            <MemoryContextPicker
              contexts={memoryContexts}
              selected={selectedMemoryContexts}
              onToggle={toggleMemoryContext}
            />
          </div>

          <div className="rounded-xl border border-line bg-panel2/30 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-fg">Experiment summary</div>
                <span className="rounded bg-panel px-2 py-1 font-mono text-[10px] text-faint">
                  {modelCount} models · {scenarioCount} scenarios · {memoryCount} memory {memoryCount === 1 ? "run" : "runs"} · 5 reps · {judgeUnits} judge rows
                </span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <Axis icon={<CheckCircle2 className="h-3.5 w-3.5" />} label="Quality" detail="judge score / frontier" />
                <Axis icon={<ShieldCheck className="h-3.5 w-3.5" />} label="Safety" detail="guard + secure refusal" />
                <Axis icon={<Zap className="h-3.5 w-3.5" />} label="Energy" detail="RAPL Wh / answer" />
                <Axis icon={<Database className="h-3.5 w-3.5" />} label="Memory" detail={orderedMemoryContexts.map((item) => item.id).join(" + ") || "none"} />
              </div>
              {chosenScenario?.description && (
                <p className="mt-3 text-xs leading-relaxed text-muted">{chosenScenario.description}</p>
              )}
            </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={startDisabled}
              title={startTitle}
              onClick={startSingleRun}
              className="btn btn-primary disabled:cursor-not-allowed disabled:opacity-40"
            >
              {spin("start", <Rocket className="h-4 w-4" />)}
              {startLabel}
            </button>
            {msg && <span className="max-w-xl truncate text-xs text-bad" title={msg}>{msg}</span>}
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

function MemoryContextPicker({
  contexts,
  selected,
  onToggle,
}: {
  contexts: NonNullable<RunMatrix["memory_contexts"]>;
  selected: string[];
  onToggle: (id: string) => void;
}) {
  return (
    <div className="rounded-xl border border-line bg-panel2/30 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="label">Memory contexts</div>
        <span className="rounded bg-panel px-2 py-1 font-mono text-[10px] text-faint">{selected.length} selected</span>
      </div>
      <div className="space-y-1.5">
        {contexts.map((context) => {
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
                <span className="block text-xs font-medium text-fg">{context.label}</span>
                <span className="mt-0.5 block font-mono text-[10px] text-faint">memory_context={context.id}</span>
              </span>
            </label>
          );
        })}
      </div>
    </div>
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