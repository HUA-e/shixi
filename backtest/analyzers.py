"""自定义分析器"""
import backtrader as bt


class NetValue(bt.Analyzer):
    """逐期记录账户净值，供绘图使用"""

    def __init__(self):
        self.net_values = []

    def next(self):
        self.net_values.append(self.strategy.broker.getvalue())

    def get_analysis(self):
        return self.net_values
