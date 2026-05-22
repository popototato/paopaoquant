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
    - 之后每根 K：**先**判有利价止盈（多=High/空=Low），触发则平仓并同价重开第 1 步
    - 未止盈时：用不利价（多=Low/空=High）相对**第 1 步入场价**的累计间距推断当前第几步，
      将层数补至推断步（单根 K 可一次追上多步），再判强平
    - 止盈：全仓加权均价 + **当前最高步**止盈距离
    - 强平：补满全部步数后，相对最后一步入场价再偏移最大步间距；触发价平仓并同价重开第 1 步
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

    def _resync_ghost_leg(self, data, is_long: bool) -> None:
        """内部 layers>0 但经纪商持仓已空：用当前价重开第 1 步（极少见）。"""
        if self._layers(is_long) <= 0 or self.getposition(data).size != 0:
            return
        px = self._sim_price or float(data.close[0])
        self._clear_leg_state(is_long)
        self._open_initial_leg(data, is_long=is_long, entry_price=px)

    def _sync_leg_before_bar(self, data, is_long: bool) -> None:
        self._resync_ghost_leg(data, is_long)

    def _process_bar(self, data, is_long: bool) -> None:
        high = float(data.high[0])
        low = float(data.low[0])
        adverse = low if is_long else high
        favorable = high if is_long else low

        self._sync_leg_before_bar(data, is_long)

        # Phase 1：有利侧 — 止盈则当根 K 平仓并同价重开第 1 步（本根不再补仓）
        self._sim_price = favorable
        if self._try_take_profit(data, is_long):
            return

        # Phase 2：不利侧 — 相对第 1 步价累计间距推断步数并补仓，再判强平
        self._sim_price = adverse
        self._sync_replenish_to_inferred_step(data, is_long, adverse)
        self._try_liquidation(data, is_long)

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

    def _step1_entry(self, is_long: bool) -> float | None:
        """第 1 步入场价（锚点）；止盈重开后更新。"""
        entry = self._step_entries(is_long).get(1)
        if entry is not None:
            return entry
        return self._anchor(is_long)

    def _last_step_entry(self, is_long: bool) -> float | None:
        """当前最高步成交价（强平基准）。"""
        layers = self._layers(is_long)
        if layers <= 0:
            return None
        entry = self._step_entries(is_long).get(layers)
        if entry is not None:
            return entry
        return self._anchor(is_long)

    def _cumulative_spacing_from_step1(self, through_step: int) -> float:
        """自第 1 步起至 through_step 的累计补仓间距（不含第 1 步自身间距）。"""
        total = 0.0
        for step in range(2, through_step + 1):
            total += self._config_for_step(step).spacing_usdt
        return total

    def _adverse_threshold_for_step(self, is_long: bool, step: int) -> float | None:
        """相对第 1 步价，推断「已达第 step 步」的不利侧阈值。"""
        step1 = self._step1_entry(is_long)
        if step1 is None or step < 1:
            return None
        if step == 1:
            return step1
        offset = self._cumulative_spacing_from_step1(step)
        return step1 - offset if is_long else step1 + offset

    def _infer_step_from_step1(self, is_long: bool, adverse: float) -> int:
        """由不利价相对第 1 步价的累计间距推断当前应处于第几步（至少 1）。"""
        if self._layers(is_long) <= 0 or self._step1_entry(is_long) is None:
            return 0
        inferred = 1
        for step in range(2, self._max_layers() + 1):
            threshold = self._adverse_threshold_for_step(is_long, step)
            if threshold is None:
                break
            if is_long:
                if adverse <= threshold:
                    inferred = step
            elif adverse >= threshold:
                inferred = step
        return inferred

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

    def _add_daily(self, amount: float, bar_dt: datetime) -> None:
        if not self._trading_started:
            return
        day = bar_dt.strftime("%Y-%m-%d")
        self.daily_pnl[day] = self.daily_pnl.get(day, 0.0) + amount

    def _net_pnl(self) -> float:
        return self.total_profit - self.total_loss - self.total_fees

    def _remaining_equity(self) -> float:
        """相对 -account_amount 底线的剩余可亏额度（含手续费）。"""
        return self.p.account_amount + self._net_pnl()

    def _cap_liquidation_loss(self, pnl: float) -> float:
        """单笔爆仓亏损不超过剩余本金，累计净盈亏不低于 -account_amount。"""
        if pnl >= 0:
            return pnl
        budget = self._remaining_equity()
        if budget <= 0:
            return 0.0
        return -min(abs(pnl), budget)

    def _record_pnl(
        self, pnl: float, is_liquidation: bool = False, *, bar_dt: datetime
    ) -> None:
        if is_liquidation:
            self.liquidation_count += 1
            pnl = self._cap_liquidation_loss(pnl)
        if pnl >= 0:
            self.total_profit += pnl
        else:
            self.total_loss += abs(pnl)
        self._add_daily(pnl, bar_dt)

    def _charge_fee(
        self,
        data,
        size: float,
        price: float,
        *,
        bar_dt: datetime | None = None,
        max_charge: float | None = None,
    ) -> float:
        fee = calc_trade_fee(price, size, DEFAULT_FEE_RATE)
        if max_charge is not None:
            fee = min(fee, max(0.0, max_charge))
        self.total_fees += fee
        dt = bar_dt if bar_dt is not None else self._bar_datetime(data)
        self._add_daily(-fee, dt)
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
    ) -> None:
        pos = self.getposition(data)
        if pos.size == 0 and self._layers(is_long) <= 0:
            return
        size = abs(pos.size)
        if size > 0:
            bar_dt = self._bar_datetime(data)
            pnl = self._leg_pnl(pos, exit_price, is_long)
            if is_liquidation:
                budget = self._remaining_equity()
                fee = self._charge_fee(
                    data, size, exit_price, bar_dt=bar_dt, max_charge=budget
                )
                budget = max(0.0, budget - fee)
                if pnl < 0:
                    pnl = -min(abs(pnl), budget)
            else:
                self._charge_fee(data, size, exit_price, bar_dt=bar_dt)
            self.close(data=data)
            self._record_pnl(pnl, is_liquidation=is_liquidation, bar_dt=bar_dt)
        self._clear_leg_state(is_long)

    def _try_liquidation(self, data, is_long: bool) -> bool:
        if self._layers(is_long) < self._max_layers():
            return False
        cfg = self._config_for_step(self._max_layers())
        ref = self._last_step_entry(is_long)
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
                )
                self._open_initial_leg(data, is_long=True, entry_price=trigger)
                return True
        else:
            trigger = ref + cfg.spacing_usdt
            if px >= trigger:
                self._close_leg(
                    data,
                    is_long=False,
                    exit_price=trigger,
                    is_liquidation=True,
                )
                self._open_initial_leg(data, is_long=False, entry_price=trigger)
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

    def _open_replenish_layer(self, data, is_long: bool, step: int, entry_price: float) -> None:
        cfg = self._config_for_step(step)
        size = self._eth_size(data, cfg.position_size, price=entry_price)
        if is_long:
            self._buy(data, size, entry_price)
            self._set_layers(True, step)
            self._record_step_entry(True, step, entry_price)
        else:
            self._sell(data, size, entry_price)
            self._set_layers(False, step)
            self._record_step_entry(False, step, entry_price)
        self.replenish_count += 1

    def _sync_replenish_to_inferred_step(self, data, is_long: bool, adverse: float) -> None:
        """未止盈时：按第 1 步价累计间距推断步数，补至推断步（单根可追多步）。"""
        current = self._layers(is_long)
        if current <= 0:
            return
        inferred = self._infer_step_from_step1(is_long, adverse)
        if inferred <= current:
            return
        target = min(inferred, self._max_layers())
        for step in range(current + 1, target + 1):
            trigger = self._adverse_threshold_for_step(is_long, step)
            if trigger is None:
                break
            self._open_replenish_layer(data, is_long, step, trigger)
