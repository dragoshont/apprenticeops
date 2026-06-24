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

// Security (mean judge score on the safety scenarios, 1–5) → colour.
// Best practice for a 3rd objective on a 2D chart is COLOUR, not bubble area.
function secColor(sec: number | null): string {
  if (sec == null) return "#64748b"; // unknown
  if (sec >= 3) return "#34d399"; // green — safe
  if (sec >= 2) return "#fbbf24"; // amber
  return "#f87171"; // red — weak guardrails
}

/** A model is Pareto-optimal (quality↑ vs energy↓) if none dominates it. */
function frontier(pts: ParetoPoint[]): Set<string> {
  const v = pts.filter((p) => p.quality != null && p.wh != null);
  const f = new Set<string>();
  for (const m of v) {
    const dom = v.some(
      (n) =>
        n !== m &&
        (n.quality ?? 0) >= (m.quality ?? 0) &&
        (n.wh ?? Infinity) <= (m.wh ?? Infinity) &&
        ((n.quality ?? 0) > (m.quality ?? 0) || (n.wh ?? Infinity) < (m.wh ?? Infinity)),
    );
    if (!dom) f.add(m.model);
  }
  return f;
}

function Dot(props: { cx?: number; cy?: number; payload?: ParetoPoint & { _front?: boolean } }) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload) return null;
  const c = secColor(payload.security);
  const onFront = payload._front;
  return (
    <g>
      {onFront && <circle cx={cx} cy={cy} r={9} fill="none" stroke={c} strokeOpacity={0.5} strokeWidth={1.5} />}
      <circle cx={cx} cy={cy} r={6} fill={c} fillOpacity={0.9} stroke="#0b1020" strokeWidth={1} />
    </g>
  );
}

function TipBox({ active, payload }: { active?: boolean; payload?: Array<{ payload: ParetoPoint }> }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-line bg-panel px-3 py-2 text-xs shadow-xl">
      <div className="mb-1 font-mono font-semibold text-fg">{p.model}</div>
      <div className="text-muted">quality {p.quality ?? "—"} · security {p.security ?? "—"}</div>
      <div className="text-muted">
        {p.wh != null ? `${p.wh} Wh/ans` : "energy —"} · {p.tok_s ?? "—"} tok/s · n={p.n}
      </div>
    </div>
  );
}

export function ParetoChart({ data }: { data: ParetoPoint[] }) {
  const front = frontier(data);
  const pts = data
    .filter((d) => d.quality != null && d.wh != null)
    .map((d) => ({ ...d, _front: front.has(d.model) }));
  return (
    <Card
      title="Pareto · quality vs energy vs security"
      icon={<Sparkles className="h-4 w-4 text-accent" />}
      hint="A trade-off map. Each dot is a model placed by energy per answer (x — left is cheaper) and quality (y — higher is better); its colour is the security score (green safe → red weak). Ringed dots are Pareto-optimal — nothing else is both better and cheaper. The top-left corner is the sweet spot."
      right={
        <div className="flex items-center gap-2 text-[10px] text-faint">
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full" style={{ background: "#34d399" }} /> safe
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full" style={{ background: "#fbbf24" }} /> mid
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full" style={{ background: "#f87171" }} /> weak
          </span>
        </div>
      }
    >
      {pts.length === 0 ? (
        <p className="py-12 text-center text-sm text-faint">Awaiting judged + telemetry data…</p>
      ) : (
        <>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 16, bottom: 28, left: 4 }}>
                <CartesianGrid stroke="rgba(127,127,127,0.18)" strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  dataKey="wh"
                  name="energy"
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  label={{ value: "Wh / answer  (← lower = better)", position: "bottom", offset: 8, fill: "#94a3b8", fontSize: 11 }}
                />
                <YAxis
                  type="number"
                  dataKey="quality"
                  name="quality"
                  domain={[0, 5]}
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  label={{ value: "quality ↑", angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 11 }}
                />
                <ZAxis type="number" range={[60, 60]} />
                <Tooltip content={<TipBox />} cursor={{ stroke: "#475569", strokeDasharray: "3 3" }} />
                <Scatter data={pts} shape={<Dot />} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-1 text-center text-[10px] text-faint">
            colour = security · ringed = on the quality/energy frontier · top-left is best
          </p>
        </>
      )}
    </Card>
  );
}
