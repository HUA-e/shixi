"""
A股费率 — 佣金 + 卖出印花税，符合A股实际交易成本
"""
import backtrader as bt

from config import COMMISSION, STAMP_DUTY, MIN_COMMISSION


class AStockCommission(bt.CommInfoBase):
    """
    A股实际费率:
    - 买入: 佣金 万分之2.5（最低5元）
    - 卖出: 佣金 万分之2.5 + 印花税 万分之5（最低5元佣金）
    """
    params = (
        ("commission", COMMISSION),     # 佣金费率
        ("stamp_duty", STAMP_DUTY),     # 印花税费率（仅卖出）
        ("min_commission", MIN_COMMISSION),  # 最低佣金
        ("stocklike", True),           # 股票模式（非期货）
        ("commtype", bt.CommInfoBase.COMM_PERC),  # 按百分比计算
        ("stamp_duty_fixed", False),    # 印花税也按百分比
    )

    def _getcommission(self, size, price, pseudoexec):
        """
        计算实际交易费用。backtrader 调用此方法。
        size > 0 = 买入, size < 0 = 卖出
        """
        value = abs(size) * price
        commission = max(value * self.p.commission, self.p.min_commission)

        if size < 0:  # 卖出加收印花税
            commission += value * self.p.stamp_duty

        return commission
