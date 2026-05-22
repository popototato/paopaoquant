from datetime import date, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from backtest import run_backtest
from data import (
    ETH_CSV_PATH,
    five_years_start_ms,
    format_ms_beijing,
    get_csv_info,
    update_eth_data,
)
from strategy import LayerStepConfig, create_strategy
from strategy_import import (
    default_steps_df,
    empty_steps_df,
    has_valid_steps,
    parse_steps_csv_file,
    parse_steps_text,
    valid_steps_rows,
)

# TradingView-style palette (aligned with app.py #131722 & chart_component)
_CLR_SURFACE = "#1e222d"
_CLR_BORDER = "#2a2e39"
_CLR_TEXT = "#d1d4dc"
_CLR_MUTED = "#787b86"
_CLR_ACCENT = "#2962ff"
_CLR_UP = "#26a69a"
_CLR_DOWN = "#ef5350"
_CLR_LINE = "#42a5f5"
_CLR_FEE = "#9aa0a6"
_CLR_INPUT_BORDER = "#363a45"
_CLR_INPUT_BORDER_HOVER = "#434651"

_CLR_BG = "#131722"
_BT_SCOPE = "section.main:has(.bt-page-marker)"
_BT_APP = ".stApp:has(.bt-page-marker)"
_BACKTEST_PAGE_MARKER = '<div class="bt-page-marker" aria-hidden="true"></div>'

_BACKTEST_PAGE_CSS = f"""
<style>
/* App shell — override Streamlit light base on some hosts (1.28+ / 1.32+) */
{_BT_APP},
{_BT_APP} [data-testid="stAppViewContainer"],
{_BT_APP} [data-testid="stAppViewBlockContainer"],
{_BT_APP} [data-testid="stMain"],
{_BT_APP} [data-testid="stMainBlockContainer"],
{_BT_APP} section.main,
{_BT_APP} [data-testid="stHeader"],
{_BT_APP} header[data-testid="stHeader"],
{_BT_APP} [data-testid="stToolbar"],
{_BT_APP} [data-testid="stDecoration"] {{
    background-color: {_CLR_BG} !important;
    color: {_CLR_TEXT} !important;
}}
{_BT_APP} [data-testid="stHeader"] {{
    background: {_CLR_BG} !important;
    border-bottom: 1px solid {_CLR_BORDER};
}}
{_BT_APP} [data-testid="stHeader"] a,
{_BT_APP} [data-testid="stHeader"] button,
{_BT_APP} [data-testid="stHeader"] span,
{_BT_APP} nav a,
{_BT_APP} nav button,
{_BT_APP} nav span {{
    color: {_CLR_TEXT} !important;
}}
{_BT_APP} [data-testid="stHeader"] a[aria-current="page"],
{_BT_APP} nav a[aria-current="page"] {{
    color: {_CLR_ACCENT} !important;
}}
{_BT_SCOPE} .block-container {{
    padding-top: 3.75rem;
    background-color: transparent !important;
}}
{_BT_SCOPE} [data-testid="stVerticalBlock"],
{_BT_SCOPE} [data-testid="stHorizontalBlock"],
{_BT_SCOPE} [data-testid="stColumn"] {{
    background-color: transparent !important;
}}
{_BT_SCOPE} h1, {_BT_SCOPE} h2, {_BT_SCOPE} h3 {{
    color: {_CLR_TEXT};
    font-weight: 600;
    letter-spacing: 0.02em;
}}
{_BT_SCOPE} p, {_BT_SCOPE} li, {_BT_SCOPE} label,
{_BT_SCOPE} [data-testid="stMarkdownContainer"] {{
    color: {_CLR_TEXT};
}}
{_BT_SCOPE} [data-testid="stCaptionContainer"] {{
    color: {_CLR_MUTED};
}}
{_BT_SCOPE} [data-testid="stWidgetLabel"] p {{
    color: {_CLR_MUTED} !important;
}}
/* Form inputs — dark surface, light text, TradingView borders */
{_BT_SCOPE} [data-testid="stTextInput"] input,
{_BT_SCOPE} [data-testid="stNumberInput"] input,
{_BT_SCOPE} [data-testid="stDateInput"] input,
{_BT_SCOPE} [data-testid="stTextArea"] textarea,
{_BT_SCOPE} textarea {{
    background-color: {_CLR_SURFACE} !important;
    color: {_CLR_TEXT} !important;
    border: 1px solid {_CLR_INPUT_BORDER} !important;
    border-radius: 4px;
    caret-color: {_CLR_TEXT};
}}
{_BT_SCOPE} [data-testid="stTextInput"] input:hover,
{_BT_SCOPE} [data-testid="stNumberInput"] input:hover,
{_BT_SCOPE} [data-testid="stDateInput"] input:hover,
{_BT_SCOPE} [data-testid="stTextArea"] textarea:hover,
{_BT_SCOPE} textarea:hover {{
    border-color: {_CLR_INPUT_BORDER_HOVER} !important;
}}
{_BT_SCOPE} [data-testid="stTextInput"] input:focus,
{_BT_SCOPE} [data-testid="stNumberInput"] input:focus,
{_BT_SCOPE} [data-testid="stDateInput"] input:focus,
{_BT_SCOPE} [data-testid="stTextArea"] textarea:focus,
{_BT_SCOPE} textarea:focus {{
    border-color: {_CLR_ACCENT} !important;
    box-shadow: 0 0 0 1px {_CLR_ACCENT};
    outline: none;
}}
{_BT_SCOPE} [data-testid="stNumberInput"] button {{
    background-color: {_CLR_SURFACE} !important;
    color: {_CLR_TEXT} !important;
    border-color: {_CLR_INPUT_BORDER} !important;
}}
{_BT_SCOPE} [data-testid="stNumberInput"] button:hover {{
    background-color: #2a2e39 !important;
    border-color: {_CLR_INPUT_BORDER_HOVER} !important;
    color: {_CLR_TEXT} !important;
}}
{_BT_SCOPE} [data-testid="stNumberInput"] button:focus {{
    border-color: {_CLR_ACCENT} !important;
    box-shadow: 0 0 0 1px {_CLR_ACCENT};
}}
{_BT_SCOPE} [data-testid="stSelectbox"] [data-baseweb="select"] > div,
{_BT_SCOPE} [data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
    background-color: {_CLR_SURFACE} !important;
    color: {_CLR_TEXT} !important;
    border: 1px solid {_CLR_INPUT_BORDER} !important;
    border-radius: 4px;
}}
{_BT_SCOPE} [data-testid="stSelectbox"] [data-baseweb="select"] > div:hover,
{_BT_SCOPE} [data-testid="stMultiSelect"] [data-baseweb="select"] > div:hover {{
    border-color: {_CLR_INPUT_BORDER_HOVER} !important;
}}
{_BT_SCOPE} [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within,
{_BT_SCOPE} [data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within {{
    border-color: {_CLR_ACCENT} !important;
    box-shadow: 0 0 0 1px {_CLR_ACCENT};
}}
{_BT_SCOPE} [data-testid="stSelectbox"] svg,
{_BT_SCOPE} [data-testid="stMultiSelect"] svg {{
    fill: {_CLR_MUTED} !important;
}}
{_BT_SCOPE} [data-testid="stSelectbox"] input,
{_BT_SCOPE} [data-testid="stMultiSelect"] input {{
    color: {_CLR_TEXT} !important;
    -webkit-text-fill-color: {_CLR_TEXT};
}}
{_BT_SCOPE} [data-testid="stDateInput"] button {{
    background-color: {_CLR_SURFACE} !important;
    color: {_CLR_TEXT} !important;
    border-color: {_CLR_INPUT_BORDER} !important;
}}
{_BT_SCOPE} [data-testid="stDateInput"] button:hover {{
    background-color: #2a2e39 !important;
    border-color: {_CLR_INPUT_BORDER_HOVER} !important;
}}
{_BT_SCOPE} [data-testid="stDateInput"] [data-baseweb="input"]:focus-within {{
    border-color: {_CLR_ACCENT} !important;
    box-shadow: 0 0 0 1px {_CLR_ACCENT};
}}
{_BT_SCOPE} [data-testid="stSlider"] [data-baseweb="slider"] > div > div {{
    background: {_CLR_INPUT_BORDER} !important;
}}
{_BT_SCOPE} [data-testid="stSlider"] [role="slider"] {{
    background: {_CLR_ACCENT} !important;
    border-color: {_CLR_ACCENT} !important;
}}
{_BT_SCOPE} [data-testid="stSlider"] [data-testid="stThumbValue"],
{_BT_SCOPE} [data-testid="stSlider"] [data-testid="stTickBarMin"],
{_BT_SCOPE} [data-testid="stSlider"] [data-testid="stTickBarMax"] {{
    color: {_CLR_MUTED} !important;
}}
{_BT_SCOPE} [data-testid="stDataEditor"] {{
    --gdg-bg-cell: {_CLR_SURFACE};
    --gdg-bg-cell-medium: #2a2e39;
    --gdg-bg-header: #2a2e39;
    --gdg-bg-header-has-focus: {_CLR_INPUT_BORDER};
    --gdg-bg-header-hovered: {_CLR_INPUT_BORDER};
    --gdg-text-dark: {_CLR_TEXT};
    --gdg-text-medium: {_CLR_MUTED};
    --gdg-text-light: {_CLR_TEXT};
    --gdg-text-header: {_CLR_TEXT};
    --gdg-border-color: {_CLR_INPUT_BORDER};
    --gdg-horizontal-border-color: {_CLR_INPUT_BORDER};
    --gdg-vertical-border-color: {_CLR_INPUT_BORDER};
    --gdg-accent-color: {_CLR_ACCENT};
    --gdg-accent-fg: #ffffff;
    --gdg-accent-light: rgba(41, 98, 255, 0.25);
    --gdg-bg-icon-header: #2a2e39;
    --gdg-fg-icon-header: {_CLR_MUTED};
}}
{_BT_SCOPE} [data-testid="stDataEditor"] input,
{_BT_SCOPE} [data-testid="stDataEditor"] textarea {{
    background-color: {_CLR_SURFACE} !important;
    color: {_CLR_TEXT} !important;
    border-color: {_CLR_INPUT_BORDER} !important;
}}
/* Popovers (select/date) — only injected on backtest page */
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] ul,
div[data-baseweb="menu"] {{
    background-color: {_CLR_SURFACE} !important;
    border-color: {_CLR_INPUT_BORDER} !important;
}}
div[data-baseweb="popover"] li,
div[data-baseweb="menu"] li {{
    color: {_CLR_TEXT} !important;
    background-color: transparent !important;
}}
div[data-baseweb="popover"] li:hover,
div[data-baseweb="menu"] li:hover {{
    background-color: #2a2e39 !important;
}}
div[data-baseweb="popover"] li[aria-selected="true"] {{
    background-color: rgba(41, 98, 255, 0.2) !important;
    color: {_CLR_TEXT} !important;
}}
{_BT_SCOPE} .stButton > button {{
    border-color: {_CLR_BORDER};
    color: {_CLR_TEXT};
    background: {_CLR_SURFACE};
}}
{_BT_SCOPE} .stButton > button[kind="primary"] {{
    background: {_CLR_ACCENT};
    border-color: {_CLR_ACCENT};
    color: #ffffff;
}}
{_BT_SCOPE} .stButton > button[kind="primary"]:hover {{
    background: #1e53e5;
    border-color: #1e53e5;
}}
{_BT_SCOPE} [data-testid="stMetric"] {{
    background: {_CLR_SURFACE};
    border: 1px solid {_CLR_BORDER};
    border-radius: 8px;
    padding: 0.65rem 0.85rem;
}}
{_BT_SCOPE} [data-testid="stMetricLabel"] {{
    color: {_CLR_MUTED};
}}
{_BT_SCOPE} [data-testid="stMetricValue"] {{
    color: {_CLR_TEXT};
}}
.bt-metric {{
    background: {_CLR_SURFACE};
    border: 1px solid {_CLR_BORDER};
    border-radius: 8px;
    padding: 0.65rem 0.85rem;
    min-height: 4.25rem;
}}
.bt-metric-label {{
    color: {_CLR_MUTED};
    font-size: 0.8rem;
    margin-bottom: 0.25rem;
}}
.bt-metric-value {{
    font-size: 1.35rem;
    font-weight: 600;
    line-height: 1.3;
    font-variant-numeric: tabular-nums;
}}
{_BT_SCOPE} [data-testid="stAlert"] {{
    border-radius: 8px;
    border-width: 1px;
}}
{_BT_SCOPE} [data-testid="stAlert"][data-baseweb="notification"] {{
    background-color: {_CLR_SURFACE};
}}
{_BT_SCOPE} div[data-testid="stNotificationContentInfo"] {{
    background-color: #1a2744;
    color: #8ab4f8;
    border: 1px solid #2d4a7a;
}}
{_BT_SCOPE} div[data-testid="stNotificationContentWarning"] {{
    background-color: #2a2416;
    color: #f0c14b;
    border: 1px solid #4a3f1f;
}}
{_BT_SCOPE} div[data-testid="stNotificationContentSuccess"] {{
    background-color: #152420;
    color: {_CLR_UP};
    border: 1px solid #1e4a3f;
}}
{_BT_SCOPE} div[data-testid="stNotificationContentError"] {{
    background-color: #2a1818;
    color: #f48fb1;
    border: 1px solid #5c2a2a;
}}
{_BT_SCOPE} details[data-testid="stExpander"] {{
    background: {_CLR_SURFACE};
    border: 1px solid {_CLR_BORDER};
    border-radius: 8px;
}}
{_BT_SCOPE} details[data-testid="stExpander"] summary {{
    color: {_CLR_TEXT};
}}
{_BT_SCOPE} [data-testid="stDataFrame"], {_BT_SCOPE} [data-testid="stDataEditor"] {{
    border: 1px solid {_CLR_BORDER};
    border-radius: 8px;
    overflow: hidden;
}}
{_BT_SCOPE} [data-testid="stProgress"] > div > div {{
    background-color: {_CLR_ACCENT};
}}
{_BT_SCOPE} [data-testid="stJson"] pre {{
    background: {_CLR_SURFACE} !important;
    color: {_CLR_TEXT} !important;
    border: 1px solid {_CLR_BORDER};
    border-radius: 8px;
}}
{_BT_SCOPE} .vega-embed {{
    background: {_CLR_SURFACE};
    border: 1px solid {_CLR_BORDER};
    border-radius: 8px;
    padding: 0.25rem;
}}
{_BT_SCOPE} [data-testid="stCheckbox"] label span,
{_BT_SCOPE} [data-testid="stRadio"] label span,
{_BT_SCOPE} [data-testid="stRadio"] label div {{
    color: {_CLR_TEXT} !important;
}}
{_BT_SCOPE} [data-testid="stCheckbox"] [data-baseweb="checkbox"] {{
    border-color: {_CLR_INPUT_BORDER} !important;
}}
{_BT_SCOPE} [data-testid="stFileUploader"] {{
    background: {_CLR_SURFACE};
    border: 1px dashed {_CLR_BORDER};
    border-radius: 8px;
}}
{_BT_SCOPE} [data-testid="stFileUploader"] label,
{_BT_SCOPE} [data-testid="stFileUploader"] small {{
    color: {_CLR_MUTED} !important;
}}
{_BT_SCOPE} [data-testid="stFileUploader"] button {{
    background: {_CLR_SURFACE} !important;
    color: {_CLR_TEXT} !important;
    border-color: {_CLR_BORDER} !important;
}}
{_BT_SCOPE} [data-testid="stSpinner"] {{
    color: {_CLR_TEXT} !important;
}}
{_BT_SCOPE} [data-testid="stSpinner"] > div {{
    border-top-color: {_CLR_ACCENT} !important;
}}
{_BT_SCOPE} [data-testid="stProgress"] > div {{
    background-color: {_CLR_INPUT_BORDER} !important;
}}
{_BT_SCOPE} hr {{
    border-color: {_CLR_BORDER} !important;
}}
{_BT_SCOPE} [data-testid="stTable"] {{
    background: {_CLR_SURFACE} !important;
}}
{_BT_SCOPE} [data-testid="stTable"] th {{
    background: #2a2e39 !important;
    color: {_CLR_TEXT} !important;
    border-color: {_CLR_BORDER} !important;
}}
{_BT_SCOPE} [data-testid="stTable"] td {{
    background: {_CLR_SURFACE} !important;
    color: {_CLR_TEXT} !important;
    border-color: {_CLR_BORDER} !important;
}}
{_BT_SCOPE} [data-testid="stCode"] {{
    background: {_CLR_SURFACE} !important;
}}
{_BT_SCOPE} [data-testid="stCode"] code {{
    color: {_CLR_TEXT} !important;
    background: #2a2e39 !important;
}}
{_BT_SCOPE} [data-testid="stTooltipIcon"] {{
    color: {_CLR_MUTED} !important;
}}
{_BT_SCOPE} [data-testid="stWidgetLabel"] {{
    color: {_CLR_MUTED};
}}
</style>
"""

_ALT_AXIS = {
    "gridColor": _CLR_BORDER,
    "domainColor": _CLR_BORDER,
    "labelColor": _CLR_MUTED,
    "titleColor": _CLR_TEXT,
    "tickColor": _CLR_BORDER,
}


def _inject_backtest_styles() -> None:
    """Marker + CSS first so shell/widgets stay dark on light-theme Streamlit hosts."""
    st.markdown(_BACKTEST_PAGE_MARKER, unsafe_allow_html=True)
    st.markdown(_BACKTEST_PAGE_CSS, unsafe_allow_html=True)


def _pnl_color(value: float) -> str:
    if value > 0:
        return _CLR_UP
    if value < 0:
        return _CLR_DOWN
    return _CLR_TEXT


def _styled_metric(label: str, value: str, color: str) -> None:
    st.markdown(
        f'<div class="bt-metric">'
        f'<div class="bt-metric-label">{label}</div>'
        f'<div class="bt-metric-value" style="color:{color}">{value}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _altair_base(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure_view(strokeWidth=0, fill=_CLR_SURFACE)
        .configure_axis(**_ALT_AXIS)
        .configure(background=_CLR_SURFACE)
        .properties(height=280)
    )


def _daily_pnl_bar_chart(df: pd.DataFrame) -> None:
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=2)
        .encode(
            x=alt.X("日期:N", title="日期", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("当日净盈利:Q", title="USDT"),
            color=alt.condition(
                "datum.当日净盈利 > 0",
                alt.value(_CLR_UP),
                alt.value(_CLR_DOWN),
            ),
            tooltip=[
                alt.Tooltip("日期:N", title="日期"),
                alt.Tooltip("当日净盈利:Q", title="净盈利", format=",.2f"),
            ],
        )
    )
    st.altair_chart(_altair_base(chart), width="stretch")


def _cumulative_pnl_line_chart(df: pd.DataFrame) -> None:
    area = (
        alt.Chart(df)
        .mark_area(opacity=0.18, color=_CLR_LINE)
        .encode(
            x=alt.X("日期:N", title="日期", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("累计净盈利:Q", title="USDT"),
        )
    )
    line = (
        alt.Chart(df)
        .mark_line(color=_CLR_LINE, strokeWidth=2)
        .encode(
            x="日期:N",
            y="累计净盈利:Q",
            tooltip=[
                alt.Tooltip("日期:N", title="日期"),
                alt.Tooltip("累计净盈利:Q", title="累计", format=",.2f"),
            ],
        )
    )
    st.altair_chart(_altair_base(area + line), width="stretch")


_inject_backtest_styles()

st.title("有限层级均值回归网格策略回测")

st.subheader("行情数据")
st.caption(
    f"数据源：Binance ETH/USDT **1 分钟线**（北京时间），本地文件 `{ETH_CSV_PATH.name}`，保留近 **5 年**。"
)

meta = get_csv_info()
st.session_state.data_meta = meta

if "force_full" not in st.session_state:
    has_1m = bool(meta and meta.get("interval") == "1m" and meta.get("count", 0) > 0)
    st.session_state.force_full = not has_1m

force_full = st.checkbox(
    "强制全量重下（近 5 年 1 分钟线，覆盖 eth.csv）",
    help="会先删除现有 eth.csv，再从 Binance 重下近 5 年 1m K 线（约 260 万条，15~40 分钟）。已有 1m 数据时请勿勾选。",
    key="force_full",
)

data_col1, data_col2 = st.columns([1, 3])

with data_col1:
    refresh_clicked = st.button("下载/更新 1 分钟线", type="secondary")

with data_col2:
    if meta and meta["count"] > 0:
        tz = meta.get("timezone", "北京时间 (UTC+8)")
        st.info(
            f"Binance ETH/USDT **1m** | {tz} | 共 **{meta['count']:,}** 条 | "
            f"{meta['start']} → {meta['end']}"
        )
        st.caption(
            f"路径：`{meta['path']}` | 文件 **{meta.get('size_mb', '?')} MB** | "
            f"文件更新时间 {meta.get('updated_at', '—')}（北京时间）"
        )
        if meta.get("interval") != "1m":
            st.warning("当前不是 1 分钟数据，请勾选「强制全量重下」后重新下载。")
        else:
            st.caption("数据已在本地，打开页面即可回测；「下载/更新」仅补齐最新 K 线（增量）。")
    else:
        st.warning(
            f"暂无本地数据（`{ETH_CSV_PATH}` 不存在或为空）。"
            "首次请直接点击「下载/更新」；若勾选「强制全量重下」会**先删除**已有文件再重下。"
        )

if refresh_clicked:
    from datetime import datetime, timezone

    progress_bar = st.progress(0.0, text="准备拉取...")
    status_text = st.empty()
    progress_state = {"now_ms": None}

    def on_progress(count: int, current_ms: int) -> None:
        if progress_state["now_ms"] is None:
            progress_state["now_ms"] = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_ms = five_years_start_ms(progress_state["now_ms"])
        span = progress_state["now_ms"] - start_ms
        ratio = min((current_ms - start_ms) / span, 1.0) if span > 0 else 0.0
        progress_bar.progress(ratio, text=f"已获取 {count:,} 条...")
        status_text.caption(
            f"{'全量重下' if force_full else '增量更新'} · "
            f"进度至 {format_ms_beijing(current_ms)} 北京时间"
        )

    try:
        meta = update_eth_data(progress_callback=on_progress, force_full=force_full)
        st.session_state["data_meta"] = meta
        progress_bar.progress(1.0, text="完成")
        mode = "全量重下" if force_full else "增量更新"
        st.success(f"{mode}完成，共 {meta['count']:,} 条（{meta['start']} → {meta['end']}）")
        st.rerun()
    except Exception as exc:
        st.error(f"拉取失败：{exc}")

st.subheader("回测时间区间（北京时间）")
if not meta or not meta.get("start_date"):
    meta = get_csv_info()
    st.session_state.data_meta = meta

if meta and meta.get("start_date"):
    data_min: date = meta["start_date"]
    data_max: date = meta["end_date"]

    if "backtest_start" not in st.session_state:
        st.session_state.backtest_start = data_min
    if "backtest_end" not in st.session_state:
        st.session_state.backtest_end = data_max
    if "range_end_all" not in st.session_state:
        st.session_state.range_end_all = False

    for _legacy in ("range_start", "range_end"):
        st.session_state.pop(_legacy, None)

    st.caption(
        f"数据可用范围：**{data_min}** ~ **{data_max}**（北京时间，末根 K 线 {meta.get('end', '—')}）｜"
        f"回测从「开始日期」当天 **00:00** 起开单"
    )

    st.session_state.backtest_start = max(
        data_min, min(st.session_state.backtest_start, data_max)
    )
    if not st.session_state.range_end_all:
        st.session_state.backtest_end = max(
            st.session_state.backtest_start,
            min(st.session_state.backtest_end, data_max),
        )

    date_col1, date_col2 = st.columns(2)
    with date_col1:
        backtest_start = st.date_input(
            "开始日期",
            min_value=data_min,
            max_value=data_max,
            key="backtest_start",
        )
    with date_col2:
        st.checkbox(
            "结束至数据末尾（所有时间）",
            help=f"不截断日历日，回测至 CSV 最后一根 K 线（{meta.get('end', '—')}）",
            key="range_end_all",
        )
        if st.session_state.range_end_all:
            backtest_end = None
            st.caption(f"结束：**{data_max}** 及以前全部 1m K 线（末根 {meta.get('end', '—')}）")
        else:
            backtest_end = st.date_input(
                "结束日期",
                min_value=backtest_start,
                max_value=data_max,
                key="backtest_end",
            )
else:
    backtest_start = None
    backtest_end = None
    st.caption("加载数据后可选择回测区间（按北京时间日历日）。")

st.subheader("账户与策略")
account_amount = st.number_input(
    "账户金额（USDT）",
    min_value=1000.0,
    value=3000.0,
    step=1000.0,
    help="操作账户固定本金（如 3000 USDT）。回测净盈亏不低于 -账户金额："
    "爆仓累计亏损最多亏光本金，单笔爆仓亦按剩余可亏额度封顶，不穿仓。",
)

position_unit = "eth"
trade_mode = st.selectbox(
    "交易模式",
    options=["dual", "long_only", "short_only"],
    format_func=lambda x: {
        "dual": "多空双开",
        "long_only": "只做多",
        "short_only": "只做空",
    }[x],
    help="若实盘只跑单边网格，请选「只做多」或「只做空」，止盈次数会更接近实盘。",
)
leverage = st.number_input(
    "合约杠杆（与实盘一致，不改变 ETH 开单数量）",
    min_value=1,
    max_value=125,
    value=100,
    step=1,
    help="按 ETH 数量开单时，盈亏 = 价差 × ETH 数量；杠杆主要影响保证金与爆仓距离。",
)

st.subheader("策略步骤配置")
st.caption(
    "每层仓位 = **ETH 数量**（与实盘一致）。开始日 **00:00** 多空各开第 1 步；"
    "之后每根 1m K：**先**有利价（多=High/空=Low）按**全仓加权均价+当前最高步止盈距离**止盈，"
    "触发当根 K **平仓并同价重开第 1 步**；未止盈时不利价相对**第 1 步价累计间距**推断第几步并补仓，"
    "再判强平。已扣 OKX Maker 0.02% 手续费。"
)

if "steps_data" not in st.session_state:
    st.session_state.steps_data = empty_steps_df()

if st.button(
    "加载默认配置",
    type="secondary",
    help="25 层 OKX 实盘参数（每层仓位 ×0.85）",
):
    st.session_state.steps_data = default_steps_df()
    st.rerun()

with st.expander("批量粘贴 / 导入 CSV", expanded=False):
    st.markdown(
        "从 **Excel** 复制多行后粘贴到下方（Tab 分隔），或上传 CSV。"
        "列顺序：`第几步 | 补仓间距 | 每层仓位 | 止盈距离`，可有表头。"
    )
    paste_text = st.text_area(
        "粘贴区",
        height=160,
        placeholder=(
            "第几步\t补仓间距\t每层仓位\t止盈距离\n"
            "1\t100\t0.5\t80\n"
            "2\t100\t1.0\t80\n"
            "3\t100\t1.5\t80"
        ),
        label_visibility="collapsed",
    )
    import_col1, import_col2 = st.columns(2)
    with import_col1:
        if st.button("导入粘贴内容", type="secondary"):
            try:
                st.session_state.steps_data = parse_steps_text(paste_text)
                st.success(f"已导入 {len(st.session_state.steps_data)} 行")
                st.rerun()
            except Exception as exc:
                st.error(f"导入失败：{exc}")
    with import_col2:
        uploaded = st.file_uploader("或上传 CSV", type=["csv"], label_visibility="collapsed")
        if uploaded is not None and st.button("导入 CSV 文件", type="secondary"):
            try:
                st.session_state.steps_data = parse_steps_csv_file(uploaded)
                st.success(f"已导入 {len(st.session_state.steps_data)} 行")
                st.rerun()
            except Exception as exc:
                st.error(f"导入失败：{exc}")

steps_df = st.data_editor(
    st.session_state.steps_data,
    num_rows="dynamic",
    width="stretch",
    key="steps_table",
    column_config={
        "第几步": st.column_config.NumberColumn(min_value=1, step=1),
        "补仓间距": st.column_config.NumberColumn("补仓间距（USDT）", min_value=1.0, step=10.0),
        "每层仓位": st.column_config.NumberColumn(
            "每层仓位（ETH）",
            min_value=0.001,
            step=0.01,
            format="%.4f",
        ),
        "止盈距离": st.column_config.NumberColumn("止盈距均价（USDT）", min_value=1.0, step=10.0),
    },
)
st.session_state.steps_data = steps_df

if st.button("开始回测", type="primary"):
    if not meta or meta["count"] == 0:
        st.error("请先刷新并加载行情数据。")
    elif backtest_end is not None and backtest_start > backtest_end:
        st.error("开始日期不能晚于结束日期。")
    elif not has_valid_steps(steps_df):
        st.error(
            "策略步骤表为空，请先导入 CSV、粘贴步骤，或在表格中手动填写至少一步；"
            "也可点击「加载默认配置」使用 25 层 OKX 模板。"
        )
    else:
        filled = valid_steps_rows(steps_df)
        layers = [
            LayerStepConfig(
                step=int(row["第几步"]),
                spacing_usdt=float(row["补仓间距"]),
                position_size=float(row["每层仓位"]),
                take_profit_distance=float(row["止盈距离"]),
            )
            for _, row in filled.iterrows()
        ]
        strategy = create_strategy(
            layers=layers,
            account_amount=account_amount,
            position_unit=position_unit,
            leverage=int(leverage),
            trade_mode=trade_mode,
        )
        with st.spinner("回测运行中..."):
            result = run_backtest(
                strategy,
                start_date=backtest_start,
                end_date=backtest_end,
            )

        st.subheader("回测结果")
        net_pnl = float(result["净盈利数额"])
        gross_profit = float(result["盈利数额"])
        gross_loss = float(result["亏损数额"])
        fee_total = float(result["手续费合计"])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            _styled_metric("净盈利", f"{net_pnl:,.2f} USDT", _pnl_color(net_pnl))
        with col2:
            _styled_metric(
                "止盈次数",
                f"{result.get('止盈次数', 0):,}",
                _CLR_UP,
            )
        with col3:
            _styled_metric(
                "爆仓次数",
                f"{result['爆仓次数']:,}",
                _CLR_DOWN if result["爆仓次数"] else _CLR_TEXT,
            )
        with col4:
            _styled_metric(
                "补仓次数",
                f"{result.get('补仓次数', 0):,}",
                _CLR_TEXT,
            )

        col5, col6, col7 = st.columns(3)
        with col5:
            _styled_metric(
                "毛利盈利",
                f"{gross_profit:,.2f} USDT",
                _pnl_color(gross_profit),
            )
        with col6:
            _styled_metric(
                "毛利亏损",
                f"{gross_loss:,.2f} USDT",
                _CLR_DOWN if gross_loss else _CLR_TEXT,
            )
        with col7:
            _styled_metric(
                "手续费",
                f"{fee_total:,.2f} USDT",
                _CLR_FEE,
            )

        st.caption(
            f"回测区间：{result['回测区间']} | "
            f"{result.get('合约杠杆', '')} | "
            f"{result.get('开单方式', '')} | "
            f"{result.get('手续费说明', '')}"
        )

        daily_pnl = result.get("每日盈利", {})
        chart_end = backtest_end or (meta.get("end_date") if meta else None)
        if daily_pnl and backtest_start and chart_end:
            st.subheader("每日盈利")
            rows = []
            day = backtest_start
            while day <= chart_end:
                key = day.isoformat()
                rows.append({"日期": key, "当日净盈利": float(daily_pnl.get(key, 0.0))})
                day += timedelta(days=1)
            chart_df = pd.DataFrame(rows)
            chart_df["累计净盈利"] = chart_df["当日净盈利"].cumsum()

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.caption("每日净盈利（USDT，含手续费，按平仓日）")
                _daily_pnl_bar_chart(chart_df)
            with chart_col2:
                st.caption("累计净盈利（USDT）")
                _cumulative_pnl_line_chart(chart_df)

        st.json(result)
