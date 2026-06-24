import { Card } from "./ui";
import { STAGE_ORDER } from "../types";
import type { ModelStage } from "../types";
import { Boxes } from "lucide-react";

const STAGE_TONE: Record<string, string> = {
  lock: "bg-slate-500/15 text-slate-400",
  reset: "bg-slate-500/15 text-slate-400",
  infer: "bg-accent/15 text-accent",
  emit: "bg-accent/15 text-accent",
  collect: "bg-sky-500/15 text-sky-300",
  judge: "bg-warn/15 text-warn",
  persist: "bg-good/15 text-good",
};

export function ModelBoard({ models }: { models: ModelStage[] }) {
  const sorted = [...models].sort((a, b) => {
    const ra = STAGE_ORDER.indexOf(a.stage as never);
    const rb = STAGE_ORDER.indexOf(b.stage as never);
    if (rb !== ra) return rb - ra;
    return a.model.localeCompare(b.model);
  });

  return (
    <Card title="Models" icon={<Boxes className="h-4 w-4 text-slate-400" />} right={<span className="text-xs text-slate-500">{models.length}</span>}>
      {sorted.length === 0 ? (
        <p className="py-6 text-center text-sm text-slate-600">No models in flight yet.</p>
      ) : (
        <ul className="max-h-[22rem] space-y-1 overflow-auto pr-1">
          {sorted.map((m) => {
            const idx = STAGE_ORDER.indexOf(m.stage as never);
            const pct = idx >= 0 ? ((idx + 1) / STAGE_ORDER.length) * 100 : 0;
            return (
              <li
                key={m.model}
                className="group flex items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-ink-800/60"
              >
                <span className="w-1.5 self-stretch rounded-full bg-line">
                  <span
                    className="block w-full rounded-full bg-accent/70"
                    style={{ height: `${pct}%` }}
                  />
                </span>
                <span className="flex-1 truncate font-mono text-xs text-slate-300">{m.model}</span>
                <span className={`pill ${STAGE_TONE[m.stage] ?? "bg-slate-500/15 text-slate-400"} capitalize`}>
                  {m.stage}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
