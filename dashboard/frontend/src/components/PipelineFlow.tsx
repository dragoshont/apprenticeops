import { STAGE_ORDER } from "../types";
import type { ModelStage } from "../types";
import {
  Lock,
  RotateCcw,
  Cpu,
  Upload,
  Download,
  Scale,
  GitCommit,
} from "lucide-react";

const META: Record<
  string,
  { n: string; icon: typeof Lock; node: "ai" | "home"; desc: string }
> = {
  lock: { n: "S1", icon: Lock, node: "ai", desc: "Lock the inference node" },
  reset: { n: "S2", icon: RotateCcw, node: "ai", desc: "Reset env before model" },
  infer: { n: "S3", icon: Cpu, node: "ai", desc: "Run scenarios × reps" },
  emit: { n: "S4", icon: Upload, node: "ai", desc: "Append result rows" },
  collect: { n: "S5", icon: Download, node: "home", desc: "Mirror results to home" },
  judge: { n: "S6", icon: Scale, node: "home", desc: "Ensemble judges, 8-wide" },
  persist: { n: "S7", icon: GitCommit, node: "home", desc: "Commit judged model" },
};

/** Which stage is "live" right now, inferred from producer/consumer activity. */
function activeStage(models: ModelStage[], producerAlive: boolean, consumerAlive: boolean): string | null {
  // The most-advanced model that is not yet persisted hints at the live stage.
  const ranks = STAGE_ORDER as readonly string[];
  let best = -1;
  for (const m of models) {
    const r = ranks.indexOf(m.stage);
    if (m.stage !== "persist" && r > best) best = r;
  }
  if (best >= 0) return ranks[best];
  if (producerAlive) return "infer";
  if (consumerAlive) return "judge";
  return null;
}

export function PipelineFlow({
  models,
  producerAlive,
  consumerAlive,
}: {
  models: ModelStage[];
  producerAlive: boolean;
  consumerAlive: boolean;
}) {
  const live = activeStage(models, producerAlive, consumerAlive);
  const liveIdx = live ? (STAGE_ORDER as readonly string[]).indexOf(live) : -1;
  const counts = new Map<string, number>();
  for (const m of models) counts.set(m.stage, (counts.get(m.stage) ?? 0) + 1);

  return (
    <div className="card card-pad">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Pipeline</h2>
        <div className="flex items-center gap-3 text-[11px] text-slate-500">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-accent/70" /> ai · inference
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-good/70" /> home · judge
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
        {STAGE_ORDER.map((s, i) => {
          const m = META[s];
          const Icon = m.icon;
          const isLive = i === liveIdx;
          const isPast = liveIdx >= 0 && i < liveIdx;
          const here = counts.get(s) ?? 0;
          const nodeColor = m.node === "ai" ? "text-accent" : "text-good";
          return (
            <div key={s} className="relative">
              <div
                className={[
                  "flex flex-col gap-2 rounded-xl border p-3 transition",
                  isLive
                    ? "border-accent/50 bg-accent/10 shadow-glow"
                    : isPast
                      ? "border-line bg-ink-800/60"
                      : "border-line/60 bg-ink-850/40",
                ].join(" ")}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[11px] font-semibold text-slate-500">{m.n}</span>
                  <Icon
                    className={`h-4 w-4 ${isLive ? nodeColor : isPast ? "text-slate-400" : "text-slate-600"} ${
                      isLive ? "animate-pulseline" : ""
                    }`}
                  />
                </div>
                <div>
                  <div className="text-xs font-semibold capitalize text-slate-200">{s}</div>
                  <div className="mt-0.5 text-[10px] leading-tight text-slate-500">{m.desc}</div>
                </div>
                {here > 0 && (
                  <div className="text-[10px] font-medium text-slate-400">
                    {here} model{here > 1 ? "s" : ""}
                  </div>
                )}
              </div>
              {i < STAGE_ORDER.length - 1 && (
                <div className="absolute -right-1.5 top-1/2 hidden h-px w-3 -translate-y-1/2 bg-line lg:block" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
