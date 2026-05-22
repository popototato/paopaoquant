/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        tv: {
          bg: "#131722",
          panel: "#1e222d",
          grid: "#2a2e39",
          text: "#d1d4dc",
          muted: "#787b86",
          border: "#2a2e39",
          accent: "#2962ff",
          up: "#089981",
          down: "#f23645",
        },
        liq: {
          bg: "#0b0e14",
          card: "#111827",
          border: "#1e293b",
          text: "#e2e8f0",
          muted: "#64748b",
          long: "#22c55e",
          short: "#ef4444",
          glowLong: "rgba(34, 197, 94, 0.35)",
          glowShort: "rgba(239, 68, 68, 0.35)",
          accent: "#38bdf8",
        },
      },
      boxShadow: {
        "liq-glow-long": "0 0 12px rgba(34, 197, 94, 0.25)",
        "liq-glow-short": "0 0 12px rgba(239, 68, 68, 0.25)",
        "liq-card": "0 0 0 1px #1e293b, 0 4px 24px rgba(0, 0, 0, 0.4)",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Trebuchet MS",
          "Roboto",
          "Ubuntu",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
