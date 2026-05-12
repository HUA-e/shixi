"""
双均线金叉死叉策略 — 最经典的入门趋势跟踪策略
"""

import backtrader as bt

from strategies.base_strategy import BaseStrategy
from config import MA_CROSS_FAST, MA_CROSS_SLOW


class MACrossStrategy(BaseStrategy):
    """
    双均线策略:
    - 短期均线上穿长期均线（金叉）→ 全仓买入
    - 短期均线下穿长期均线（死叉）→ 全部卖出
    - 受 T+1 约束：当日买入次日才能卖出
    """
    params = (
        ("fast", MA_CROSS_FAST),
        ("slow", MA_CROSS_SLOW),
    )

    def __init__(self):
        super().__init__()
        self.sma_fast = bt.ind.SMA(period=self.p.fast)
        self.sma_slow = bt.ind.SMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.sma_fast, self.sma_slow)

    def next(self):
        if self.order:
            return  # 有未成交订单，等待

        if not self.position:
            if self.crossover > 0:          # 金叉 → 买入
                self.order = self.buy()
        else:
            if self.crossover < 0 and self.can_sell():  # 死叉 → 卖出
                self.order = self.sell()
