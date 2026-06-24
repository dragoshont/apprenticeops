import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend (FastAPI) does the SSH + log reading and exposes /api + /ws.
// In dev, Vite proxies to it so the React app can fetch with same-origin paths.
const BACKEND = process.env.BACKEND_ORIGIN || "http://127.0.0.1:8770";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5290,
    host: "127.0.0.1",
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true },
      "/ws": { target: BACKEND.replace(/^http/, "ws"), ws: true },
    },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
