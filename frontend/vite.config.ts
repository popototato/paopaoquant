import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.resolve(__dirname, "../static/trading_panel");

export default defineConfig(({ mode }) => {
  if (mode === "production") {
    return {
      plugins: [react()],
      define: {
        "process.env.NODE_ENV": JSON.stringify("production"),
      },
      build: {
        lib: {
          entry: path.resolve(__dirname, "src/main.tsx"),
          name: "PaopaoTradingPanel",
          formats: ["iife"],
          fileName: () => "panel.bundle.js",
        },
        cssCodeSplit: false,
        outDir: OUT_DIR,
        emptyOutDir: true,
        rollupOptions: {
          external: [],
          output: {
            inlineDynamicImports: true,
            assetFileNames: (assetInfo) =>
              assetInfo.name?.endsWith(".css") ? "panel.bundle.css" : "[name][extname]",
          },
        },
      },
    };
  }

  return {
    plugins: [react()],
    base: "./",
  };
});
