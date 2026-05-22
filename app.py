"""泡泡量化 · 入口（顶部导航）。"""

import streamlit as st

st.set_page_config(
    page_title="泡泡量化",
    page_icon="🫧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if not hasattr(st, "Page") or not hasattr(st, "navigation"):
    st.error(
        f"**Streamlit 版本过低**（当前 `{st.__version__}`）。\n\n"
        "本应用使用 `st.Page` / `st.navigation`，需要 **streamlit ≥ 1.36.0**。\n\n"
        "请在仓库根目录 `requirements.txt` 中设置 `streamlit>=1.36.0`（推荐 `>=1.57,<1.58`），"
        "推送到 GitHub 后在 Cloud **Reboot app** 或等待自动重新部署。"
    )
    st.stop()

st.markdown(
    """
<style>
/* Top st.navigation bar is fixed ~3rem; keep main content below it (local + Cloud). */
.block-container,
[data-testid="stAppViewContainer"] [data-testid="stMain"] .block-container,
[data-testid="stMainBlockContainer"] {
    padding-top: 3.75rem;
    padding-bottom: 0.5rem;
    padding-left: 1rem;
    padding-right: 1rem;
    max-width: 100%;
}
section.main > div {
    padding-left: 0;
    padding-right: 0;
}
.stApp,
section.main,
[data-testid="stAppViewContainer"] {
    background-color: #131722;
}
[data-testid="stHeader"] {
    background-color: #131722 !important;
    border-bottom: 1px solid #2a2e39;
}
div[data-testid="stVerticalBlock"] > div:has(iframe) {
    width: 100%;
    background: #131722 !important;
}
iframe {
    width: 100% !important;
    background: #131722 !important;
    border: none;
    display: block;
}
div[data-testid="stHtml"] {
    background: #131722;
}
</style>
""",
    unsafe_allow_html=True,
)

try:
    home_page = st.Page("home_page.py", title="首页", default=True, icon="🫧")
    backtest_page = st.Page(
        "backtest_page.py",
        title="有限层级均值回归网格策略回测",
        icon="📊",
    )

    pg = st.navigation([home_page, backtest_page], position="top")
    pg.run()
except Exception as exc:
    st.error("应用启动失败。请展开下方错误信息，或在 Cloud **Manage app → Logs** 查看完整堆栈。")
    st.exception(exc)
