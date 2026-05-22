"""泡泡量化 · 入口（顶部导航）。"""

import streamlit as st

st.set_page_config(
    page_title="泡泡量化",
    page_icon="🫧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
.block-container {
    padding-top: 0.5rem;
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

home_page = st.Page("home_page.py", title="首页", default=True, icon="🫧")
backtest_page = st.Page(
    "backtest_page.py",
    title="有限层级均值回归网格策略回测",
    icon="📊",
)

pg = st.navigation([home_page, backtest_page], position="top")
pg.run()
