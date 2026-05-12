"""
海龟交易策略 — 经典趋势跟踪系统（Richard Dennis 1983）

核心规则:
- 入场: 价格突破20日最高价（唐奇安通道上轨）
- 出场: 价格跌破10日最低价（唐奇安通道下轨）
- 加仓: 每0.5ATR加一次仓（最多4次）
- 止损: 2倍ATR
- 仓位: 基于ATR波动率归一化
"""
import backtrader as bt

from strategies.base_strategy import BaseStrategy


class TurtleStrategy(BaseStrategy):
    """
    海龟交易策略（简化版，单次入场）

    系统1（短期）: 突破20日高点买入，跌破10日低点卖出
    """
    params = (
        ("entry_period", 20),    # 入场通道周期
        ("exit_period", 10),     # 出场通道周期
        ("atr_period", 20),      # ATR计算周期
        ("atr_stop", 2.0),       # ATR止损倍数
    )

    def __init__(self):
        super().__init__()
        self.donchian_high = bt.ind.Highest(self.data.high, period=self.p.entry_period)
        self.donchian_low = bt.ind.Lowest(self.data.low, period=self.p.exit_period)
        self.atr = bt.ind.ATR(period=self.p.atr_period)
        self._stop_price = None   # ATR止损线

    def next(self):
        if self.order:
            return

        if not self.position:
            # 突破N日最高价 → 买入
            if self.data.close[0] >= self.donchian_high[-1]:
                self.order = self.buy()
                self._stop_price = self.data.close[0] - self.p.atr_stop * self.atr[0]
        else:
            # 更新止损线（只上移不下移 — 保护利润）
            current_stop = self.data.close[0] - self.p.atr_stop * self.atr[0]
            if self._stop_price:
                self._stop_price = max(self._stop_price, current_stop)

            # 跌破N日最低价 或 触及止损线 → 卖出
            exit_channel = self.data.close[0] <= self.donchian_low[-1]
            exit_stop = self._stop_price and self.data.close[0] <= self._stop_price

            if (exit_channel or exit_stop) and self.can_sell():
                self.order = self.sell()
                self._stop_price = None
