import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card } from "./ui";
import type { ParetoPoint } from "../types";
import { Sparkles } from "lucide-react";

function Dot(props: { cx?: number; cy?: number; payload?: ParetoPoint }) {
  const { cx, cy } = props;
  if (cx == null || cy == null) return null;
  return (
    <g>
      <circle cx={cx} cy={cy} r={6} fill="#5b8cff" fillOpacity={0.85} stroke="#a9c0ff" strokeWidth={1} />
    </g>
  );
}

function TipBox({ active, payload }: { active?: boolean; payload?: Array<{ payload: ParetoPoint }> }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-line bg-panel px-3 py-2 text-xs shadow-xl">
      <div className="mb-1 font-mono font-semibold text-fg">{p.model}</div>
      <div className="text-muted">quality {p.quality ?? "—"} · {p.tok_s ?? "—"} tok/s</div>
      <div className="text-muted">{p.wh != null ? `${p.wh} Wh/ans` : "energy —"} · n={p.n}</div>
    </div>
  );
}

export function ParetoChart({ data }: { data: ParetoPoint[] }) {
  const pts = data.filter((d) => d.quality != null && d.wh != null);
  return (
    <Card
      title="Pareto · quality vs energy"
      icon={<Sparkles className="h-4 w-4 text-accent" />}
      right={<span className="text-xs text-slate-500">{pts.length} scored</span>}
    >
      {pts.length === 0 ? (
        <p className="py-12 text-center text-sm text-faint">
          Awaiting judged + telemetry data…
        </p>
      ) : (
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 16, bottom: 28, left: 4 }}>
              <CartesianGrid stroke="#1d2740" strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="wh"
                name="energy"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                label={{ value: "Wh / answer  (lower better →)", position: "bottom", offset: 8, fill: "#64748b", fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="quality"
                name="quality"
                domain={[0, 5]}
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                label={{ value: "quality", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 11 }}
              />
              <ZAxis type="number" dataKey="tok_s" range={[40, 40]} />
              <Tooltip content={<TipBox />} cursor={{ stroke: "#334155", strokeDasharray: "3 3" }} />
              <Scatter data={pts} shape={<Dot />} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}
