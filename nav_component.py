"""顶部水平导航（首页 / 策略回测）。"""

from __future__ import annotations

import streamlit as st

NAV_ITEMS: list[tuple[str, str]] = [
    ("首页", "app.py"),
    ("有限层级均值回归网格策略回测", "pages/1_grid_backtest.py"),
]

_NAV_CSS = """
<style>
div[data-testid="stHorizontalBlock"]:has(button[kind="primary"]) {
    gap: 0.5rem;
}
.paopao-top-nav {
    border-bottom: 1px solid rgba(49, 51, 63, 0.15);
    margin-bottom: 0.75rem;
    padding-bottom: 0.25rem;
}
</style>
"""


def render_top_nav(current_page: str) -> None:
    """渲染顶部导航栏；current_page 为当前页面路径（与 NAV_ITEMS 中一致）。"""
    st.markdown(_NAV_CSS, unsafe_allow_html=True)
    st.markdown('<div class="paopao-top-nav"></div>', unsafe_allow_html=True)

    cols = st.columns(len(NAV_ITEMS))
    for col, (label, page_path) in zip(cols, NAV_ITEMS):
        with col:
            is_current = page_path == current_page
            if is_current:
                st.button(label, disabled=True, use_container_width=True, key=f"nav_cur_{page_path}")
            elif st.button(label, use_container_width=True, key=f"nav_go_{page_path}"):
                st.switch_page(page_path)

    st.markdown("")
