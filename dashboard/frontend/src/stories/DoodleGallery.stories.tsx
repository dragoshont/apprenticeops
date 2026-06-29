import type { Meta, StoryObj } from "@storybook/react";
import { DoodleGallery, type DoodleOutput } from "../components/DoodleGallery";
import { doodleOutputs } from "./doodleFixtures";

const RUN_ID = "doodle-doodle-6-none-baseline-20260629-174430";

const meta = {
  title: "Mission Control/Doodle Gallery",
  component: DoodleGallery,
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story) => (
      <div className="min-h-screen bg-bg px-4 py-6 text-fg sm:px-6 lg:py-8">
        <div className="mx-auto max-w-7xl">
          <Story />
        </div>
      </div>
    ),
  ],
} satisfies Meta<typeof DoodleGallery>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Real SVG completions captured from a live doodle run. */
export const Populated: Story = {
  args: { outputs: doodleOutputs, runId: RUN_ID },
};

/** Same outputs, regrouped by model — the toggle's second lens. */
export const ByModel: Story = {
  args: { outputs: doodleOutputs, runId: RUN_ID, defaultGroupBy: "model" },
};

/** One scenario, every model attempt side by side. */
export const SingleScenario: Story = {
  args: {
    outputs: doodleOutputs.filter((output) => output.scenario === "doodle-wolf-moon"),
    runId: RUN_ID,
  },
};

const placeholderOnly: DoodleOutput[] = [
  {
    scenario: "doodle-butterfly",
    model: "qwen2.5:0.5b",
    rep: 1,
    detScore: 0,
    svg: '<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg"><!-- Insert your butterfly SVG code here --></svg>',
  },
];

/** A model that returned an empty SVG shell is flagged, not rendered blank. */
export const PlaceholderOnly: Story = {
  args: { outputs: placeholderOnly, runId: RUN_ID },
};

/** No SVG outputs yet for the selected run. */
export const Empty: Story = {
  args: { outputs: [], runId: undefined },
};

/** Outputs are still being collected for the selected run. */
export const Loading: Story = {
  args: { outputs: [], runId: RUN_ID, loading: true },
};

const maliciousProbe: DoodleOutput[] = [
  {
    scenario: "doodle-xss-probe",
    model: "untrusted-input",
    rep: 1,
    detScore: 0,
    svg:
      '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" ' +
      'onload="window.parent.__XSS__=1">' +
      "<script>window.parent.__XSS__=1<\/script>" +
      '<circle cx="100" cy="100" r="80" fill="#c0392b"/>' +
      '<text x="100" y="105" text-anchor="middle" fill="#fff" font-size="14">probe</text>' +
      "</svg>",
  },
];

/**
 * Adversarial: the SVG carries both an `onload=` handler and a `<script>` that
 * try to set `window.parent.__XSS__`. Because <DoodleTile> renders it inside
 * `<iframe sandbox="">`, neither executes — only the red circle paints.
 */
export const SandboxSecurityProbe: Story = {
  args: { outputs: maliciousProbe, runId: "security-probe" },
};
