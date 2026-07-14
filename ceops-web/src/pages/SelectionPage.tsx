import { PreviewDataNotice } from "../components/PreviewDataNotice";
import { Shell } from "../components/Shell";
import { EvidenceReleaseStrip } from "../components/EvidenceReleaseStrip";
import { ParetoChart } from "../components/ParetoChart";
import { RecommendationRule } from "../components/RecommendationRule";
import { ResultTable } from "../components/ResultTable";
import {
  PREVIEW_POINTS,
  PREVIEW_RECOMMENDATION,
  PREVIEW_RELEASE,
  PREVIEW_VERIFY_CMD,
} from "../lib/sampleData";

const FILTERS: { label: string; options: string[] }[] = [
  {
    label: "Cost ceiling",
    options: ["≤ 4 Wh · ≤ 1000 ms", "≤ 8 Wh · ≤ 2000 ms", "No ceiling"],
  },
  { label: "Quality floor", options: ["≥ 55", "≥ 65", "≥ 75"] },
  { label: "Refusal", options: ["Comparable only", "Include qualified"] },
  {
    label: "Evidence",
    options: ["Verified only", "Include qualified", "Show withdrawn"],
  },
  { label: "Preference sensitivity", options: ["Off", "Show reruns"] },
];

const slug = (s: string) => "f-" + s.toLowerCase().replace(/[^a-z0-9]+/g, "-");

/** Public Selection — the release-scoped controlled evidence explorer (§6.1). */
export function SelectionPage() {
  const recPoint = PREVIEW_POINTS.find(
    (p) => p.id === PREVIEW_RECOMMENDATION.pointId,
  )!;
  return (
    <>
      <PreviewDataNotice />
      <Shell current="Evidence">
        <EvidenceReleaseStrip release={PREVIEW_RELEASE} />
        <main className="page">
          <section className="hero">
            <p className="eyebrow">
              Evidence · release apprenticeops-2026.07 · Selection
            </p>
            <h1 className="pagetitle">Selection</h1>
            <p className="lede">
              Explore the controlled operating points for this release. Adjust
              the preference constraints; the front, the recommendation and the
              table stay bound to the same release-scoped evidence.
            </p>

            <div
              className="filters"
              role="group"
              aria-label="Comparison constraints (preview, non-interactive)"
            >
              {FILTERS.map((f) => (
                <div className="filter" key={f.label}>
                  <label htmlFor={slug(f.label)}>{f.label}</label>
                  <select id={slug(f.label)} defaultValue={f.options[0]}>
                    {f.options.map((o) => (
                      <option key={o}>{o}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <div className="explorer">
              <div className="chartcard">
                <div className="chartcard__head">
                  <span className="chartcard__title">Controlled Pareto front</span>
                  <span className="chartcard__axes">
                    Ops quality × latency × energy
                  </span>
                </div>
                <ParetoChart points={PREVIEW_POINTS} />
              </div>
              <RecommendationRule
                rec={PREVIEW_RECOMMENDATION}
                point={recPoint}
              />
            </div>

            <ResultTable
              points={PREVIEW_POINTS}
              release={PREVIEW_RELEASE}
              verifyCmd={PREVIEW_VERIFY_CMD}
            />
          </section>
        </main>
      </Shell>
    </>
  );
}
