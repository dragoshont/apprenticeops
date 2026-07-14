import type { DeploymentPoint, Recommendation } from "../lib/types";

function fmt(n: number | null, unit: string) {
  return n === null ? "n/a" : `${n}${unit}`;
}

/** Recommendation column. Rendered in strong neutral, never verified teal: a
 *  preference-dependent operating point is not universal truth. */
export function RecommendationRule({
  rec,
  point,
}: {
  rec: Recommendation;
  point: DeploymentPoint;
}) {
  return (
    <aside className="reccard" aria-label="Current recommendation">
      <p className="reccard__eyebrow">Recommendation · preference-dependent</p>
      <p className="reccard__name">{point.model}</p>
      <p className="reccard__sub">{point.condition}</p>

      <p className="reccard__rulelabel">Preference rule</p>
      <p className="reccard__rule">{rec.rule}</p>
      <ul className="reccard__constraints">
        {rec.constraints.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>

      <dl className="reccard__stats">
        <dt>Ops quality</dt>
        <dd>
          {point.quality}
          <span className="ci"> ({point.qualityLow}–{point.qualityHigh})</span>
        </dd>
        <dt>Energy / task</dt>
        <dd>{fmt(point.energyWh, " Wh")}</dd>
        <dt>Latency p50</dt>
        <dd>{fmt(point.latencyMs, " ms")}</dd>
        <dt>Appropriate refusal</dt>
        <dd>{fmt(point.refusalPct, "%")}</dd>
      </dl>
    </aside>
  );
}
