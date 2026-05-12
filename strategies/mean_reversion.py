"""
均值回归策略 — 布林带 + RSI 过滤
"""
import backtrader as bt

from strategies.base_strategy import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """
    布林带均值回归:
    - 价格触及/跌破下轨 且 RSI < 30（超卖）→ 买入
    - 价格触及/突破上轨 或 RSI > 70（超买）→ 卖出
    """
    params = (
        ("bb_period", 20),     # 布林带周期
        ("bb_dev", 2.0),       # 布林带标准差倍数
        ("rsi_period", 14),    # RSI周期
        ("rsi_oversold", 30),  # RSI超卖阈值
        ("rsi_overbought", 70),# RSI超买阈值
    )

    def __init__(self):
        super().__init__()
        self.bb = bt.ind.BollingerBands(period=self.p.bb_period, devfactor=self.p.bb_dev)
        self.rsi = bt.ind.RSI(period=self.p.rsi_period)

    def next(self):
        if self.order:
            return

        if not self.position:
            # 价格触及下轨 且 RSI超卖 → 买入
            if (self.data.close[0] <= self.bb.lines.bot[0]
                    and self.rsi[0] < self.p.rsi_oversold):
                self.order = self.buy()
        else:
            # 价格突破上轨 或 RSI超买 → 卖出
            exit_upper = self.data.close[0] >= self.bb.lines.top[0]
            exit_rsi = self.rsi[0] > self.p.rsi_overbought

            if (exit_upper or exit_rsi) and self.can_sell():
                self.order = self.sell()
