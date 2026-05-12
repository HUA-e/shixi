"""
仓位管理 — 百分比仓位、ATR波动调整仓位、凯利公式

backtrader 的 Sizer 在每次买入时被调用，决定买入多少股。
"""
import backtrader as bt


class PercentSizer(bt.Sizer):
    """
    按账户总值的百分比买入（向下取整到100股）
    这是 backtrader 内置 PercentSizer 的增强版，确保整数手
    """
    params = (("percents", 95),)

    def _getsizing(self, comminfo, cash, data, isbuy):
        if not isbuy:
            return self.broker.getposition(data).size  # 卖出全部

        size = (cash * self.p.percents / 100) / data.close[0]
        lots = int(size / 100) * 100  # A股必须是100股整数倍
        return max(lots, 100)         # 至少买1手


class ATRSizer(bt.Sizer):
    """
    基于ATR波动率调整仓位大小 — 高波动时减仓、低波动时加仓

    公式: 仓位 = 账户总值 * 风险比例 / (ATR * 乘数)
          然后 × 当前价格 / 每手股数 → 向下取整到100股

    params:
        risk_percent: 每笔交易愿意承担的风险比例
        atr_period:   ATR计算周期
        atr_mult:     ATR乘数
    """
    params = (
        ("risk_percent", 2),  # 每笔交易风险2%
        ("atr_period", 14),
        ("atr_mult", 2.0),
    )

    def __init__(self):
        self.atr = {}

    def _getsizing(self, comminfo, cash, data, isbuy):
        if not isbuy:
            return self.broker.getposition(data).size

        if data not in self.atr:
            self.atr[data] = bt.ind.ATR(data, period=self.p.atr_period)

        atr_val = self.atr[data][0]
        if atr_val == 0:
            atr_val = data.close[0] * 0.01  # 兜底：ATR为0默认波动1%

        risk_amount = cash * (self.p.risk_percent / 100)
        stop_distance = self.p.atr_mult * atr_val
        shares = risk_amount / stop_distance
        lots = int(shares / 100) * 100

        return max(lots, 100)


class KellySizer(bt.Sizer):
    """
    凯利公式仓位 — 根据历史胜率和盈亏比计算最优仓位

    公式: f = (bp - q) / b
          b = 平均盈利 / 平均亏损（盈亏比）
          p = 胜率, q = 1 - p

    默认使用保守凯利（half-Kelly），即仓位减半
    """
    params = (
        ("win_rate", 0.4),        # 默认胜率40%
        ("profit_loss_ratio", 2.0),  # 默认盈亏比2:1
        ("half_kelly", True),     # 使用半凯利降低风险
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        if not isbuy:
            return self.broker.getposition(data).size

        b = self.p.profit_loss_ratio
        p = self.p.win_rate
        q = 1 - p

        kelly = (b * p - q) / b
        kelly = max(kelly, 0.05)  # 至少5%
        kelly = min(kelly, 0.50)  # 至多50%

        if self.p.half_kelly:
            kelly /= 2

        size = (cash * kelly) / data.close[0]
        lots = int(size / 100) * 100
        return max(lots, 100)
