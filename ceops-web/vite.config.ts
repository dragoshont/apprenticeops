import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Design-only preview workbench. No backend proxy; Storybook renders static
// design surfaces driven by illustrative data.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", emptyOutDir: true },
});
