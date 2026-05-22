#!/usr/bin/env node
/** Fail build if IIFE bundle artifacts are missing. */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const panelDir = path.resolve(__dirname, "../../static/trading_panel");
const jsPath = path.join(panelDir, "panel.bundle.js");
const cssPath = path.join(panelDir, "panel.bundle.css");
const indexPath = path.join(panelDir, "index.html");

const indexHtml = `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>泡泡量化 · 交易面板</title>
    <link rel="stylesheet" href="/app/static/trading_panel/panel.bundle.css" />
  </head>
  <body>
    <div id="paopao-trading-panel" style="width: 100%; min-height: 700px"></div>
    <script src="/app/static/trading_panel/panel.bundle.js"></script>
  </body>
</html>
`;

if (!fs.existsSync(jsPath)) {
  console.error(`[postbuild] Missing ${jsPath}. Run: cd frontend && npm run build`);
  process.exit(1);
}

const jsStat = fs.statSync(jsPath);
if (jsStat.size < 10_000) {
  console.error(`[postbuild] panel.bundle.js looks too small (${jsStat.size} bytes).`);
  process.exit(1);
}

if (!fs.existsSync(cssPath)) {
  console.error(`[postbuild] Missing ${cssPath}. Ensure cssCodeSplit: false in vite.config.ts.`);
  process.exit(1);
}

fs.writeFileSync(indexPath, indexHtml, "utf-8");

console.log(
  `[postbuild] OK — ${jsPath} (${(jsStat.size / 1024).toFixed(0)} KB), ${cssPath}, ${indexPath}`,
);
