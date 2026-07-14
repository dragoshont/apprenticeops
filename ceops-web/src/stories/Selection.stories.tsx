import type { Meta, StoryObj } from "@storybook/react";
import { SelectionPage } from "../pages/SelectionPage";

const meta = {
  title: "CEOps/Public/Selection",
  component: SelectionPage,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof SelectionPage>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The release-scoped controlled evidence explorer with the complete table. */
export const Explorer: Story = {};
