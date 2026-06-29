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
            <div className="space-y-2 pt-1">
              <div className="rounded-lg border border-line/60 bg-panel/50 px-3 py-2 text-[11px] leading-relaxed text-muted">
                Reliability checks are about answer rows. Here, <span className="font-mono text-fg">60</span> means 2 models x 6 scenarios x 5 repeats. A value like <span className="font-mono text-fg">22/60</span> means 22 of those 60 answers failed that check.
              </div>
              <div className="grid gap-2 sm:grid-cols-5 xl:grid-cols-7">
                <ReliabilityChip
                  label="DNF"
                  value={`${reliability.dnf}/${reliability.rows}`}
                  sub={`${reliability.dnf_rate}% failed answers`}
                  tone={reliability.dnf ? "text-warn" : "text-good"}
                  help="Did Not Finish. The model call did not produce a usable final answer before the harness gave up. Example: 22/60 means 22 answer attempts failed out of 60 total answer attempts."
                />
                <ReliabilityChip
                  label="Length"
                  value={`${reliability.length}`}
                  sub={`${reliability.length_rate}% hit token cap`}
                  tone={reliability.length ? "text-warn" : "text-good"}
                  help="Answers that stopped because they reached the maximum token limit. These are not empty, but may be cut off before completing the task."
                />
                <ReliabilityChip
                  label="Zero stalls"
                  value={`${reliability.zero_output_stalls}`}
                  sub={`${reliability.zero_output_stall_rate}% no text returned`}
                  tone={reliability.zero_output_stalls ? "text-bad" : "text-good"}
                  help="The worst DNF subtype: Ollama accepted the request path but the model returned no answer text before the stall timeout. In plain terms: nothing useful came back."
                />
                <ReliabilityChip
                  label="Judge empty"
                  value={`${reliability.judge_empty}`}
                  sub={`${reliability.judge_evidence_missing} evidence gaps`}
                  tone={reliability.judge_empty || reliability.judge_evidence_missing ? "text-warn" : "text-good"}
                  help="Judge calls that could not score a meaningful answer. This often follows DNF/zero-stall rows because there is no model answer for the judge to evaluate."
                />
                <ReliabilityChip
                  label="Frontier input"
                  value={formatTokenCount(sumJudgeTokens(reliability, "tokens_in"))}
                  sub={judgeUsageSub(reliability)}
                  tone="text-muted"
                  help="Input tokens sent to the frontier judge models. If this is blank, the Copilot CLI did not report token usage for this run, even though judge calls completed."
                />
                <ReliabilityChip
                  label="Frontier output"
                  value={formatTokenCount(sumJudgeTokens(reliability, "tokens_out"))}
                  sub={judgeOutputSub(reliability)}
                  tone="text-muted"
                  help="Output tokens returned by the frontier judge models. Blank means usage accounting was not reported by the judge backend."
                />
                <ReliabilityChip
                  label="Cache"
                  value={formatPercent(weightedCachePct(reliability))}
                  sub={judgeCacheSub(reliability)}
                  tone="text-muted"
                  help="How much judge input was served from cache. Blank means cache accounting was not reported by the judge backend."
                />
              </div>
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

function ReliabilityChip({ label, value, sub, tone, help }: { label: string; value: string; sub: string; tone: string; help: string }) {
  return (
    <div className="rounded-lg border border-line/60 bg-panel/50 px-2.5 py-2">
      <div className="flex items-center gap-1 text-[10px] font-medium uppercase tracking-[0.12em] text-faint">
        {label}
        <Hint text={help} align="start" />
      </div>
      <div className={`mt-0.5 font-mono text-sm font-semibold ${tone}`}>{value}</div>
      <div className="mt-0.5 truncate text-[10px] text-muted" title={sub}>{sub}</div>
    </div>
  );
}
