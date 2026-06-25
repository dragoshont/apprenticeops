import { useEffect, useState } from "react";
import { Play, Pause, RotateCw, Square, ChevronDown, Loader2 } from "lucide-react";
import { control } from "../api";
import type { RunMatrix } from "../types";

export function Controls({
  state,
  runId,
  runMatrix,
  onAfter,
  liveElsewhere = false,
}: {
  state: string;
  runId: string | null;
  runMatrix?: RunMatrix | null;
  onAfter: (runId?: string | null) => void;
  liveElsewhere?: boolean;
}) {
  const [modelSet, setModelSet] = useState<string>("");
  const [scenarioSet, setScenarioSet] = useState<string>("");
  const [memoryContext, setMemoryContext] = useState<string>("");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const modelSets = runMatrix?.model_sets ?? [];
  const scenarioSets = runMatrix?.scenario_sets ?? [];
  const memoryContexts = runMatrix?.memory_contexts ?? [];
  const experimentPlans = runMatrix?.experiment_plans ?? [];

  // Matrix options load on the first status poll; default to the server-provided
  // ids and keep selections pointed at existing options.
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
  }, [modelSets, scenarioSets, memoryContexts, modelSet, scenarioSet, memoryContext, runMatrix?.defaults?.model_set, runMatrix?.defaults?.scenario_set, runMatrix?.defaults?.memory_context]);

  const running = state === "running";
  const paused = state === "paused";
  const stopped = state === "stopped";
  const active = running || paused;
  const chosenModel = modelSets.find((item) => item.id === modelSet) ?? modelSets[0];
  const chosenScenario = scenarioSets.find((item) => item.id === scenarioSet) ?? scenarioSets[0];
  const chosenMemory = memoryContexts.find((item) => item.id === memoryContext) ?? memoryContexts[0];
  const modelCount = chosenModel?.model_count ?? 0;
  const scenarioCount = chosenScenario?.scenario_count ?? 0;
  const inferenceUnits = modelCount * scenarioCount * 5;
  const judgeUnits = inferenceUnits * 2;

  async function run(action: string, fn: () => Promise<{ run_id?: string }>) {
    setBusy(action);
    setMsg(null);
    try {
      const r = await fn();
      setMsg(null);
      onAfter(r?.run_id ?? undefined);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  const spin = (k: string, icon: React.ReactNode) =>
    busy === k ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : icon;

  const cbtn =
    "inline-flex items-center gap-1 rounded-lg border border-line bg-panel2/50 px-2.5 py-1.5 text-xs font-medium text-fg transition hover:border-accent/50 disabled:cursor-not-allowed disabled:opacity-40";

  const startPhase = (memoryId: string) => {
    const memory = memoryContexts.find((item) => item.id === memoryId);
    if (chosenModel && chosenScenario && memory) {
      setMemoryContext(memory.id);
      run("start", () => control.start(chosenModel.id, chosenScenario.id, memory.id));
    }
  };

  return (
    <div className="flex flex-col gap-2">
      {!active && experimentPlans.length > 0 && (
        <div className="rounded-lg border border-line bg-panel2/40 px-3 py-2 text-xs">
          {experimentPlans.map((plan) => (
            <div key={plan.id} className="space-y-2">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="font-medium text-fg">{plan.label}</div>
                  {plan.description && <div className="mt-0.5 max-w-3xl text-faint">{plan.description}</div>}
                </div>
                {plan.gate && <div className="max-w-lg text-[11px] text-muted">Gate: {plan.gate}</div>}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {plan.phases.map((phase, index) => {
                  const phaseMemory = memoryContexts.find((item) => item.id === phase.memory_context);
                  return (
                    <button
                      key={phase.id}
                      type="button"
                      className="inline-flex items-center gap-1 rounded-lg border border-line bg-panel/70 px-2.5 py-1.5 text-[11px] font-medium text-fg transition hover:border-accent/50 disabled:cursor-not-allowed disabled:opacity-40"
                      disabled={!chosenModel || !chosenScenario || !phaseMemory || busy != null || liveElsewhere}
                      title={phase.gate || phaseMemory?.description}
                      onClick={() => startPhase(phase.memory_context)}
                    >
                      {busy === "start" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                      {index + 1}. {phase.label}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-1.5">
      {!active && (
        <div className="flex flex-wrap items-center overflow-hidden rounded-lg border border-line bg-panel2 text-xs">
          <div className="relative">
            <select
              aria-label="Model list"
              value={modelSet}
              onChange={(e) => setModelSet(e.target.value)}
              className="appearance-none bg-transparent py-1.5 pl-2.5 pr-7 text-xs text-fg focus:outline-none"
            >
              {modelSets.map((item) => (
                <option key={item.id} value={item.id} className="bg-panel text-fg">
                  {item.label}
                  {item.model_count != null ? ` · ${item.model_count}` : ""}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
          </div>
          <div className="relative border-l border-line">
            <select
              aria-label="Scenario set"
              value={scenarioSet}
              onChange={(e) => setScenarioSet(e.target.value)}
              className="appearance-none bg-transparent py-1.5 pl-2.5 pr-7 text-xs text-fg focus:outline-none"
            >
              {scenarioSets.map((item) => (
                <option key={item.id} value={item.id} className="bg-panel text-fg">
                  {item.label}
                  {item.scenario_count != null ? ` · ${item.scenario_count}` : ""}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
          </div>
          <div className="relative border-l border-line">
            <select
              aria-label="Memory context"
              value={memoryContext}
              onChange={(e) => setMemoryContext(e.target.value)}
              className="appearance-none bg-transparent py-1.5 pl-2.5 pr-7 text-xs text-fg focus:outline-none"
            >
              {memoryContexts.map((item) => (
                <option key={item.id} value={item.id} className="bg-panel text-fg">
                  {item.label}
                  {item.byte_count ? ` · ${Math.ceil(item.byte_count / 1024)}KB` : ""}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
          </div>
          {chosenModel && chosenScenario && chosenMemory && (
            <span
              className="hidden border-l border-line px-2.5 py-1.5 font-mono text-[10px] text-faint md:inline"
              title={`${modelCount} models × ${scenarioCount} scenarios × 5 reps = ${inferenceUnits} inference units; ×2 judges = ${judgeUnits} judge units; memory=${chosenMemory.id}`}
            >
              {modelCount}m×{scenarioCount}s×5 · {judgeUnits}j · {chosenMemory.id}
            </span>
          )}
          <button
            className="inline-flex items-center gap-1 border-l border-line bg-accent/15 px-2.5 py-1.5 font-medium text-accent transition hover:bg-accent/25 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!chosenModel || !chosenScenario || !chosenMemory || busy != null || liveElsewhere}
            title={liveElsewhere ? "A run is already running or paused — only one run can use the ai node. Follow it to control it." : undefined}
            onClick={() => chosenModel && chosenScenario && chosenMemory && run("start", () => control.start(chosenModel.id, chosenScenario.id, chosenMemory.id))}
          >
            {spin("start", <Play className="h-3.5 w-3.5" />)}
            Start
          </button>
        </div>
      )}

      {running && (
        <button className={cbtn} disabled={busy != null} onClick={() => run("pause", () => control.pause(runId))}>
          {spin("pause", <Pause className="h-3.5 w-3.5" />)}
          Pause
        </button>
      )}

      {(paused || stopped) && (
        <button
          className={`${cbtn} border-accent/50 bg-accent/15 text-accent`}
          disabled={busy != null}
          onClick={() => run("resume", () => control.resume(runId))}
        >
          {spin("resume", <RotateCw className="h-3.5 w-3.5" />)}
          {paused ? "Resume" : "Continue"}
        </button>
      )}

      {active && (
        <button
          className={`${cbtn} hover:border-bad/60 hover:bg-bad/10 hover:text-bad`}
          disabled={busy != null}
          onClick={() => run("stop", () => control.stop(runId))}
        >
          {spin("stop", <Square className="h-3.5 w-3.5" />)}
          Cancel
        </button>
      )}

      {msg && <span className="max-w-[16rem] truncate text-xs text-bad" title={msg}>{msg}</span>}
      </div>
    </div>
  );
}
