import type { Meta, StoryObj } from "@storybook/react";
import { StateBadge, MeasureBadge } from "../components/StateBadge";

const SPACES: [string, string][] = [
  ["1", "4"],
  ["2", "8"],
  ["3", "12"],
  ["4", "16"],
  ["5", "24"],
  ["6", "32"],
  ["7", "48"],
  ["8", "64"],
];

/** A single-screen tour of the CEOps visual system for design sign-off. */
function Foundations() {
  return (
    <main className="page" style={{ paddingTop: 40, paddingBottom: 80 }}>
      <p className="eyebrow">CEOps design tokens</p>
      <h1 className="pagetitle">Foundations</h1>
      <p className="lede">
        Editorial-scientific, not SaaS: Source Serif 4 for titles, Source Sans 3
        for text and data, and evidence state carried by word, icon and border in
        addition to color.
      </p>

      <section className="page__section">
        <p className="eyebrow">Type scale</p>
        <h2 className="pagetitle" style={{ marginBottom: 8 }}>
          Page title — Source Serif 4 48/54
        </h2>
        <p className="hero__question" style={{ margin: "0 0 12px" }}>
          Selection question — Serif 32/38
        </p>
        <p style={{ fontSize: 22, lineHeight: "28px", margin: "0 0 12px" }}>
          Section heading — Sans 22/28
        </p>
        <p style={{ maxWidth: 720, margin: "0 0 6px" }}>
          Body — Source Sans 3 15/23. Measurements use tabular numerals so
          columns align:{" "}
          <span className="u-tnum">0.6 · 3.6 · 9.8 Wh</span>.
        </p>
        <p
          style={{
            fontSize: 13,
            lineHeight: "18px",
            color: "var(--color-text-muted)",
          }}
        >
          Metadata — Sans 13/18.
        </p>
      </section>

      <section className="page__section">
        <p className="eyebrow">Evidence state — color is never the only cue</p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <StateBadge state="verified" />
          <StateBadge state="qualified" />
          <StateBadge state="withdrawn" />
          <StateBadge state="unavailable" />
        </div>
        <p className="eyebrow" style={{ marginTop: 24 }}>
          Measurement type — a separate axis
        </p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <MeasureBadge label="Measured" />
          <MeasureBadge label="Judged" />
          <MeasureBadge label="Derived" />
          <MeasureBadge label="Proxy" />
          <MeasureBadge label="Unavailable" />
        </div>
      </section>

      <section className="page__section">
        <p className="eyebrow">Spacing scale (px)</p>
        <div style={{ display: "flex", gap: 16, alignItems: "flex-end", flexWrap: "wrap" }}>
          {SPACES.map(([step, px]) => (
            <div key={step} style={{ textAlign: "center" }}>
              <div
                style={{
                  width: `${px}px`,
                  height: `${px}px`,
                  background: "var(--state-verified-tint)",
                  border: "1px solid var(--state-verified-line)",
                  borderRadius: 2,
                }}
              />
              <div
                className="u-tnum"
                style={{ fontSize: 12, marginTop: 6, color: "var(--color-text-muted)" }}
              >
                {px}
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

const meta = {
  title: "CEOps/Foundations",
  component: Foundations,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof Foundations>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Tokens: Story = {};
