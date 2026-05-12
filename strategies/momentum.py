"""
动量策略 — 基于N日价格突破的趋势跟踪策略
"""
import backtrader as bt

from strategies.base_strategy import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """
    动量策略:
    - 价格突破N日新高且当前价在MA上方 → 买入
    - 跌破N日低点或移动止损触发 → 卖出
    """
    params = (
        ("lookback", 20),
        ("ma_period", 60),
        ("trail_pct", 0.06),
    )

    def __init__(self):
        super().__init__()
        self.ma = bt.ind.SMA(period=self.p.ma_period)
        self.highest = bt.ind.Highest(self.data.high, period=self.p.lookback)
        self.lowest = bt.ind.Lowest(self.data.low, period=self.p.lookback)
        self._peak = None

    def next(self):
        if self.order:
            return

        # 确保指标已就绪（有足够的历史数据）
        if len(self) < max(self.p.lookback, self.p.ma_period):
            return

        if not self.position:
            # 收盘价突破N日最高价 且 在MA上方 → 买入
            if (self.data.close[0] >= self.highest[0]
                    and self.data.close[0] > self.ma[0]):
                self.order = self.buy()
                self._peak = self.data.close[0]
        else:
            if self._peak:
                self._peak = max(self._peak, self.data.close[0])

            # 跌破N日最低价 或 移动止损触发 → 卖出
            exit_channel = self.data.close[0] <= self.lowest[0]
            trail_hit = (self._peak and
                         (self.data.close[0] - self._peak) / self._peak <= -self.p.trail_pct)

            if (exit_channel or trail_hit) and self.can_sell():
                self.order = self.sell()
                self._peak = None
