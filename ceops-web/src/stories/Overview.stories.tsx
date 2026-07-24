import type { Meta, StoryObj } from "@storybook/react";
import { OverviewPage } from "../pages/OverviewPage";

const meta = {
  title: "CEOps/Public/Overview",
  component: OverviewPage,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof OverviewPage>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The public homepage first viewport. Toggle Theme in the toolbar to review
 *  the neutral-light and charcoal-dark modes; both are first-class. */
export const FirstViewport: Story = {};
