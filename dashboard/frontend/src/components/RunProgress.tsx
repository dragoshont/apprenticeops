import type { PersistenceStatus, Progress, AnalyticsScope, ReliabilityReport } from "../types";
import { Bar, Hint } from "./ui";
import { Gauge, Cpu, Scale, Clock, Timer } from "lucide-react";

function Row({
  icon,
  label,
  done,
  total,
  tone,
  live,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  done: number;
  total: number;
  tone: string;
  live: boolean;
  hint?: string;
}) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="flex items-center gap-1.5 font-medium text-muted">
          {icon}
          {label}
          {hint && <Hint text={hint} />}
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

function persistenceCopy(persistence?: PersistenceStatus) {
  if (!persistence) return null;
  if (persistence.status === "clean") return "Persistence complete: all model evidence pushed.";
  if (persistence.status === "retrying_push") return `Judged complete; retrying git push for ${persistence.push_pending_count} model(s).`;
  if (persistence.status === "not_expected") return "Persistence not expected for this inference-only run.";
  return `Persistence ${persistence.status}: ${persistence.committed_count}/${persistence.committed_total} models pushed.`;
}

export function RunProgress({
  progress,
  live,
  scope,
  persistence,
  batchNotice,
  reliability,
}: {
  progress?: Progress;
  live: boolean;
  scope?: AnalyticsScope;
  persistence?: PersistenceStatus;
  batchNotice?: string | null;
  reliability?: ReliabilityReport | null;
}) {
  const p = progress;
  const pct = p?.pct ?? 0;
  const persistenceText = persistenceCopy(persistence);
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
              <Gauge className="h-3.5 w-3.5" /> Selected run work progress
            </div>
            <div className="text-sm text-muted">
              memory_context={scope?.memory_context ?? "none"} · inference + judge work only
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
            {batchNotice && <div className="text-[11px] text-warn">{batchNotice}</div>}
            {persistenceText && <div className={`text-[11px] ${persistence?.status === "retrying_push" ? "text-warn" : "text-faint"}`}>{persistenceText}</div>}
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
            hint="A 'unit' is one model answering one scenario once. Inference runs on the ai node; this bar is units done vs. planned (scenarios × repetitions × models)."
          />
          <Row
            icon={<Scale className="h-3.5 w-3.5" />}
            label="Judge (home)"
            done={p?.judge_done ?? 0}
            total={p?.judge_total ?? 0}
            tone="warn"
            live={live}
            hint="Every finished answer is graded by 2 LLM judges on the home node. This bar is judgements done vs. planned (units × 2 judges), so it trails inference."
          />
          {p?.rate_per_min != null && (
            <div className="text-right text-[11px] text-faint">
              {p.rate_per_min} units/min
            </div>
          )}
          {reliability && (
            <div className="grid gap-2 pt-1 sm:grid-cols-5 xl:grid-cols-7">
              <ReliabilityChip label="DNF" value={`${reliability.dnf}/${reliability.rows}`} sub={`${reliability.dnf_rate}%`} tone={reliability.dnf ? "text-warn" : "text-good"} />
              <ReliabilityChip label="Length" value={`${reliability.length}`} sub={`${reliability.length_rate}%`} tone={reliability.length ? "text-warn" : "text-good"} />
              <ReliabilityChip label="Zero stalls" value={`${reliability.zero_output_stalls}`} sub={`${reliability.zero_output_stall_rate}%`} tone={reliability.zero_output_stalls ? "text-bad" : "text-good"} />
              <ReliabilityChip label="Judge empty" value={`${reliability.judge_empty}`} sub={`${reliability.judge_evidence_missing} evidence gaps`} tone={reliability.judge_empty || reliability.judge_evidence_missing ? "text-warn" : "text-good"} />
              <ReliabilityChip label="Frontier input" value={formatTokenCount(sumJudgeTokens(reliability, "tokens_in"))} sub={judgeUsageSub(reliability)} tone="text-muted" />
              <ReliabilityChip label="Frontier output" value={formatTokenCount(sumJudgeTokens(reliability, "tokens_out"))} sub={judgeOutputSub(reliability)} tone="text-muted" />
              <ReliabilityChip label="Cache" value={formatPercent(weightedCachePct(reliability))} sub={judgeCacheSub(reliability)} tone="text-muted" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function sumJudgeTokens(reliability: ReliabilityReport, key: "tokens_in" | "tokens_out" | "cache_read" | "cache_write" | "uncached_input_tokens") {
  return Object.values(reliability.usage_by_judge ?? {}).reduce((sum, usage) => sum + (usage[key] || 0), 0);
}

function judgeUsageSub(reliability: ReliabilityReport) {
  const entries = Object.entries(reliability.usage_by_judge ?? {});
  if (!entries.length) return "usage not recorded yet";
  return entries.map(([judge, usage]) => `${judge}: ${usage.calls} calls`).join(" · ");
}

function judgeOutputSub(reliability: ReliabilityReport) {
  const entries = Object.entries(reliability.usage_by_judge ?? {});
  if (!entries.length) return "usage not recorded yet";
  return entries.map(([judge, usage]) => `${judge}: ${formatTokenCount(usage.tokens_out || 0)}`).join(" · ");
}

function judgeCacheSub(reliability: ReliabilityReport) {
  const cached = sumJudgeTokens(reliability, "cache_read");
  const uncached = sumJudgeTokens(reliability, "uncached_input_tokens");
  if (!cached && !uncached) return "cache not reported yet";
  return `${formatTokenCount(cached)} cached · ${formatTokenCount(uncached)} uncached`;
}

function weightedCachePct(reliability: ReliabilityReport) {
  const input = sumJudgeTokens(reliability, "tokens_in");
  if (!input) return null;
  return (sumJudgeTokens(reliability, "cache_read") / input) * 100;
}

function formatPercent(value: number | null) {
  if (value == null) return "—";
  return `${value.toFixed(value >= 10 ? 1 : 2)}%`;
}

function formatTokenCount(tokens: number) {
  if (!tokens) return "—";
  if (tokens >= 1_000_000) return `${trimOne(tokens / 1_000_000)}M`;
  if (tokens >= 1_000) return `${trimOne(tokens / 1_000)}k`;
  return `${tokens}`;
}

function trimOne(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function ReliabilityChip({ label, value, sub, tone }: { label: string; value: string; sub: string; tone: string }) {
  return (
    <div className="rounded-lg border border-line/60 bg-panel/50 px-2.5 py-2">
      <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-faint">{label}</div>
      <div className={`mt-0.5 font-mono text-sm font-semibold ${tone}`}>{value}</div>
      <div className="mt-0.5 truncate text-[10px] text-muted" title={sub}>{sub}</div>
    </div>
  );
}
