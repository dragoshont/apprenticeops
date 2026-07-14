import { Fragment } from "react";
import type { DeploymentPoint } from "../lib/types";

// Plot geometry (viewBox units; the SVG scales to its column width).
const W = 760;
const H = 470;
const M = { top: 22, right: 104, bottom: 56, left: 60 };
const PW = W - M.left - M.right;
const PH = H - M.top - M.bottom;

const X_MAX = 2500; // latency p50, ms
const Y_MIN = 35;
const Y_MAX = 85; // ops quality

const xToPx = (ms: number) => M.left + (ms / X_MAX) * PW;
const yToPx = (q: number) => M.top + (1 - (q - Y_MIN) / (Y_MAX - Y_MIN)) * PH;
// Bubble AREA encodes energy: radius scales with the square root of Wh.
const rEnergy = (wh: number) => 4 + Math.sqrt(wh) * 3.2;

const X_TICKS = [0, 500, 1000, 1500, 2000, 2500];
const Y_TICKS = [35, 45, 55, 65, 75, 85];

function strokeFor(p: DeploymentPoint) {
  // Front points carry their evidence state color. Dominated points are neutral,
  // except withdrawn/integrity-failed, whose red is reserved and never hidden.
  if (!p.onFront && p.state !== "withdrawn") return "var(--chart-dominated)";
  switch (p.state) {
    case "verified":
      return "var(--state-verified-line)";
    case "qualified":
      return "var(--state-qualified-line)";
    case "withdrawn":
      return "var(--state-withdrawn-line)";
    default:
      return "var(--state-unavailable-line)";
  }
}
function fillFor(p: DeploymentPoint) {
  if (!p.onFront && p.state !== "withdrawn") return "var(--chart-dominated-fill)";
  return p.state === "verified" ? "var(--chart-front-fill)" : "transparent";
}
function ariaFor(p: DeploymentPoint) {
  const energy =
    p.energyWh === null ? "energy unavailable" : `${p.energyWh} watt-hours per task`;
  return `${p.model}, ${p.condition}. Ops quality ${p.quality}, interval ${p.qualityLow} to ${p.qualityHigh}. Latency ${p.latencyMs} milliseconds. ${energy}. ${p.onFront ? "On the controlled front" : "Dominated"}. Evidence ${p.state}.`;
}

/** Accessible controlled-Pareto scatter. Every point is keyboard-focusable and
 *  the complete ResultTable below is the textual equivalent. */
export function ParetoChart({ points }: { points: DeploymentPoint[] }) {
  const front = points
    .filter((p) => p.onFront)
    .sort((a, b) => a.latencyMs - b.latencyMs);

  const modelCounts = new Map<string, number>();
  front.forEach((p) => modelCounts.set(p.model, (modelCounts.get(p.model) ?? 0) + 1));
  const shortLabel = (p: DeploymentPoint) =>
    (modelCounts.get(p.model) ?? 0) > 1
      ? `${p.model} · ${p.condition.split(" · ")[0]}`
      : p.model;

  const frontPath = front
    .map((p) => `${xToPx(p.latencyMs)},${yToPx(p.quality)}`)
    .join(" ");

  return (
    <div>
      <svg
        className="pareto"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Controlled Pareto front: ops quality versus latency p50, with bubble area encoding energy per task. A complete data table follows this chart."
      >
        {Y_TICKS.map((t) => (
          <Fragment key={`y${t}`}>
            <line className="grid-line" x1={M.left} y1={yToPx(t)} x2={M.left + PW} y2={yToPx(t)} />
            <text className="tick" x={M.left - 8} y={yToPx(t) + 4} textAnchor="end">
              {t}
            </text>
          </Fragment>
        ))}
        {X_TICKS.map((t) => (
          <text className="tick" key={`x${t}`} x={xToPx(t)} y={M.top + PH + 20} textAnchor="middle">
            {t}
          </text>
        ))}

        <line className="axis-line" x1={M.left} y1={M.top + PH} x2={M.left + PW} y2={M.top + PH} />
        <line className="axis-line" x1={M.left} y1={M.top} x2={M.left} y2={M.top + PH} />
        <text className="axis-label" x={M.left + PW / 2} y={H - 12} textAnchor="middle">
          Latency p50 (ms) — lower is cheaper
        </text>
        <text
          className="axis-label"
          transform={`translate(16 ${M.top + PH / 2}) rotate(-90)`}
          textAnchor="middle"
        >
          Ops quality (0–100)
        </text>

        <polyline className="front-line" points={frontPath} />

        {points.map((p) => {
          const cx = xToPx(p.latencyMs);
          const cy = yToPx(p.quality);
          const stroke = strokeFor(p);
          const r = p.energyWh === null ? 9 : rEnergy(p.energyWh);
          const labelRight = cx < M.left + PW * 0.66;
          return (
            <g
              className="pt-group"
              key={p.id}
              tabIndex={0}
              role="img"
              aria-label={ariaFor(p)}
            >
              {p.onFront && (
                <line
                  className="err-bar"
                  x1={cx}
                  y1={yToPx(p.qualityHigh)}
                  x2={cx}
                  y2={yToPx(p.qualityLow)}
                  style={{ stroke }}
                />
              )}
              {p.energyWh === null ? (
                <rect
                  x={cx - 6}
                  y={cy - 6}
                  width={12}
                  height={12}
                  style={{ fill: "transparent", stroke }}
                  strokeWidth={1.75}
                />
              ) : (
                <circle
                  cx={cx}
                  cy={cy}
                  r={r}
                  style={{ fill: fillFor(p), stroke }}
                  strokeWidth={p.onFront ? 2 : 1.5}
                />
              )}
              {p.onFront && (
                <text
                  className="pt-label"
                  x={labelRight ? cx + r + 6 : cx - r - 6}
                  y={cy - 8}
                  textAnchor={labelRight ? "start" : "end"}
                >
                  {shortLabel(p)}
                </text>
              )}
              <circle className="pt-focus-ring" cx={cx} cy={cy} r={r + 5} />
            </g>
          );
        })}
      </svg>

      <div className="chartlegend">
        <span className="legend-item">
          <span className="legend-swatch" /> On controlled front (labelled, quality interval)
        </span>
        <span className="legend-item">
          <span className="legend-swatch dominated" /> Dominated
        </span>
        <span className="legend-item sizekey" aria-hidden>
          <SizeKey />
        </span>
        <span className="legend-item">Bubble area = energy per task (Wh)</span>
      </div>
    </div>
  );
}

function SizeKey() {
  const vals = [1, 5, 10];
  const maxR = 4 + Math.sqrt(10) * 3.2;
  const h = maxR * 2 + 18;
  let x = 0;
  return (
    <svg width={150} height={h} viewBox={`0 0 150 ${h}`}>
      {vals.map((v) => {
        const r = 4 + Math.sqrt(v) * 3.2;
        const cx = (x += maxR + 10);
        const cy = maxR + 2;
        return (
          <g key={v}>
            <circle
              cx={cx}
              cy={cy}
              r={r}
              style={{ fill: "var(--chart-front-fill)", stroke: "var(--chart-front)" }}
              strokeWidth={1.5}
            />
            <text
              x={cx}
              y={h - 2}
              textAnchor="middle"
              style={{ fontSize: 10, fill: "var(--color-text-faint)" }}
            >
              {v} Wh
            </text>
          </g>
        );
      })}
    </svg>
  );
}
