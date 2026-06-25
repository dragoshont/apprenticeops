import { useState } from "react";
import { FlaskConical, Loader2, Play } from "lucide-react";
import { control } from "../api";
import type { ExperimentState, RunMatrix } from "../types";
import { Card, StatePill } from "./ui";

export function ExperimentPlanCard({
  runMatrix,
  experiments,
  runActive,
  onAfter,
}: {
  runMatrix?: RunMatrix | null;
  experiments: ExperimentState[];
  runActive: boolean;
  onAfter: (runId?: string | null) => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const plans = runMatrix?.experiment_plans ?? [];
  const modelSet = runMatrix?.defaults?.model_set ?? runMatrix?.model_sets?.[0]?.id;
  const scenarioSet = runMatrix?.defaults?.scenario_set ?? runMatrix?.scenario_sets?.[0]?.id;
  const memoryContexts = runMatrix?.memory_contexts ?? [];

  if (!plans.length || !modelSet || !scenarioSet) return null;

  async function startPhase(planId: string, phaseId: string) {
    if (!modelSet || !scenarioSet) return;
    const existing = experiments.find(
      (item) => item.plan_id === planId && item.model_set === modelSet && item.scenario_set === scenarioSet,
    );
    setBusy(`${planId}:${phaseId}`);
    setMsg(null);
    try {
      const result = await control.startPhase(planId, phaseId, modelSet, scenarioSet, existing?.experiment_id);
      onAfter(result?.run_id ?? null);
    } catch (error) {
      setMsg(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card
      title="Experiment Plan"
      icon={<FlaskConical className="h-4 w-4 text-muted" />}
      right={<span className="text-xs text-faint">{modelSet} × {scenarioSet}</span>}
    >
      <div className="space-y-4">
        {plans.map((plan) => {
          const existing = experiments.find(
            (item) => item.plan_id === plan.id && item.model_set === modelSet && item.scenario_set === scenarioSet,
          );
          return (
            <div key={plan.id} className="space-y-3">
              <div className="grid gap-2 md:grid-cols-[1fr_1.1fr]">
                <div>
                  <div className="text-sm font-medium text-fg">{plan.label}</div>
                  {plan.description && <p className="mt-1 text-xs leading-relaxed text-muted">{plan.description}</p>}
                </div>
                {plan.gate && (
                  <div className="rounded-lg border border-line bg-panel2/40 px-3 py-2 text-[11px] leading-relaxed text-muted">
                    Gate: {plan.gate}
                  </div>
                )}
              </div>

              <div className="grid gap-2 md:grid-cols-2">
                {plan.phases.map((phase, index) => {
                  const phaseState = existing?.phases.find((item) => item.id === phase.id);
                  const status = phaseState?.status ?? "pending";
                  const priorPhasesCompleted = plan.phases
                    .slice(0, index)
                    .every((prior) => existing?.phases.find((item) => item.id === prior.id)?.status === "completed");
                  const memory = memoryContexts.find((item) => item.id === phase.memory_context);
                  const actionKey = `${plan.id}:${phase.id}`;
                  const canStart = status === "pending" && priorPhasesCompleted && !runActive;
                  const disabledReason = runActive
                    ? "A run is already running or paused."
                    : status !== "pending"
                      ? `Phase status is ${status}.`
                      : !priorPhasesCompleted
                        ? "Complete and review the previous phase first."
                        : undefined;
                  return (
                    <div key={phase.id} className="rounded-xl border border-line bg-panel2/30 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-mono text-[10px] text-faint">PHASE {index + 1}</div>
                          <div className="mt-1 text-sm font-medium text-fg">{phase.label}</div>
                        </div>
                        <StatePill state={status} size="sm" />
                      </div>
                      <div className="mt-2 text-xs text-muted">Memory: {memory?.label ?? phase.memory_context}</div>
                      {phase.gate && <div className="mt-2 text-[11px] leading-relaxed text-faint">{phase.gate}</div>}
                      <button
                        type="button"
                        disabled={busy != null || !canStart}
                        title={disabledReason}
                        onClick={() => startPhase(plan.id, phase.id)}
                        className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-line bg-panel px-2.5 py-1.5 text-xs font-medium text-fg transition hover:border-accent/50 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {busy === actionKey ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                        {priorPhasesCompleted ? `Start Phase ${index + 1}` : "Locked"}
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
        {msg && <div className="rounded-lg border border-bad/30 bg-bad/10 px-3 py-2 text-xs text-bad">{msg}</div>}
      </div>
    </Card>
  );
}