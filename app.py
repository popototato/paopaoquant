from datetime import date, timedelta

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
from strategy_import import default_steps_df, parse_steps_csv_file, parse_steps_text

st.set_page_config(page_title="泡泡量化回测工具", layout="wide")
st.title("泡泡量化回测工具")

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
if meta and meta.get("start_date"):
    data_min: date = meta["start_date"]
    data_max: date = meta["end_date"]
    today = min(date.today(), data_max)
    year_start = max(data_min, date(today.year, 1, 1))

    if "range_start" not in st.session_state:
        st.session_state.range_start = year_start
    if "range_end" not in st.session_state:
        st.session_state.range_end = data_max

    st.caption(
        f"数据可用范围：**{data_min}** ~ **{data_max}**（北京时间）｜"
        f"回测从「开始日期」当天 **00:00** 起开单"
    )

    q1, q2, q3, q4 = st.columns(4)
    if q1.button("今年", use_container_width=True):
        st.session_state.range_start = year_start
        st.session_state.range_end = data_max
        st.rerun()
    if q2.button("近30天", use_container_width=True):
        st.session_state.range_start = max(data_min, today - timedelta(days=30))
        st.session_state.range_end = data_max
        st.rerun()
    if q3.button("近90天", use_container_width=True):
        st.session_state.range_start = max(data_min, today - timedelta(days=90))
        st.session_state.range_end = data_max
        st.rerun()
    if q4.button("全部数据", use_container_width=True):
        st.session_state.range_start = data_min
        st.session_state.range_end = data_max
        st.rerun()

    # 夹在数据范围内，避免越界
    st.session_state.range_start = max(data_min, min(st.session_state.range_start, data_max))
    st.session_state.range_end = max(
        st.session_state.range_start,
        min(st.session_state.range_end, data_max),
    )

    date_col1, date_col2 = st.columns(2)
    with date_col1:
        backtest_start = st.date_input(
            "开始日期",
            value=st.session_state.range_start,
            min_value=data_min,
            max_value=data_max,
            key="backtest_start",
        )
    with date_col2:
        backtest_end = st.date_input(
            "结束日期",
            value=st.session_state.range_end,
            min_value=backtest_start,
            max_value=data_max,
            key="backtest_end",
        )
    st.session_state.range_start = backtest_start
    st.session_state.range_end = backtest_end
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
    help="操作账户固定总额：盈利划出至外部账户，亏损由外部补足，账户总额保持不变。",
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
    "之后每根 1m K：不利价（多=Low/空=High）按**上一步成交价+下一步间距**补仓并判强平，"
    "有利价按**全仓加权均价+当前最高步止盈距离**止盈，触发当根 K **平仓并同价重开第 1 步**；"
    "已扣 Taker 0.05%。"
)

if "steps_data" not in st.session_state:
    st.session_state.steps_data = default_steps_df()

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
    elif backtest_start and backtest_end and backtest_start > backtest_end:
        st.error("开始日期不能晚于结束日期。")
    elif steps_df.empty:
        st.error("请至少配置一步策略。")
    else:
        layers = [
            LayerStepConfig(
                step=int(row["第几步"]),
                spacing_usdt=float(row["补仓间距"]),
                position_size=float(row["每层仓位"]),
                take_profit_distance=float(row["止盈距离"]),
            )
            for _, row in steps_df.iterrows()
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
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("净盈利", f"{result['净盈利数额']:,.2f} USDT")
        col2.metric("止盈次数", result.get("止盈次数", 0))
        col3.metric("爆仓次数", result["爆仓次数"])
        col4.metric("补仓次数", result.get("补仓次数", 0))

        col5, col6, col7 = st.columns(3)
        col5.metric("毛利盈利", f"{result['盈利数额']:,.2f} USDT")
        col6.metric("毛利亏损", f"{result['亏损数额']:,.2f} USDT")
        col7.metric("手续费", f"{result['手续费合计']:,.2f} USDT")

        st.caption(
            f"回测区间：{result['回测区间']} | "
            f"{result.get('合约杠杆', '')} | "
            f"{result.get('开单方式', '')} | "
            f"{result.get('手续费说明', '')}"
        )

        daily_pnl = result.get("每日盈利", {})
        if daily_pnl and backtest_start and backtest_end:
            st.subheader("每日盈利")
            rows = []
            day = backtest_start
            while day <= backtest_end:
                key = day.isoformat()
                rows.append({"日期": key, "当日净盈利": float(daily_pnl.get(key, 0.0))})
                day += timedelta(days=1)
            chart_df = pd.DataFrame(rows)
            chart_df["累计净盈利"] = chart_df["当日净盈利"].cumsum()

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.caption("每日净盈利（USDT，含手续费）")
                st.bar_chart(chart_df.set_index("日期")[["当日净盈利"]])
            with chart_col2:
                st.caption("累计净盈利（USDT）")
                st.line_chart(chart_df.set_index("日期")[["累计净盈利"]])

        st.json(result)
