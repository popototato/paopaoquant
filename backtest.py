from datetime import date

import backtrader as bt

from data import ETH_CSV_PATH, parse_date, to_backtrader_datetime
from fees import FEE_LABEL
from strategy import GridReplenishStrategy, GridStrategyParams


def _load_csv_feed(
    start_date: date | None = None,
    end_date: date | None = None,
) -> bt.feeds.GenericCSVData:
    kwargs: dict = {
        "dataname": str(ETH_CSV_PATH),
        "datetime": 0,
        "open": 1,
        "high": 2,
        "low": 3,
        "close": 4,
        "volume": 5,
        "openinterest": -1,
        "dtformat": "%Y-%m-%d %H:%M:%S",
        "timeframe": bt.TimeFrame.Minutes,
        "compression": 1,
    }
    if start_date is not None:
        kwargs["fromdate"] = to_backtrader_datetime(parse_date(start_date))
    if end_date is not None:
        kwargs["todate"] = to_backtrader_datetime(parse_date(end_date), end_of_day=True)
    return bt.feeds.GenericCSVData(**kwargs)


def run_backtest(
    strategy: GridStrategyParams,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    account = strategy.account_amount
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(max(account * 10, 1_000_000.0))
    cerebro.broker.set_shortcash(True)
    cerebro.broker.setcommission(commission=0.0)

    cerebro.adddata(_load_csv_feed(start_date, end_date))
    cerebro.adddata(_load_csv_feed(start_date, end_date))

    trading_start = to_backtrader_datetime(parse_date(start_date)) if start_date else None

    cerebro.addstrategy(
        GridReplenishStrategy,
        layer_configs=strategy.layers,
        account_amount=account,
        position_unit=strategy.position_unit,
        leverage=strategy.leverage,
        trade_mode=strategy.trade_mode,
        trading_start=trading_start,
    )

    run_result = cerebro.run()
    strat: GridReplenishStrategy = run_result[0]
    stats = strat.get_result_stats()

    max_step = max(layer.step for layer in strategy.layers)
    layer_summary = []
    for layer in strategy.layers:
        item = {
            "第几步": layer.step,
            "补仓间距": layer.spacing_usdt,
            "每层仓位": layer.position_size,
            "止盈距离": layer.take_profit_distance,
        }
        if layer.step == max_step:
            item["强平说明"] = (
                f"多空各自补完第 {max_step} 步后，"
                f"多头再跌 / 空头再涨 {layer.spacing_usdt} USDT 即爆仓"
            )
        layer_summary.append(item)

    range_text = "全部数据"
    if start_date or end_date:
        start_text = str(start_date) if start_date else "最早"
        end_text = str(end_date) if end_date else "最新"
        range_text = f"{start_text} 00:00 ~ {end_text} 23:59（北京时间）"

    result = {
        "回测区间": range_text,
        "K线周期": "1m",
        "账户金额": round(account, 2),
        "手续费说明": FEE_LABEL,
        "策略步骤": layer_summary,
        **stats,
    }
    result["实际开单时间"] = stats.get("开单时间", "—")
    print(result)
    return result
