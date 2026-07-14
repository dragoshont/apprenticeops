import type { Preview } from "@storybook/react";
import "../src/styles/tokens.css";
import "../src/styles/app.css";

// Light (neutral) and charcoal dark are equal, first-class themes per the
// approved brief (§9.2). The toolbar switches the `data-theme` on the story
// root; every semantic token resolves from that attribute.
export const globalTypes = {
  theme: {
    description: "Color theme",
    defaultValue: "light",
    toolbar: {
      title: "Theme",
      icon: "mirror",
      items: [
        { value: "light", title: "Light (neutral)" },
        { value: "dark", title: "Dark (charcoal)" },
      ],
      dynamicTitle: true,
    },
  },
};

const preview: Preview = {
  parameters: {
    layout: "fullscreen",
    controls: {
      matchers: { color: /(background|color)$/i, date: /Date$/i },
    },
    a11y: {
      config: {
        rules: [
          // The illustrative Pareto chart is paired with a complete data table;
          // decorative SVG groups are marked aria-hidden intentionally.
        ],
      },
    },
  },
  decorators: [
    (Story, context) => {
      const theme = context.globals.theme === "dark" ? "dark" : "light";
      return (
        <div data-theme={theme} className="ceops-root">
          <Story />
        </div>
      );
    },
  ],
};

export default preview;
