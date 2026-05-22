import streamlit as st

from chart_component import (
    TRADING_PANEL_STATIC_PATH,
    _trading_panel_iframe_src,
    _trading_panel_static_diagnostics,
    render_trading_panel,
)
from data import ETH_CSV_PATH, get_csv_info

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

panel_url = _trading_panel_iframe_src()
st.markdown(
    f"**面板静态页测试**（Streamlit 运行中可点）：[打开交易面板]({panel_url})"
)

panel_issues = _trading_panel_static_diagnostics()
if panel_issues:
    st.error("首页图表依赖的静态交易面板未就绪：" + "；".join(panel_issues))
    st.caption(
        f"部署后请确认可访问：`{panel_url}` "
        f"（路径 `{TRADING_PANEL_STATIC_PATH}`）。"
        "本地修复：`cd frontend && npm run build`，然后提交 `static/trading_panel/`。"
    )
else:
    render_trading_panel()
