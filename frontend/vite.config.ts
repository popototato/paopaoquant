import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/** Streamlit Cloud static URL prefix (enableStaticServing). */
const STREAMLIT_STATIC_BASE = "/app/static/trading_panel/";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // Cloud iframe loads /app/static/trading_panel/index.html — assets must be absolute.
  // Dev server: relative base. Override: VITE_BASE=./ npm run build
  base:
    process.env.VITE_BASE ??
    (mode === "development" ? "./" : STREAMLIT_STATIC_BASE),
  build: {
    outDir: "../static/trading_panel",
    emptyOutDir: true,
  },
}));
