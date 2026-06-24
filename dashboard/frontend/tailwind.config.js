/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#06080f",
          900: "#0a0e1a",
          850: "#0e1322",
          800: "#121829",
          750: "#172037",
        },
        line: "#1d2740",
        accent: { DEFAULT: "#5b8cff", soft: "#16203c" },
        good: "#34d399",
        warn: "#fbbf24",
        bad: "#f87171",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(91,140,255,0.25), 0 8px 30px -12px rgba(91,140,255,0.45)",
      },
      keyframes: {
        pulseline: {
          "0%,100%": { opacity: "0.25" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        pulseline: "pulseline 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
