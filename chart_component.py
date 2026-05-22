"""TradingView Lightweight Charts 嵌入组件（Streamlit iframe）。"""

from __future__ import annotations

import csv
import json
import os
import re
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

from data import ETH_CSV_PATH, beijing_str_to_ms

TRADING_PANEL_DIR = Path(__file__).resolve().parent / "static" / "trading_panel"
TRADING_PANEL_INDEX = TRADING_PANEL_DIR / "index.html"
TRADING_PANEL_ASSETS_DIR = TRADING_PANEL_DIR / "assets"
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


def _streamlit_local_origin() -> str:
    """When ``st.context.url`` is missing, build origin from Streamlit server config."""
    try:
        from streamlit.config import get_option

        port = int(get_option("server.port"))
        address = str(get_option("server.address") or "localhost")
        if address in ("0.0.0.0", "::", ""):
            address = "localhost"
        elif address == "::1":
            address = "localhost"
        return f"http://{address}:{port}"
    except Exception:
        return "http://localhost:8501"


def _trading_panel_origin() -> str:
    base_url = getattr(st.context, "url", None)
    if base_url and base_url.startswith(("http://", "https://")):
        return base_url.rstrip("/")
    return _streamlit_local_origin().rstrip("/")


def _trading_panel_iframe_src() -> str:
    """Always return an absolute URL — relative ``/app/static/`` breaks ``st.iframe``."""
    return f"{_trading_panel_origin()}{TRADING_PANEL_STATIC_PATH}"


def _absolute_static_asset_url(path: str, *, origin: str | None = None) -> str:
    if path.startswith(("http://", "https://")):
        return path
    base = (origin or _trading_panel_origin()).rstrip("/")
    if path.startswith("/"):
        return f"{base}{path}"
    return urljoin(f"{base}/", path.lstrip("./"))


def _trading_panel_embed_html(*, origin: str | None = None) -> str:
    """Inject built panel CSS/JS into ``#paopao-trading-panel`` when iframe cannot load."""
    html = TRADING_PANEL_INDEX.read_text(encoding="utf-8")
    base = origin or _trading_panel_origin()
    chunks: list[str] = [
        '<div id="paopao-trading-panel" style="width:100%;min-height:1200px;"></div>'
    ]
    for tag in re.findall(r"<link[^>]+>", html, flags=re.I):
        if "stylesheet" not in tag.lower():
            continue
        m = re.search(r'href=["\']([^"\']+)["\']', tag, flags=re.I)
        if not m:
            continue
        abs_href = _absolute_static_asset_url(m.group(1), origin=base)
        chunks.append(f'<link rel="stylesheet" crossorigin href="{abs_href}">')
    for tag in re.findall(r'<script[^>]+src=["\'][^"\']+["\'][^>]*>', html, flags=re.I):
        m = re.search(r'src=["\']([^"\']+)["\']', tag, flags=re.I)
        if not m:
            continue
        abs_src = _absolute_static_asset_url(m.group(1), origin=base)
        chunks.append(
            f'<script type="module" crossorigin src="{abs_src}"></script>'
        )
    return "\n".join(chunks)


def _use_trading_panel_embed() -> bool:
    if os.environ.get("PAOPAO_TRADING_PANEL_EMBED", "").strip() in ("1", "true", "yes"):
        return True
    if st.session_state.get("_paopao_trading_panel_embed"):
        return True
    return st.query_params.get("panel_embed", "") == "1"


def _trading_panel_static_diagnostics() -> list[str]:
    """Return human-readable issues when the built panel is missing or mis-linked."""
    issues: list[str] = []
    if not TRADING_PANEL_INDEX.is_file():
        issues.append(
            f"缺少 `{TRADING_PANEL_INDEX.relative_to(TRADING_PANEL_DIR.parent.parent)}`"
        )
        return issues

    html = TRADING_PANEL_INDEX.read_text(encoding="utf-8")
    if 'src="./assets/' in html or 'href="./assets/' in html:
        issues.append(
            "index.html 仍使用相对路径 `./assets/`。"
            "请在 `frontend` 目录执行 `npm run build`（生产 base 应为 `/app/static/trading_panel/`）。"
        )

    if not TRADING_PANEL_ASSETS_DIR.is_dir():
        issues.append(f"缺少 assets 目录：`{TRADING_PANEL_ASSETS_DIR.name}/`")
        return issues

    asset_names = {p.name for p in TRADING_PANEL_ASSETS_DIR.iterdir() if p.is_file()}
    for attr, prefix in (("src", "src="), ("href", "href=")):
        marker = f'{attr}="/app/static/trading_panel/assets/'
        if marker not in html and f'{attr}="./assets/' not in html:
            continue
        # Extract referenced bundle names from index.html
        for part in html.split(prefix)[1:]:
            if "/assets/" not in part:
                continue
            name = part.split("/assets/", 1)[1].split('"', 1)[0].strip()
            if name and name not in asset_names:
                issues.append(f"index.html 引用的资源不存在：`assets/{name}`")

    return issues


def _render_trading_panel_iframe(panel_url: str, panel_height: int) -> None:
    """Prefer ``st.iframe``; fall back to ``components.v1.iframe`` on failure."""
    try:
        st.iframe(
            panel_url,
            width="stretch",
            height=panel_height,
        )
    except Exception:
        components.iframe(
            src=panel_url,
            width=None,
            height=panel_height,
            scrolling=True,
        )


def render_trading_panel(*, height: int | None = None) -> None:
    """嵌入 React 交易面板（需先 `cd frontend && npm run build`）。

    Uses absolute ``/app/static/`` URLs (``enableStaticServing``). Falls back to
    inline embed in ``#paopao-trading-panel`` when iframe mode is unavailable.
    """
    panel_height = height if height is not None else _DEFAULT_TRADING_PANEL_HEIGHT

    panel_url = _trading_panel_iframe_src()
    issues = _trading_panel_static_diagnostics()
    if issues:
        st.error("交易面板静态资源异常，图表无法加载：\n\n" + "\n".join(f"- {x}" for x in issues))
        st.markdown(
            f"构建后应可通过 [静态面板]({panel_url}) 直接打开（需已部署且 `enableStaticServing = true`）。"
        )
        st.code("cd frontend && npm install && npm run build", language="bash")
        return

    if _use_trading_panel_embed():
        st.html(_trading_panel_embed_html(), width="stretch")
        return

    _render_trading_panel_iframe(panel_url, panel_height)

    with st.expander("图表区域空白？"):
        st.caption(
            f"先在新标签页打开 [静态面板]({panel_url}) 确认资源可访问。"
            "若静态页正常但 iframe 空白，可改用内联嵌入（避开 Streamlit #root 冲突）。"
        )
        if st.button("改用内联嵌入模式", key="paopao_panel_embed_btn"):
            st.session_state["_paopao_trading_panel_embed"] = True
            st.rerun()

