import { STAGE_ORDER } from "../types";
import type { ModelStage } from "../types";

const META: Record<string, { n: string; node: "ai" | "home" }> = {
  lock: { n: "S1", node: "ai" },
  reset: { n: "S2", node: "ai" },
  infer: { n: "S3", node: "ai" },
  emit: { n: "S4", node: "ai" },
  collect: { n: "S5", node: "home" },
  judge: { n: "S6", node: "home" },
  persist: { n: "S7", node: "home" },
};

function activeStage(models: ModelStage[], producerAlive: boolean, consumerAlive: boolean): string | null {
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

/** Compact one-line pipeline strip: 7 stage chips with the live one highlighted.
 * Deliberately small — the progress bars are the hero; this is just orientation. */
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

  return (
    <div className="card flex flex-wrap items-center gap-x-1 gap-y-2 px-4 py-2.5">
      <span className="mr-1 text-[11px] font-medium uppercase tracking-wider text-faint">Pipeline</span>
      {STAGE_ORDER.map((s, i) => {
        const m = META[s];
        const isLive = i === liveIdx;
        const isPast = liveIdx >= 0 && i < liveIdx;
        const nodeColor = m.node === "ai" ? "text-accent" : "text-good";
        return (
          <div key={s} className="flex items-center">
            <span
              className={[
                "inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] transition",
                isLive
                  ? "bg-accent/15 font-semibold text-accent ring-1 ring-accent/30"
                  : isPast
                    ? "text-muted"
                    : "text-faint",
              ].join(" ")}
            >
              <span className={`font-mono ${isLive ? nodeColor : ""}`}>{m.n}</span>
              <span className="capitalize">{s}</span>
              {isLive && <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />}
            </span>
            {i < STAGE_ORDER.length - 1 && (
              <span className={`mx-0.5 h-px w-2 ${isPast ? "bg-muted/40" : "bg-line"}`} />
            )}
          </div>
        );
      })}
      <span className="ml-auto flex items-center gap-2.5 text-[10px] text-faint">
        <span className="inline-flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-accent/70" /> ai
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-good/70" /> home
        </span>
      </span>
    </div>
  );
}
