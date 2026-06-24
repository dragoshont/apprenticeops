import { useMemo, useState } from "react";
import type { ModelProgress } from "../types";
import { Card, Bar } from "./ui";
import { Boxes, Search, Check } from "lucide-react";

const STAGE_TONE: Record<string, string> = {
  infer: "text-info",
  emit: "text-info",
  judge: "text-warn",
  persist: "text-good",
};

function ModelRow({ m }: { m: ModelProgress }) {
  const infPct = m.inf_total ? Math.round((m.inf_done / m.inf_total) * 100) : 0;
  const judgePct = m.judge_total ? Math.round((m.judge_done / m.judge_total) * 100) : 0;
  const live = !m.committed && (infPct > 0 || judgePct > 0) && (infPct < 100 || judgePct < 100);
  return (
    <div className="rounded-lg px-2 py-2 transition hover:bg-panel2/50">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 truncate font-mono text-xs text-fg">
          {m.committed && <Check className="h-3 w-3 shrink-0 text-good" />}
          {m.model}
        </span>
        <span className={`text-[10px] font-medium uppercase tracking-wide ${STAGE_TONE[m.stage] ?? "text-muted"}`}>
          {m.stage}
        </span>
      </div>
      <div className="grid grid-cols-[2.6rem_1fr_3.2rem] items-center gap-2 text-[10px]">
        <span className="text-faint">inf</span>
        <Bar value={m.inf_done} max={m.inf_total} tone="info" live={live} className="h-1.5" />
        <span className="text-right font-mono tabular-nums text-faint">
          {m.inf_done}/{m.inf_total}
        </span>
        <span className="text-faint">judge</span>
        <Bar value={m.judge_done} max={m.judge_total} tone="warn" live={live} className="h-1.5" />
        <span className="text-right font-mono tabular-nums text-faint">
          {m.judge_done}/{m.judge_total}
        </span>
      </div>
    </div>
  );
}

export function ModelBars({ models }: { models: ModelProgress[] }) {
  const [q, setQ] = useState("");
  const sorted = useMemo(() => {
    const rank = (m: ModelProgress) => (m.committed ? 2 : m.inf_done + m.judge_done > 0 ? 0 : 1);
    return [...models]
      .filter((m) => m.model.toLowerCase().includes(q.toLowerCase()))
      .sort((a, b) => {
        const r = rank(a) - rank(b);
        if (r) return r;
        return b.inf_done + b.judge_done - (a.inf_done + a.judge_done) || a.model.localeCompare(b.model);
      });
  }, [models, q]);

  const done = models.filter((m) => m.committed).length;

  return (
    <Card
      title="Models"
      icon={<Boxes className="h-4 w-4 text-muted" />}
      right={
        <span className="text-xs text-faint">
          {done}/{models.length} done
        </span>
      }
    >
      {models.length > 12 && (
        <div className="relative mb-2">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="filter models…"
            className="w-full rounded-lg border border-line bg-panel2/50 py-1.5 pl-8 pr-3 text-xs text-fg placeholder:text-faint focus:border-accent/60 focus:outline-none"
          />
        </div>
      )}
      {sorted.length === 0 ? (
        <p className="py-6 text-center text-sm text-faint">
          {models.length ? "No models match." : "No models in flight yet."}
        </p>
      ) : (
        <div className="max-h-[26rem] space-y-0.5 overflow-auto pr-1">
          {sorted.map((m) => (
            <ModelRow key={m.model} m={m} />
          ))}
        </div>
      )}
    </Card>
  );
}
