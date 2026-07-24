import { Info } from "lucide-react";
import { PreviewDataNotice } from "../components/PreviewDataNotice";
import { Shell } from "../components/Shell";
import { EvidenceReleaseStrip } from "../components/EvidenceReleaseStrip";
import { ParetoChart } from "../components/ParetoChart";
import { RecommendationRule } from "../components/RecommendationRule";
import { PrimaryActions } from "../components/PrimaryActions";
import {
  PREVIEW_POINTS,
  PREVIEW_RECOMMENDATION,
  PREVIEW_RELEASE,
} from "../lib/sampleData";

/** Public Overview — the first-viewport decision contract (brief §6.1, §7). */
export function OverviewPage() {
  const recPoint = PREVIEW_POINTS.find(
    (p) => p.id === PREVIEW_RECOMMENDATION.pointId,
  )!;
  return (
    <>
      <PreviewDataNotice />
      <Shell current="Overview">
        <EvidenceReleaseStrip release={PREVIEW_RELEASE} />
        <main className="page">
          <section className="hero">
            <p className="hero__def">
              <b>CEOps</b> is a benchmark and paper on whether small, locally
              sovereign model deployments are good enough, safe enough, and
              efficient enough for bounded operations work.
            </p>
            <h1 className="hero__question">
              Which local model deployment is good enough at a cost your hardware
              can sustain?
            </h1>

            <div className="scopes">
              <span className="scope">
                <b>7 of 24</b>
                <span>controlled comparisons</span>
              </span>
              <span className="scope">
                <b>2 of 94</b>
                <span>breadth comparisons</span>
              </span>
              <span className="scope">
                <span>Single environment:</span>
                <b>reference CPU</b>
              </span>
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

            <PrimaryActions />

            <p className="boundary">
              <Info size={16} strokeWidth={2} aria-hidden />
              <span>
                Results hold for one measured environment and one preference
                rule. They do not rank models universally, and they do not imply
                readiness for autonomous operations.
              </span>
            </p>
          </section>
        </main>
      </Shell>
    </>
  );
}
