import type { Progress } from "../types";
import { Bar } from "./ui";
import { Gauge, Cpu, Scale, Clock, Timer } from "lucide-react";

function Row({
  icon,
  label,
  done,
  total,
  tone,
  live,
}: {
  icon: React.ReactNode;
  label: string;
  done: number;
  total: number;
  tone: string;
  live: boolean;
}) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="flex items-center gap-1.5 font-medium text-muted">
          {icon}
          {label}
        </span>
        <span className="font-mono text-faint">
          <span className="text-fg">{done.toLocaleString()}</span> / {total.toLocaleString()}
          <span className="ml-2 tabular-nums text-muted">{pct}%</span>
        </span>
      </div>
      <Bar value={done} max={total} tone={tone} live={live} className="h-2.5" />
    </div>
  );
}

export function RunProgress({ progress, live }: { progress?: Progress; live: boolean }) {
  const p = progress;
  const pct = p?.pct ?? 0;
  return (
    <div className="card card-pad">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
        {/* big number */}
        <div className="flex items-center gap-4 sm:w-64 sm:shrink-0">
          <div className="relative grid h-20 w-20 place-items-center">
            <svg viewBox="0 0 36 36" className="h-20 w-20 -rotate-90">
              <circle cx="18" cy="18" r="15.5" fill="none" className="stroke-line" strokeWidth="3" />
              <circle
                cx="18"
                cy="18"
                r="15.5"
                fill="none"
                className="stroke-accent transition-all duration-700"
                strokeWidth="3"
                strokeLinecap="round"
                strokeDasharray={`${(pct / 100) * 97.4} 97.4`}
              />
            </svg>
            <span className="absolute font-mono text-lg font-bold text-fg tabular-nums">
              {Math.round(pct)}%
            </span>
          </div>
          <div className="space-y-1">
            <div className="label flex items-center gap-1.5">
              <Gauge className="h-3.5 w-3.5" /> Run progress
            </div>
            <div className="text-sm text-muted">
              {p?.pct_remaining != null ? `${p.pct_remaining}% remaining` : "—"}
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-faint">
              <span className="flex items-center gap-1">
                <Timer className="h-3 w-3" />
                ETA {p?.eta_human ?? (live ? "calculating…" : "—")}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {p?.elapsed_s ? `${Math.floor(p.elapsed_s / 60)}m elapsed` : "—"}
              </span>
            </div>
          </div>
        </div>

        {/* bars */}
        <div className="flex-1 space-y-3">
          <Row
            icon={<Cpu className="h-3.5 w-3.5" />}
            label="Inference (ai)"
            done={p?.inf_done ?? 0}
            total={p?.inf_total ?? 0}
            tone="info"
            live={live}
          />
          <Row
            icon={<Scale className="h-3.5 w-3.5" />}
            label="Judge (home)"
            done={p?.judge_done ?? 0}
            total={p?.judge_total ?? 0}
            tone="warn"
            live={live}
          />
          {p?.rate_per_min != null && (
            <div className="text-right text-[11px] text-faint">
              {p.rate_per_min} units/min
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
