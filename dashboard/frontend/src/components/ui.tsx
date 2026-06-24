import type { ReactNode } from "react";
import type { PipelineState } from "../types";

export function Card({
  title,
  icon,
  right,
  children,
  className = "",
}: {
  title?: string;
  icon?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card card-pad ${className}`}>
      {(title || right) && (
        <header className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            {icon}
            {title}
          </h2>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}

const STATE_STYLE: Record<PipelineState, string> = {
  running: "bg-good/15 text-good ring-1 ring-good/30",
  paused: "bg-warn/15 text-warn ring-1 ring-warn/30",
  done: "bg-accent/15 text-accent ring-1 ring-accent/30",
  idle: "bg-slate-500/15 text-slate-400 ring-1 ring-slate-500/30",
  error: "bg-bad/15 text-bad ring-1 ring-bad/30",
};

export function StatePill({ state }: { state: PipelineState }) {
  const dot: Record<PipelineState, string> = {
    running: "bg-good animate-pulse",
    paused: "bg-warn",
    done: "bg-accent",
    idle: "bg-slate-500",
    error: "bg-bad animate-pulse",
  };
  return (
    <span className={`pill ${STATE_STYLE[state]}`}>
      <span className={`h-2 w-2 rounded-full ${dot[state]}`} />
      {state.toUpperCase()}
    </span>
  );
}

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="stat mt-1">{value}</div>
      {sub != null && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

export function Bar({ value, max, tone = "accent" }: { value: number; max: number; tone?: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const c =
    tone === "good" ? "bg-good" : tone === "warn" ? "bg-warn" : tone === "bad" ? "bg-bad" : "bg-accent";
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-line">
      <div className={`h-full rounded-full ${c} transition-all duration-700`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function fmtAgo(ts?: number) {
  if (!ts) return "—";
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}
