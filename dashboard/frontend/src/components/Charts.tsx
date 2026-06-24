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
import { Card } from "./ui";
import type { ParetoPoint, Scores } from "../types";
import { Trophy, BarChart3, Layers } from "lucide-react";

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

/** Top models by mean judge quality. */
export function QualityLeaderboard({ pareto }: { pareto: ParetoPoint[] }) {
  const data = pareto
    .filter((p) => p.quality != null)
    .sort((a, b) => (b.quality ?? 0) - (a.quality ?? 0))
    .slice(0, 14)
    .map((p) => ({ model: p.model, quality: p.quality }));
  return (
    <Card title="Quality leaderboard" icon={<Trophy className="h-4 w-4 text-warn" />}>
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
              <Tooltip content={<Tip unit=" / 5" />} cursor={{ fill: "rgba(127,127,127,0.08)" }} />
              <Bar dataKey="quality" radius={[0, 4, 4, 0]} maxBarSize={18}>
                {data.map((_, i) => (
                  <Cell key={i} fill={ACCENT} />
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
export function ScoreDistribution({ scores }: { scores?: Scores }) {
  const data = (scores?.hist ?? []).map((b) => ({ score: b.score.toFixed(1), count: b.count }));
  return (
    <Card title="Judge score distribution" icon={<BarChart3 className="h-4 w-4 text-good" />}>
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
              <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={48}>
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
export function ClassQuality({ scores }: { scores?: Scores }) {
  const data = (scores?.by_class ?? []).map((c) => ({ class: c.class, quality: c.quality }));
  return (
    <Card title="Quality by scenario class" icon={<Layers className="h-4 w-4 text-accent" />}>
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
              <Tooltip content={<Tip unit=" / 5" />} cursor={{ fill: "rgba(127,127,127,0.08)" }} />
              <Bar dataKey="quality" radius={[0, 4, 4, 0]} maxBarSize={16}>
                {data.map((d, i) => (
                  <Cell key={i} fill={(d.quality ?? 0) >= 2.5 ? GOOD : (d.quality ?? 0) >= 1.8 ? WARN : "#f87171"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}
