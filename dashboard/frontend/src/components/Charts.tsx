import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Card, Hint } from "./ui";
import type { AnalyticsScope, ParetoPoint, Scores, RunSummary } from "../types";
import { Trophy, BarChart3, Layers, Sparkles, Star, BatteryLow, Zap, Cpu, Clock, ShieldCheck } from "lucide-react";

const ACCENT = "#5b8cff";
const GOOD = "#34d399";
const WARN = "#fbbf24";
const GRID = "rgba(127,127,127,0.18)";
const AXIS = "#94a3b8";

function Tip({ active, payload, label, unit }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-line bg-panel px-3 py-2 text-xs shadow-xl">
      <div className="mb-0.5 font-mono font-semibold text-fg">{label}</div>
      <div className="text-muted">
        {payload[0].value}
        {unit ?? ""}
      </div>
    </div>
  );
}

function scopeTitle(base: string, scope?: AnalyticsScope) {
  const memory = scope?.memory_context ?? "none";
  return `${base} · ${memory}`;
}

function ScopeRight({ scope }: { scope?: AnalyticsScope }) {
  return <span className="font-mono text-[10px] text-faint">selected run · memory_context={scope?.memory_context ?? "none"}</span>;
}

/** Tooltip that also shows the sample size n behind a mean (a mean from few
 * judgments is weaker evidence than one from many). */
function TipN({ active, payload, unit }: any) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload ?? {};
  const name = p.model ?? p.class ?? "";
  return (
    <div className="rounded-lg border border-line bg-panel px-3 py-2 text-xs shadow-xl">
      <div className="mb-0.5 font-mono font-semibold text-fg">{name}</div>
      <div className="text-muted">
        {payload[0].value}
        {unit ?? ""}
        {p.n != null ? <span className="text-faint"> · n={p.n}</span> : null}
      </div>
    </div>
  );
}

/** Top models by mean judge quality. */
export function QualityLeaderboard({ pareto, scope }: { pareto: ParetoPoint[]; scope?: AnalyticsScope }) {
  const data = pareto
    .filter((p) => p.quality != null)
    .sort((a, b) => (b.quality ?? 0) - (a.quality ?? 0))
    .slice(0, 14)
    .map((p) => ({ model: p.model, quality: p.quality, n: p.n }));
  const fullN = Math.max(1, ...data.map((d) => d.n ?? 0));
  return (
    <Card
      title={scopeTitle("Quality leaderboard", scope)}
      icon={<Trophy className="h-4 w-4 text-warn" />}
      hint="Models ranked by their mean judge score (1–5), best first. The score is the average over every answer the model gave, across both LLM judges."
      right={<ScopeRight scope={scope} />}
    >
      {data.length === 0 ? (
        <p className="py-10 text-center text-sm text-faint">No judged models yet…</p>
      ) : (
        <div style={{ height: Math.max(160, data.length * 26) }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
              <CartesianGrid stroke={GRID} horizontal={false} />
              <XAxis type="number" domain={[0, 5]} stroke={AXIS} fontSize={11} tickLine={false} />
              <YAxis
                type="category"
                dataKey="model"
                width={120}
                stroke={AXIS}
                fontSize={10}
                tickLine={false}
                interval={0}
              />
              <Tooltip content={<TipN unit=" / 5" />} cursor={{ fill: "rgba(127,127,127,0.08)" }} />
              <Bar dataKey="quality" radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false}>
                {data.map((d, i) => (
                  <Cell key={i} fill={ACCENT} fillOpacity={d.n != null && d.n < fullN ? 0.4 : 1} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}

/** Distribution of judge scores (1–5). */
export function ScoreDistribution({ scores, scope }: { scores?: Scores; scope?: AnalyticsScope }) {
  const data = (scores?.hist ?? []).map((b) => ({ score: b.score.toFixed(1), count: b.count }));
  return (
    <Card
      title={scopeTitle("Judge score distribution", scope)}
      icon={<BarChart3 className="h-4 w-4 text-good" />}
      hint="How many individual answers received each score from 1 (useless or unsafe) to 5 (excellent). A left-heavy shape means the small models mostly failed; right-heavy means they did well. Counted across every model and judge in this run."
      right={<ScopeRight scope={scope} />}
    >
      {data.length === 0 ? (
        <p className="py-10 text-center text-sm text-faint">No judgments yet…</p>
      ) : (
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ left: -8, right: 8, top: 8 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="score" stroke={AXIS} fontSize={11} tickLine={false} />
              <YAxis stroke={AXIS} fontSize={11} tickLine={false} allowDecimals={false} />
              <Tooltip content={<Tip unit=" answers" />} cursor={{ fill: "rgba(127,127,127,0.08)" }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={48} isAnimationActive={false}>
                {data.map((d, i) => (
                  <Cell key={i} fill={Number(d.score) >= 3 ? GOOD : Number(d.score) >= 2 ? WARN : "#f87171"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}

/** Mean quality by scenario class (where the models do well / struggle). */
export function ClassQuality({ scores, scope }: { scores?: Scores; scope?: AnalyticsScope }) {
  const data = (scores?.by_class ?? []).map((c) => ({ class: c.class, quality: c.quality, n: c.n }));
  const fullN = Math.max(1, ...data.map((d) => d.n ?? 0));
  return (
    <Card
      title={scopeTitle("Quality by scenario class", scope)}
      icon={<Layers className="h-4 w-4 text-accent" />}
      hint="Mean judge score (1–5) grouped by the kind of ops task — e.g. monitor, upgrade, detect, guard. Shows which categories the models handle well and where they struggle."
      right={<ScopeRight scope={scope} />}
    >
      {data.length === 0 ? (
        <p className="py-10 text-center text-sm text-faint">No judgments yet…</p>
      ) : (
        <div style={{ height: Math.max(160, data.length * 24) }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
              <CartesianGrid stroke={GRID} horizontal={false} />
              <XAxis type="number" domain={[0, 5]} stroke={AXIS} fontSize={11} tickLine={false} />
              <YAxis
                type="category"
                dataKey="class"
                width={96}
                stroke={AXIS}
                fontSize={10}
                tickLine={false}
                interval={0}
              />
              <Tooltip content={<TipN unit=" / 5" />} cursor={{ fill: "rgba(127,127,127,0.08)" }} />
              <Bar dataKey="quality" radius={[0, 4, 4, 0]} maxBarSize={16} isAnimationActive={false}>
                {data.map((d, i) => (
                  <Cell
                    key={i}
                    fill={(d.quality ?? 0) >= 2.5 ? GOOD : (d.quality ?? 0) >= 1.8 ? WARN : "#f87171"}
                    fillOpacity={d.n != null && d.n < fullN ? 0.4 : 1}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}

/** Models on the quality-vs-energy efficiency frontier: a model is Pareto-optimal
 * if no other model has both >= quality AND <= Wh/answer. */
function paretoFront(pts: ParetoPoint[]): Set<string> {
  const v = pts.filter((p) => p.quality != null && p.wh != null);
  const front = new Set<string>();
  for (const m of v) {
    const dominated = v.some(
      (n) =>
        n !== m &&
        (n.quality ?? 0) >= (m.quality ?? 0) &&
        (n.wh ?? Infinity) <= (m.wh ?? Infinity) &&
        ((n.quality ?? 0) > (m.quality ?? 0) || (n.wh ?? Infinity) < (m.wh ?? Infinity)),
    );
    if (!dominated) front.add(m.model);
  }
  return front;
}

export function ParetoLeaderboard({ pareto, scope }: { pareto: ParetoPoint[]; scope?: AnalyticsScope }) {
  const rows = pareto
    .filter((p) => p.quality != null)
    .sort((a, b) => (b.quality ?? 0) - (a.quality ?? 0) || (b.tok_s ?? 0) - (a.tok_s ?? 0));
  const front = paretoFront(pareto);
  const fullN = Math.max(1, ...rows.map((p) => p.n ?? 0));
  return (
    <Card
      title={scopeTitle("Pareto leaderboard", scope)}
      icon={<Sparkles className="h-4 w-4 text-accent" />}
      hint="Models ranked by quality. A starred row sits on the quality-vs-energy frontier: no other model is both higher quality and lower energy, so it is an efficient pick."
      right={
        <span className="text-xs text-faint">
          <span className="mr-2 font-mono text-[10px]">memory_context={scope?.memory_context ?? "none"}</span>
          {front.size} on frontier <Star className="-mt-0.5 inline h-3 w-3 fill-warn text-warn" />
        </span>
      }
    >
      {rows.length === 0 ? (
        <p className="py-10 text-center text-sm text-faint">No judged + telemetry data yet…</p>
      ) : (
        <div className="max-h-[26rem] overflow-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="sticky top-0 bg-panel text-left text-[11px] uppercase tracking-wider text-faint">
                <th className="px-2 py-2 font-medium">#</th>
                <th className="px-2 py-2 font-medium">Model</th>
                <th className="px-2 py-2 text-right font-medium">Quality</th>
                <th className="px-2 py-2 text-right font-medium">n</th>
                <th className="px-2 py-2 text-right font-medium">tok/s</th>
                <th className="px-2 py-2 text-right font-medium">Wh/ans</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((p, i) => {
                const onFront = front.has(p.model);
                return (
                  <tr
                    key={p.model}
                    className={`border-t border-line/70 ${onFront ? "bg-warn/[0.06]" : ""}`}
                  >
                    <td className="px-2 py-2 font-mono text-xs text-faint">{i + 1}</td>
                    <td className="px-2 py-2">
                      <span className="flex items-center gap-1.5 font-mono text-xs text-fg">
                        {onFront && <Star className="h-3 w-3 shrink-0 fill-warn text-warn" />}
                        {p.model}
                      </span>
                    </td>
                    <td className="px-2 py-2 text-right font-mono tabular-nums text-fg">{p.quality}</td>
                    <td className={`px-2 py-2 text-right font-mono tabular-nums ${p.n < fullN ? "text-warn" : "text-faint"}`}>{p.n}</td>
                    <td className="px-2 py-2 text-right font-mono tabular-nums text-muted">
                      {p.tok_s ?? "—"}
                    </td>
                    <td className="px-2 py-2 text-right font-mono tabular-nums text-muted">
                      {p.wh ?? "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

/** Power leaderboard — ranked by energy ascending (LOWER power = better, i.e. the
 * inverse of power). Shows Wh/answer, mean watts, and quality for context. */
export function PowerLeaderboard({ pareto, scope }: { pareto: ParetoPoint[]; scope?: AnalyticsScope }) {
  const rows = pareto
    .filter((p) => p.wh != null)
    .sort((a, b) => (a.wh ?? Infinity) - (b.wh ?? Infinity)); // lower energy first
  return (
    <Card
      title={scopeTitle("Power leaderboard", scope)}
      icon={<BatteryLow className="h-4 w-4 text-good" />}
      hint="Models ranked by energy per answer, lowest first — the inverse of power, so spending less energy for the same work wins. Quality is shown only for context; it is never multiplied into the ranking."
      right={<ScopeRight scope={scope} />}
    >
      {rows.length === 0 ? (
        <p className="py-10 text-center text-sm text-faint">No telemetry yet…</p>
      ) : (
        <div className="max-h-[26rem] overflow-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="sticky top-0 bg-panel text-left text-[11px] uppercase tracking-wider text-faint">
                <th className="px-2 py-2 font-medium">#</th>
                <th className="px-2 py-2 font-medium">Model</th>
                <th className="px-2 py-2 text-right font-medium">Wh/ans</th>
                <th className="px-2 py-2 text-right font-medium">Watts</th>
                <th className="px-2 py-2 text-right font-medium">Quality</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((p, i) => (
                <tr key={p.model} className="border-t border-line/70">
                  <td className="px-2 py-2 font-mono text-xs text-faint">{i + 1}</td>
                  <td className="px-2 py-2 font-mono text-xs text-fg">{p.model}</td>
                  <td className="px-2 py-2 text-right font-mono tabular-nums text-good">{p.wh ?? "—"}</td>
                  <td className="px-2 py-2 text-right font-mono tabular-nums text-muted">{p.watts ?? "—"}</td>
                  <td className="px-2 py-2 text-right font-mono tabular-nums text-muted">{p.quality ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function Metric({ icon, label, value, sub, hint }: { icon: React.ReactNode; label: string; value: React.ReactNode; sub?: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-line bg-panel2/40 p-3">
      <div className="label flex items-center gap-1.5">
        {icon}
        {label}
        {hint && <Hint text={hint} align="end" className="ml-auto" />}
      </div>
      <div className="mt-1 font-mono text-xl font-semibold text-fg tabular-nums">{value}</div>
      {sub && <div className="text-[10px] text-faint">{sub}</div>}
    </div>
  );
}

/** Roll-up stats for the selected run: energy, power, compute, quality, security. */
export function RunSummaryCard({ summary, scope }: { summary?: RunSummary; scope?: AnalyticsScope }) {
  const s = summary;
  return (
    <div className="space-y-2">
      <div className="px-1 font-mono text-[10px] text-faint">Summary scope: selected run · memory_context={scope?.memory_context ?? "none"}</div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      <Metric icon={<Zap className="h-3.5 w-3.5" />} label="Energy" value={s?.energy_wh != null ? `${s.energy_wh} Wh` : "—"} sub="total this run" hint="Total electricity this run has drawn, in watt-hours — summed across every model's inference, measured from the CPU's Intel RAPL energy counter. Lower is better." />
      <Metric icon={<BatteryLow className="h-3.5 w-3.5" />} label="Power" value={s?.mean_watts != null ? `${s.mean_watts} W` : "—"} sub="mean draw" hint="Average power draw in watts while the CPU was inferring — the mean of the per-model RAPL package readings." />
      <Metric icon={<Clock className="h-3.5 w-3.5" />} label="Compute" value={s?.cpu_minutes != null ? `${s.cpu_minutes}m` : "—"} sub="CPU-minutes" hint="Total processor time spent this run, in CPU-minutes — the sum of every model's wall-clock inference time." />
      <Metric icon={<Cpu className="h-3.5 w-3.5" />} label="Quality" value={s?.quality_overall ?? "—"} sub={s?.n != null ? `mean judge / 5 · n=${s.n}` : "mean judge / 5"} hint="Mean judge score (1–5) across every answer in this run, averaged over both LLM judges. Higher is better." />
      <Metric icon={<ShieldCheck className="h-3.5 w-3.5" />} label="Security" value={s?.security_overall ?? "—"} sub={s?.n_security != null ? `safety scenarios / 5 · n=${s.n_security}` : "safety scenarios / 5"} hint="Mean judge score (1–5) on the safety scenarios only — the 'secure' and 'guard' classes that test whether a model refuses or safely handles risky operations." />
      </div>
    </div>
  );
}
