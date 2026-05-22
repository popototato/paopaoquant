"""TradingView Lightweight Charts 嵌入组件（Streamlit iframe）。"""

from __future__ import annotations

import csv
import json
from collections import deque
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from data import ETH_CSV_PATH, beijing_str_to_ms

TRADING_PANEL_DIR = Path(__file__).resolve().parent / "static" / "trading_panel"
TRADING_PANEL_INDEX = TRADING_PANEL_DIR / "index.html"
TRADING_PANEL_STATIC_PATH = "/app/static/trading_panel/index.html"

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


# Default iframe height (px); browser loads JS via /app/static/ — no server-side inline
_DEFAULT_TRADING_PANEL_HEIGHT = 1600


def _trading_panel_iframe_src() -> str:
    """Cloud 上 iframe 需要绝对 URL；本地回退相对 static 路径。"""
    base_url = getattr(st.context, "url", None)
    if base_url and base_url.startswith(("http://", "https://")):
        return f"{base_url.rstrip('/')}{TRADING_PANEL_STATIC_PATH}"
    return TRADING_PANEL_STATIC_PATH


def render_trading_panel(*, height: int | None = None) -> None:
    """嵌入 React 交易面板（需先 `cd frontend && npm run build`）。

    仅使用 ``st.iframe`` + ``/app/static/``（``enableStaticServing``），
    不在 Python 侧内联 JS，避免 Cloud 首屏 keepalive 超时。
    """
    panel_height = height if height is not None else _DEFAULT_TRADING_PANEL_HEIGHT

    if not TRADING_PANEL_INDEX.is_file():
        st.warning(
            "交易面板尚未构建。请在项目根目录执行："
            "`cd frontend && npm install && npm run build`"
        )
        return

    st.iframe(
        _trading_panel_iframe_src(),
        width="stretch",
        height=panel_height,
    )

