import type { ReactNode } from "react";

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
          <h2 className="flex items-center gap-2 text-sm font-semibold text-fg">
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

const STATE_STYLE: Record<string, string> = {
  running: "bg-good/15 text-good ring-1 ring-good/30",
  paused: "bg-warn/15 text-warn ring-1 ring-warn/30",
  done: "bg-accent/15 text-accent ring-1 ring-accent/30",
  canceled: "bg-bad/15 text-bad ring-1 ring-bad/30",
  stopped: "bg-muted/15 text-muted ring-1 ring-muted/25",
  idle: "bg-muted/15 text-muted ring-1 ring-muted/25",
  error: "bg-bad/15 text-bad ring-1 ring-bad/30",
};

const DOT: Record<string, string> = {
  running: "bg-good animate-pulse",
  paused: "bg-warn",
  done: "bg-accent",
  canceled: "bg-bad",
  stopped: "bg-muted",
  idle: "bg-muted",
  error: "bg-bad animate-pulse",
};

export function StatePill({ state, size = "md" }: { state: string; size?: "sm" | "md" }) {
  const cls = STATE_STYLE[state] ?? STATE_STYLE.idle;
  const pad = size === "sm" ? "px-2 py-0.5 text-[10px]" : "";
  return (
    <span className={`pill ${cls} ${pad}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${DOT[state] ?? DOT.idle}`} />
      {state.toUpperCase()}
    </span>
  );
}

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="stat mt-1">{value}</div>
      {sub != null && <div className="mt-0.5 text-xs text-faint">{sub}</div>}
    </div>
  );
}

const TONE: Record<string, string> = {
  accent: "bg-accent",
  good: "bg-good",
  warn: "bg-warn",
  bad: "bg-bad",
  info: "bg-info",
};

export function Bar({
  value,
  max,
  tone = "accent",
  live = false,
  className = "",
}: {
  value: number;
  max: number;
  tone?: string;
  live?: boolean;
  className?: string;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className={`track ${live && pct > 0 && pct < 100 ? "track-live" : ""} ${className}`}>
      <div
        className={`h-full rounded-full ${TONE[tone] ?? TONE.accent} transition-all duration-700`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function fmtAgo(ts?: number | null) {
  if (!ts) return "—";
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export function fmtDur(seconds?: number | null) {
  if (seconds == null || seconds < 0) return "—";
  const s = Math.floor(seconds);
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d) return `${d}d ${h}h ${m}m`;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${s % 60}s`;
  return `${s}s`;
}

export function fmtClock(ts?: number | null) {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
