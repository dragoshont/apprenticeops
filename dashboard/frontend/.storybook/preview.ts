import type { Preview } from "@storybook/react";
import "../src/index.css";

const preview: Preview = {
  parameters: {
    backgrounds: {
      default: "mission control",
      values: [
        { name: "mission control", value: "rgb(6 8 15)" },
        { name: "light", value: "rgb(246 248 251)" },
      ],
    },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
  },
};

export default preview;
