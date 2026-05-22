"""TradingView Lightweight Charts 嵌入组件（Streamlit iframe）。"""

from __future__ import annotations

import csv
import json
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from data import ETH_CSV_PATH, beijing_str_to_ms

TRADING_PANEL_DIR = Path(__file__).resolve().parent / "static" / "trading_panel"
TRADING_PANEL_BUNDLE_JS = TRADING_PANEL_DIR / "panel.bundle.js"
TRADING_PANEL_BUNDLE_CSS = TRADING_PANEL_DIR / "panel.bundle.css"
TRADING_PANEL_INDEX_HTML = TRADING_PANEL_DIR / "index.html"
TRADING_PANEL_STATIC_BASE = "/app/static/trading_panel/"
TRADING_PANEL_STATIC_URL = f"{TRADING_PANEL_STATIC_BASE}index.html"

BEIJING_TZ = ZoneInfo("Asia/Shanghai")
LIGHTWEIGHT_CHARTS_CDN = (
    "https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.0/"
    "dist/lightweight-charts.standalone.production.js"
)


def load_ohlc_tail(csv_path: Path = ETH_CSV_PATH, n_bars: int = 1000) -> list[dict] | None:
    """读取 CSV 末尾 n 根 K 线，避免加载整个大文件。"""
    if not csv_path.exists() or csv_path.stat().st_size < 20:
        return None

    n_bars = max(1, int(n_bars))
    tail_lines: deque[str] = deque(maxlen=n_bars)

    with csv_path.open(encoding="utf-8") as file:
        reader = csv.reader(file)
        header = next(reader, None)
        if not header:
            return None
        for row in reader:
            if len(row) >= 5:
                tail_lines.append(row)

    if not tail_lines:
        return None

    bars: list[dict] = []
    for row in tail_lines:
        dt_str = row[0].strip()
        try:
            ts = beijing_str_to_ms(dt_str) // 1000
            bars.append(
                {
                    "time": ts,
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                }
            )
        except (ValueError, IndexError):
            continue
    if not bars:
        return None
    bars.sort(key=lambda b: b["time"])
    # 去重时间戳，避免 Lightweight Charts 报错
    deduped: list[dict] = []
    last_t = None
    for b in bars:
        if b["time"] != last_t:
            deduped.append(b)
            last_t = b["time"]
    return deduped or None


def _format_range_caption(bars: list[dict]) -> str:
    if not bars:
        return ""
    start_ts = bars[0]["time"]
    end_ts = bars[-1]["time"]
    start = datetime.fromtimestamp(start_ts, tz=BEIJING_TZ).strftime("%Y-%m-%d %H:%M")
    end = datetime.fromtimestamp(end_ts, tz=BEIJING_TZ).strftime("%Y-%m-%d %H:%M")
    return f"{start} → {end}（北京时间）"


def render_eth_candlestick_chart(
    bars: list[dict],
    *,
    height: int = 520,
    title: str = "ETH/USDT 1 分钟 K 线",
) -> None:
    """用 Lightweight Charts v4 渲染蜡烛图。"""
    data_json = json.dumps(bars, ensure_ascii=False)
    range_text = _format_range_caption(bars)
    safe_title = (
        title.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "PingFang SC", "Microsoft YaHei", sans-serif;
      background: #0e1117;
      color: #e6e8eb;
    }}
    #wrap {{
      width: 100%;
      padding: 8px 12px 4px;
    }}
    #title {{
      font-size: 15px;
      font-weight: 600;
      margin-bottom: 2px;
    }}
    #subtitle {{
      font-size: 12px;
      color: #9aa0a6;
      margin-bottom: 8px;
    }}
    #chart {{
      width: 100%;
      height: {height - 72}px;
    }}
    #credit {{
      font-size: 11px;
      color: #6b7280;
      margin-top: 6px;
      text-align: right;
    }}
  </style>
  <script src="{LIGHTWEIGHT_CHARTS_CDN}"></script>
</head>
<body>
  <div id="wrap">
    <div id="title">{safe_title}</div>
    <div id="subtitle">{len(bars):,} 根 · {range_text}</div>
    <div id="chart"></div>
    <div id="credit">Powered by TradingView Lightweight Charts</div>
  </div>
  <script>
    const bars = {data_json};
    const container = document.getElementById("chart");
    if (typeof LightweightCharts === "undefined") {{
      container.innerHTML = "<p style='color:#ef5350;padding:12px'>图表库加载失败，请检查网络或刷新页面。</p>";
    }} else try {{
    const chart = LightweightCharts.createChart(container, {{
      layout: {{
        background: {{ type: "solid", color: "#0e1117" }},
        textColor: "#d1d4dc",
      }},
      grid: {{
        vertLines: {{ color: "#1f2937" }},
        horzLines: {{ color: "#1f2937" }},
      }},
      crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
      rightPriceScale: {{ borderColor: "#374151" }},
      timeScale: {{
        borderColor: "#374151",
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time, tickMarkType) => {{
          const ts = typeof time === "number" ? time : Math.floor(new Date(time).getTime() / 1000);
          const d = new Date(ts * 1000);
          const fmt = (opts) => d.toLocaleString("zh-CN", {{ timeZone: "Asia/Shanghai", hour12: false, ...opts }});
          const T = LightweightCharts.TickMarkType;
          if (tickMarkType === T.Year) return fmt({{ year: "2-digit" }});
          if (tickMarkType === T.Month) return fmt({{ month: "short" }});
          if (tickMarkType === T.DayOfMonth) return fmt({{ month: "numeric", day: "numeric" }});
          if (tickMarkType === T.TimeWithSeconds) return fmt({{ hour: "2-digit", minute: "2-digit", second: "2-digit" }});
          return fmt({{ hour: "2-digit", minute: "2-digit" }});
        }},
      }},
      localization: {{
        locale: "zh-CN",
        dateFormat: "yyyy-MM-dd",
        timeFormatter: (time) => {{
          const ts = typeof time === "number" ? time : Math.floor(new Date(time).getTime() / 1000);
          return new Date(ts * 1000).toLocaleString("zh-CN", {{
            timeZone: "Asia/Shanghai",
            hour12: false,
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
          }});
        }},
      }},
    }});
    const series = chart.addCandlestickSeries({{
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
    }});
    series.setData(bars);
    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => {{
      chart.applyOptions({{ width: container.clientWidth }});
    }});
    ro.observe(container);
    chart.applyOptions({{ width: container.clientWidth }});
    }} catch (e) {{
      container.innerHTML = "<p style='color:#ef5350;padding:12px'>图表渲染失败: " + e.message + "</p>";
    }}
  </script>
</body>
</html>"""

    st.html(html, width="stretch")


_DEFAULT_TRADING_PANEL_HEIGHT = 1600


def _resolve_panel_bundle_paths() -> tuple[Path, Path]:
    """Return JS/CSS paths; prefer ``panel.bundle.*``, fall back to hashed legacy names."""
    js_path = TRADING_PANEL_BUNDLE_JS
    css_path = TRADING_PANEL_BUNDLE_CSS

    if not js_path.is_file():
        legacy_js = sorted(TRADING_PANEL_DIR.glob("index-*.js"))
        if not legacy_js:
            assets_dir = TRADING_PANEL_DIR / "assets"
            if assets_dir.is_dir():
                legacy_js = sorted(assets_dir.glob("index-*.js"))
        if legacy_js:
            js_path = legacy_js[0]

    if not css_path.is_file():
        legacy_css = sorted(TRADING_PANEL_DIR.glob("index-*.css"))
        if not legacy_css:
            assets_dir = TRADING_PANEL_DIR / "assets"
            if assets_dir.is_dir():
                legacy_css = sorted(assets_dir.glob("index-*.css"))
        if legacy_css:
            css_path = legacy_css[0]

    return js_path, css_path


def trading_panel_bundle_diagnostics() -> list[str]:
    issues: list[str] = []
    js_path, css_path = _resolve_panel_bundle_paths()
    if not js_path.is_file():
        issues.append(
            f"缺少 `{TRADING_PANEL_BUNDLE_JS.name}`（请在 `frontend` 目录执行 `npm run build`）。"
        )
    elif js_path.stat().st_size < 10_000:
        issues.append(f"`{js_path.name}` 体积异常偏小，请重新构建。")
    if not css_path.is_file():
        issues.append(
            f"缺少 `{TRADING_PANEL_BUNDLE_CSS.name}`（Vite 需 `cssCodeSplit: false`）。"
        )
    if not TRADING_PANEL_INDEX_HTML.is_file():
        issues.append(
            f"缺少 `{TRADING_PANEL_INDEX_HTML.name}`（`npm run build` 会通过 postbuild 生成）。"
        )
    return issues


def _is_paopao_dev() -> bool:
    return os.environ.get("PAOPAO_DEV", "").strip().lower() in ("1", "true", "yes")


def _trading_panel_srcdoc() -> str:
    """Build iframe HTML with absolute bundle URLs (srcdoc base is app root, not /app/static/)."""
    html = TRADING_PANEL_INDEX_HTML.read_text(encoding="utf-8")
    base = TRADING_PANEL_STATIC_BASE
    if f'href="{base}' not in html:
        html = (
            html.replace('href="panel.bundle.css"', f'href="{base}panel.bundle.css"')
            .replace('src="panel.bundle.js"', f'src="{base}panel.bundle.js"')
        )
    return html


def _render_trading_panel_static(*, panel_height: int) -> None:
    """Embed panel via ``st.iframe`` srcdoc; bundles load from ``enableStaticServing`` paths."""
    if _is_paopao_dev():
        st.caption(f"交易面板已加载（bundles: `{TRADING_PANEL_STATIC_BASE}`）")
    st.iframe(_trading_panel_srcdoc(), width="stretch", height=panel_height)


def render_trading_panel(*, height: int | None = None) -> None:
    """嵌入 React 交易面板（需先 `cd frontend && npm run build`）。

    Embeds ``index.html`` via ``st.iframe`` srcdoc; JS/CSS load from ``/app/static/trading_panel/``
    (``.streamlit/config.toml`` → ``enableStaticServing = true``). Avoids nesting the static
    HTML URL in an iframe (often shows an iframe error on Streamlit Cloud).
    """
    panel_height = height if height is not None else _DEFAULT_TRADING_PANEL_HEIGHT
    issues = trading_panel_bundle_diagnostics()
    if issues:
        st.error("交易面板构建产物异常：\n\n" + "\n".join(f"- {x}" for x in issues))
        st.code("cd frontend && npm install && npm run build", language="bash")
        return

    _render_trading_panel_static(panel_height=panel_height)

