import streamlit as st

from chart_component import render_trading_panel
from data import ETH_CSV_PATH, get_csv_info

_HOME_PANEL_KEY = "home_trading_panel_loaded"

st.markdown(
    """
<style>
[data-testid="stCaptionContainer"] {
    color: #787b86;
    padding-top: 0.25rem;
}
</style>
""",
    unsafe_allow_html=True,
)

with st.spinner("正在加载页面信息…"):
    meta = get_csv_info(count_rows=False)

if meta and meta.get("count", 0) > 0:
    count_note = ""
    if meta.get("count_estimated"):
        count_note = "（约）"
    st.caption(
        f"本地 1m 回测数据{count_note}：{meta['count']:,} 条 | "
        f"{meta.get('start', '—')} → {meta.get('end', '—')} | "
        f"{meta.get('size_mb', '?')} MB（`{ETH_CSV_PATH.name}`）"
    )
else:
    st.warning(
        f"暂无本地 1m 数据（`{ETH_CSV_PATH.name}`）。"
        "请通过顶部导航进入 **有限层级均值回归网格策略回测** 下载行情。"
    )

panel_slot = st.empty()
if not st.session_state.get(_HOME_PANEL_KEY):
    panel_slot.info(
        "交易面板约 450KB，正在准备加载… "
        "若超过 30 秒仍无图表，请刷新页面，并在 Cloud 日志确认已部署 "
        "`static/trading_panel/index.html` 与 `assets/*.js`。"
    )
    st.session_state[_HOME_PANEL_KEY] = True
    st.rerun()

panel_slot.empty()
with st.spinner("正在加载交易面板…"):
    render_trading_panel()
