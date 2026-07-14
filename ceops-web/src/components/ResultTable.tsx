import { ArrowDownUp } from "lucide-react";
import type { DeploymentPoint, ReleaseMeta } from "../lib/types";
import { StateBadge } from "./StateBadge";

function num(n: number | null, digits = 0) {
  return n === null ? <span className="na">n/a</span> : n.toFixed(digits);
}

/** The complete textual equivalent of the Pareto chart. Units live in the
 *  headers; measurements are decimal-aligned tabular numerals; missing values
 *  render as "n/a", never as zero. */
export function ResultTable({
  points,
  release,
  verifyCmd,
}: {
  points: DeploymentPoint[];
  release: ReleaseMeta;
  verifyCmd: string;
}) {
  return (
    <div className="tablewrap">
      <table className="resulttable">
        <caption className="u-vh">
          Controlled results for {release.tag}. Illustrative preview data.
        </caption>
        <thead>
          <tr>
            <th scope="col">
              <span className="sortcue">
                Package <ArrowDownUp size={12} aria-hidden />
              </span>
            </th>
            <th scope="col" className="num">
              Ops quality <span className="unit">0–100</span>
            </th>
            <th scope="col" className="num">
              Energy <span className="unit">Wh</span>
            </th>
            <th scope="col" className="num">
              Latency p50 <span className="unit">ms</span>
            </th>
            <th scope="col" className="num">
              Refusal <span className="unit">%</span>
            </th>
            <th scope="col" className="num">
              Reliability <span className="unit">%</span>
            </th>
            <th scope="col">Evidence</th>
          </tr>
        </thead>
        <tbody>
          {points.map((p) => (
            <tr key={p.id} className={p.onFront ? "is-front" : undefined}>
              <th scope="row" className="pkgcell">
                <span className="pkg">
                  <b>{p.model}</b>
                  <small>{p.condition}</small>
                </span>
              </th>
              <td className="num">
                {p.quality}
                <span className="ci"> ({p.qualityLow}–{p.qualityHigh})</span>
              </td>
              <td className="num">{num(p.energyWh, 1)}</td>
              <td className="num">{num(p.latencyMs, 0)}</td>
              <td className="num">{num(p.refusalPct, 0)}</td>
              <td className="num">{num(p.reliabilityPct, 0)}</td>
              <td>
                <StateBadge state={p.state} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="tablefoot">
        {release.controlledScope} · {release.breadthScope} · verify with{" "}
        <code>{verifyCmd}</code>
      </div>
    </div>
  );
}
