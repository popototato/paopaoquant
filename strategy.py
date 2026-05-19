from dataclasses import dataclass
from datetime import datetime

import backtrader as bt

from fees import DEFAULT_FEE_RATE, calc_trade_fee


@dataclass
class LayerStepConfig:
    step: int
    spacing_usdt: float
    position_size: float  # ETH 数量
    take_profit_distance: float


@dataclass
class GridStrategyParams:
    layers: list[LayerStepConfig]
    account_amount: float
    position_unit: str = "eth"
    leverage: int = 100
    trade_mode: str = "dual"  # dual | long_only | short_only


def create_strategy(
    layers: list[LayerStepConfig],
    account_amount: float,
    position_unit: str = "eth",
    leverage: int = 100,
    trade_mode: str = "dual",
) -> GridStrategyParams:
    sorted_layers = sorted(layers, key=lambda x: x.step)
    return GridStrategyParams(
        layers=sorted_layers,
        account_amount=account_amount,
        position_unit=position_unit,
        leverage=max(1, int(leverage)),
        trade_mode=trade_mode,
    )


class GridReplenishStrategy(bt.Strategy):
    """
    分批补仓（ETH 数量开单），逐根 1m K 线推进：

    - 开始日北京时间 00:00 首根 K：多空各开第 1 步
    - 每根 K：不利价（多=Low/空=High）先按上一步入场价 + 下一步间距补仓，再判强平
    - 有利价（多=High/空=Low）按全仓加权均价 + 当前最高步止盈距离止盈；
      触发止盈当根 K 在触发价平全腿并立即重开第 1 步
    - 强平：补满全部步数后，相对最后一步入场价再偏移最大步间距
    """

    params = (
        ("layer_configs", None),
        ("account_amount", 100_000.0),
        ("position_unit", "eth"),
        ("leverage", 100),
        ("trade_mode", "dual"),
        ("trading_start", None),
    )

    def __init__(self):
        self.long_data = self.datas[0]
        self.short_data = self.datas[1]
        self.long_layers = 0
        self.short_layers = 0
        self.long_anchor = None
        self.short_anchor = None
        self.long_step_entry: dict[int, float] = {}
        self.short_step_entry: dict[int, float] = {}

        self.total_profit = 0.0
        self.total_loss = 0.0
        self.total_fees = 0.0
        self.liquidation_count = 0
        self.take_profit_count = 0
        self.replenish_count = 0
        self._sim_price = 0.0
        self._trading_started = False
        self.actual_open_time: str | None = None
        self.daily_pnl: dict[str, float] = {}
        self._pending_reopen_long: float | None = None
        self._pending_reopen_short: float | None = None

    def start(self):
        self._configs = list(self.p.layer_configs)

    def _bar_datetime(self, data) -> datetime:
        return data.datetime.datetime(0)

    def _ensure_trading_started(self) -> bool:
        """跳过开始日之前 K 线；开始日 00:00 首根 K 多空各开第 1 步。"""
        if self._trading_started:
            return True
        if not self._configs:
            return False

        bar_dt = self._bar_datetime(self.long_data)
        if self.p.trading_start is not None and bar_dt < self.p.trading_start:
            return False

        self._sim_price = float(self.long_data.open[0])
        if self.p.trade_mode in ("dual", "long_only"):
            self._open_initial_leg(self.long_data, is_long=True, entry_price=self._sim_price)
        if self.p.trade_mode in ("dual", "short_only"):
            px = float(self.short_data.open[0])
            self._open_initial_leg(self.short_data, is_long=False, entry_price=px)

        self._trading_started = True
        self.actual_open_time = bar_dt.strftime("%Y-%m-%d %H:%M:%S")
        return True

    def next(self):
        if not self._configs:
            return
        if not self._ensure_trading_started():
            return
        if self.p.trade_mode in ("dual", "long_only"):
            self._process_bar(self.long_data, is_long=True)
        if self.p.trade_mode in ("dual", "short_only"):
            self._process_bar(self.short_data, is_long=False)

    def _pending_reopen(self, is_long: bool) -> float | None:
        return self._pending_reopen_long if is_long else self._pending_reopen_short

    def _set_pending_reopen(self, is_long: bool, price: float | None) -> None:
        if is_long:
            self._pending_reopen_long = price
        else:
            self._pending_reopen_short = price

    def _try_pending_reopen(self, data, is_long: bool) -> None:
        entry = self._pending_reopen(is_long)
        if entry is None or self._layers(is_long) > 0:
            return
        if self.getposition(data).size != 0:
            return
        self._open_initial_leg(data, is_long=is_long, entry_price=entry)
        self._set_pending_reopen(is_long, None)

    def _resync_ghost_leg(self, data, is_long: bool) -> None:
        """内部 layers>0 但经纪商持仓已空：用当前价重开第 1 步（极少见）。"""
        if self._pending_reopen(is_long) is not None:
            return
        if self._layers(is_long) <= 0 or self.getposition(data).size != 0:
            return
        px = self._sim_price or float(data.close[0])
        self._clear_leg_state(is_long)
        self._open_initial_leg(data, is_long=is_long, entry_price=px)

    def _sync_leg_before_bar(self, data, is_long: bool) -> None:
        self._try_pending_reopen(data, is_long)
        self._resync_ghost_leg(data, is_long)

    def _process_bar(self, data, is_long: bool) -> None:
        high = float(data.high[0])
        low = float(data.low[0])
        adverse = low if is_long else high
        favorable = high if is_long else low

        self._sync_leg_before_bar(data, is_long)

        # Phase 1：不利侧 — 相对上一步入场价逐层补仓，再判强平
        self._sim_price = adverse
        while self._try_replenish(data, is_long):
            pass
        self._try_liquidation(data, is_long)

        # Phase 2：有利侧 — 止盈则当根 K 平仓并同价重开第 1 步
        self._sim_price = favorable
        self._try_take_profit(data, is_long)

    def get_result_stats(self) -> dict:
        net = self.total_profit - self.total_loss - self.total_fees
        return {
            "爆仓次数": self.liquidation_count,
            "止盈次数": self.take_profit_count,
            "补仓次数": self.replenish_count,
            "盈利数额": round(self.total_profit, 2),
            "亏损数额": round(self.total_loss, 2),
            "手续费合计": round(self.total_fees, 2),
            "净盈利数额": round(net, 2),
            "合约杠杆": f"{self.p.leverage}x",
            "开单方式": f"ETH 数量（{self.p.leverage}x）",
            "交易模式": self.p.trade_mode,
            "开单时间": self.actual_open_time or "—",
            "每日盈利": dict(sorted(self.daily_pnl.items())),
        }

    def _config_for_step(self, step: int) -> LayerStepConfig:
        idx = min(step - 1, len(self._configs) - 1)
        return self._configs[idx]

    def _max_layers(self) -> int:
        return len(self._configs)

    def _layers(self, is_long: bool) -> int:
        return self.long_layers if is_long else self.short_layers

    def _set_layers(self, is_long: bool, value: int) -> None:
        if is_long:
            self.long_layers = value
        else:
            self.short_layers = value

    def _anchor(self, is_long: bool) -> float | None:
        return self.long_anchor if is_long else self.short_anchor

    def _set_anchor(self, is_long: bool, price: float) -> None:
        if is_long:
            self.long_anchor = price
        else:
            self.short_anchor = price

    def _replenish_ref_price(self, is_long: bool) -> float | None:
        """补仓间距基准 = 当前最高步（上一步）的成交价。"""
        layers = self._layers(is_long)
        if layers <= 0:
            return None
        entry = self._step_entries(is_long).get(layers)
        if entry is not None:
            return entry
        return self._anchor(is_long)

    def _step_entries(self, is_long: bool) -> dict[int, float]:
        return self.long_step_entry if is_long else self.short_step_entry

    def _record_step_entry(self, is_long: bool, step: int, price: float) -> None:
        self._step_entries(is_long)[step] = price

    def _clear_step_entries(self, is_long: bool) -> None:
        self._step_entries(is_long).clear()

    def _clear_leg_state(self, is_long: bool) -> None:
        self._set_layers(is_long, 0)
        self._clear_step_entries(is_long)
        if is_long:
            self.long_anchor = None
        else:
            self.short_anchor = None

    def _position_avg_price(self, data, is_long: bool) -> float | None:
        layers = self._layers(is_long)
        if layers <= 0:
            return None
        entries = self._step_entries(is_long)
        total_value = 0.0
        total_size = 0.0
        for step in range(1, layers + 1):
            price = entries.get(step)
            if price is None:
                continue
            cfg = self._config_for_step(step)
            size = self._eth_size(data, cfg.position_size, price=price)
            total_value += price * size
            total_size += size
        if total_size <= 0:
            return None
        return total_value / total_size

    def _eth_size(self, data, amount: float, price: float | None = None) -> float:
        if self.p.position_unit == "eth":
            return amount
        px = price if price is not None else (self._sim_price or float(data.close[0]))
        if px <= 0:
            return 0.0
        return (amount * self.p.leverage) / px

    def _add_daily(self, amount: float) -> None:
        if not self._trading_started:
            return
        day = self._bar_datetime(self.long_data).strftime("%Y-%m-%d")
        self.daily_pnl[day] = self.daily_pnl.get(day, 0.0) + amount

    def _record_pnl(self, pnl: float, is_liquidation: bool = False) -> None:
        if is_liquidation:
            self.liquidation_count += 1
        if pnl >= 0:
            self.total_profit += pnl
        else:
            self.total_loss += abs(pnl)
        self._add_daily(pnl)

    def _charge_fee(self, data, size: float, price: float) -> float:
        fee = calc_trade_fee(price, size, DEFAULT_FEE_RATE)
        self.total_fees += fee
        self._add_daily(-fee)
        return fee

    def _buy(self, data, size: float, price: float) -> None:
        if size <= 0:
            return
        self._charge_fee(data, size, price)
        self.buy(data=data, size=size)

    def _sell(self, data, size: float, price: float) -> None:
        if size <= 0:
            return
        self._charge_fee(data, size, price)
        self.sell(data=data, size=size)

    def _leg_pnl(self, pos, exit_price: float, is_long: bool) -> float:
        size = abs(pos.size)
        if is_long:
            return (exit_price - pos.price) * size
        return (pos.price - exit_price) * size

    def _close_leg(
        self,
        data,
        is_long: bool,
        exit_price: float,
        is_liquidation: bool,
        *,
        pending_reopen: bool = False,
    ) -> None:
        pos = self.getposition(data)
        if pos.size == 0 and self._layers(is_long) <= 0:
            return
        size = abs(pos.size)
        if size > 0:
            pnl = self._leg_pnl(pos, exit_price, is_long)
            self._charge_fee(data, size, exit_price)
            self.close(data=data)
            self._record_pnl(pnl, is_liquidation=is_liquidation)
        self._clear_leg_state(is_long)
        if pending_reopen:
            self._set_pending_reopen(is_long, exit_price)

    def _try_liquidation(self, data, is_long: bool) -> bool:
        if self._layers(is_long) < self._max_layers():
            return False
        cfg = self._config_for_step(self._max_layers())
        ref = self._replenish_ref_price(is_long)
        if ref is None:
            return False
        px = self._sim_price
        if is_long:
            trigger = ref - cfg.spacing_usdt
            if px <= trigger:
                self._close_leg(
                    data,
                    is_long=True,
                    exit_price=trigger,
                    is_liquidation=True,
                    pending_reopen=True,
                )
                return True
        else:
            trigger = ref + cfg.spacing_usdt
            if px >= trigger:
                self._close_leg(
                    data,
                    is_long=False,
                    exit_price=trigger,
                    is_liquidation=True,
                    pending_reopen=True,
                )
                return True
        return False

    def _try_take_profit(self, data, is_long: bool) -> bool:
        if self._layers(is_long) <= 0:
            return False

        current_step = self._layers(is_long)
        cfg = self._config_for_step(current_step)
        avg = self._position_avg_price(data, is_long)
        if avg is None:
            pos = self.getposition(data)
            if pos.size != 0:
                avg = float(pos.price)
            else:
                return False

        px = self._sim_price
        if is_long:
            target = avg + cfg.take_profit_distance
            if px < target:
                return False
            self.take_profit_count += 1
            self._close_leg(data, is_long=True, exit_price=target, is_liquidation=False)
            self._open_initial_leg(data, is_long=True, entry_price=target)
            return True

        target = avg - cfg.take_profit_distance
        if px > target:
            return False
        self.take_profit_count += 1
        self._close_leg(data, is_long=False, exit_price=target, is_liquidation=False)
        self._open_initial_leg(data, is_long=False, entry_price=target)
        return True

    def _open_initial_leg(self, data, is_long: bool, entry_price: float | None = None) -> None:
        """开第 1 步；以内部 layers==0 为准（止盈当根 K 可立即重开）。"""
        if self._layers(is_long) > 0:
            return
        first = self._config_for_step(1)
        px = entry_price if entry_price is not None else (self._sim_price or float(data.close[0]))
        size = self._eth_size(data, first.position_size, price=px)
        if is_long:
            self._buy(data, size, px)
            self._set_layers(True, 1)
            self._set_anchor(True, px)
            self._record_step_entry(True, 1, px)
        else:
            self._sell(data, size, px)
            self._set_layers(False, 1)
            self._set_anchor(False, px)
            self._record_step_entry(False, 1, px)

    def _try_replenish(self, data, is_long: bool) -> bool:
        if self._layers(is_long) >= self._max_layers():
            return False
        next_step = self._layers(is_long) + 1
        cfg = self._config_for_step(next_step)
        ref = self._replenish_ref_price(is_long)
        if ref is None:
            return False
        px = self._sim_price

        if is_long:
            trigger = ref - cfg.spacing_usdt
            if px > trigger:
                return False
            size = self._eth_size(data, cfg.position_size, price=trigger)
            self._buy(data, size, trigger)
            self._set_layers(True, next_step)
            self._set_anchor(True, trigger)
            self._record_step_entry(True, next_step, trigger)
            self.replenish_count += 1
            return True

        trigger = ref + cfg.spacing_usdt
        if px < trigger:
            return False
        size = self._eth_size(data, cfg.position_size, price=trigger)
        self._sell(data, size, trigger)
        self._set_layers(False, next_step)
        self._set_anchor(False, trigger)
        self._record_step_entry(False, next_step, trigger)
        self.replenish_count += 1
        return True
