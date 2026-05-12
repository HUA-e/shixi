"""
止损模块 — 固定止损、ATR动态止损、移动止损
"""
import backtrader as bt


class FixedStop:
    """
    固定比例止损 — 买入价格下跌超过指定百分比即卖出

    用法（在策略 next 中）:
        self.fixed_stop = FixedStop(self, percent=0.05)
        ...
        if self.fixed_stop.should_exit():
            self.order = self.sell()
    """

    def __init__(self, strategy, percent=0.05):
        self.strategy = strategy
        self.percent = percent
        self._entry_price = None

    def record_entry(self, price=None):
        self._entry_price = price or self.strategy.data.close[0]

    def should_exit(self):
        if self._entry_price is None or not self.strategy.position:
            return False
        current = self.strategy.data.close[0]
        return (current - self._entry_price) / self._entry_price <= -self.percent

    def reset(self):
        self._entry_price = None


class ATRStop:
    """
    ATR动态止损 — 以买入价减去N倍ATR作为止损线，随价格上涨上移

    用法:
        self.atr_stop = ATRStop(self, atr_period=14, multiplier=2.0)
        ...
        self.atr_stop.record_entry()
        if self.atr_stop.should_exit():
            self.order = self.sell()
    """

    def __init__(self, strategy, atr_period=14, multiplier=2.0):
        self.s = strategy
        self.multiplier = multiplier
        self.atr = bt.ind.ATR(strategy.data, period=atr_period)
        self._stop_price = None

    def record_entry(self, price=None):
        entry = price or self.s.data.close[0]
        self._stop_price = entry - self.multiplier * self.atr[0]

    def should_exit(self):
        if self._stop_price is None or not self.s.position:
            return False

        # 止损线随价格上涨而上移（移动止损）
        current_atr_stop = self.s.data.close[0] - self.multiplier * self.atr[0]
        self._stop_price = max(self._stop_price, current_atr_stop)

        return self.s.data.close[0] <= self._stop_price

    def reset(self):
        self._stop_price = None


class TrailingStop:
    """
    移动止损 — 从最高点回撤超过指定百分比即卖出

    用法:
        self.trail_stop = TrailingStop(self, percent=0.08)
        ...
        self.trail_stop.record_entry()
        if self.trail_stop.should_exit():
            self.order = self.sell()
    """

    def __init__(self, strategy, percent=0.08):
        self.s = strategy
        self.percent = percent
        self._peak = None

    def record_entry(self, price=None):
        self._peak = price or self.s.data.close[0]

    def should_exit(self):
        if self._peak is None or not self.s.position:
            return False

        current = self.s.data.close[0]
        self._peak = max(self._peak, current)
        return (current - self._peak) / self._peak <= -self.percent

    def reset(self):
        self._peak = None
