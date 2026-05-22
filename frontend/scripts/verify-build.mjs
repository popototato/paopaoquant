#!/usr/bin/env node
/** Fail build if index.html does not reference Streamlit /app/static/ asset URLs. */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const indexPath = path.resolve(__dirname, "../../static/trading_panel/index.html");
const requiredPrefix = "/app/static/trading_panel/assets/";

if (!fs.existsSync(indexPath)) {
  console.error(`[postbuild] Missing ${indexPath}. Run vite build first.`);
  process.exit(1);
}

const html = fs.readFileSync(indexPath, "utf8");
if (!html.includes(requiredPrefix)) {
  console.error(
    `[postbuild] index.html must use absolute asset URLs under ${requiredPrefix}`,
  );
  console.error("Use: cd frontend && npm run build  (production base /app/static/trading_panel/)");
  process.exit(1);
}

const assetsDir = path.resolve(__dirname, "../../static/trading_panel/assets");
if (!fs.existsSync(assetsDir)) {
  console.error(`[postbuild] Missing assets directory: ${assetsDir}`);
  process.exit(1);
}

console.log(`[postbuild] OK — ${indexPath}`);
