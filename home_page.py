import streamlit as st

from chart_component import render_trading_panel
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

render_trading_panel()
