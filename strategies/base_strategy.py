"""
策略基类 — 提供日志、订单管理和 A股 T+1 约束
"""
import backtrader as bt


class BaseStrategy(bt.Strategy):
    """所有策略的基类，封装通用能力"""

    def __init__(self):
        self.order = None     # 当前未成交订单
        self.buy_bar = None   # 最近一次买入所在的 bar 索引（用于 T+1 检查）
        self.trade_log = []   # 逐笔交易记录

    def log(self, msg):
        dt = self.datas[0].datetime.date(0)
        print(f"  [{dt}] {msg}")

    def notify_order(self, order):
        if order.status == order.Completed:
            if order.isbuy():
                self.log(f"买入 {order.executed.size:.0f}股 @ {order.executed.price:.2f}")
                self.buy_bar = len(self)
                self._last_buy = {
                    "date": self.datas[0].datetime.date(0).isoformat(),
                    "price": round(order.executed.price, 2),
                    "size": int(order.executed.size),
                    "bar_idx": len(self),
                }
            else:
                self.log(f"卖出 {order.executed.size:.0f}股 @ {order.executed.price:.2f}")
                self._last_sell = {
                    "date": self.datas[0].datetime.date(0).isoformat(),
                    "price": round(order.executed.price, 2),
                    "size": int(order.executed.size),
                    "bar_idx": len(self),
                }
        elif order.status in (order.Canceled, order.Margin, order.Rejected):
            self.log(f"订单失败: {order.getstatusname()}")

        self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.log(f"交易完成  毛利: {trade.pnl:.2f}  净利: {trade.pnlcomm:.2f}")
            buy_info = getattr(self, "_last_buy", {})
            sell_info = getattr(self, "_last_sell", {})
            self.trade_log.append({
                "buy_date": buy_info.get("date", ""),
                "buy_price": buy_info.get("price", 0),
                "sell_date": sell_info.get("date", ""),
                "sell_price": sell_info.get("price", 0),
                "size": buy_info.get("size", 0),
                "pnl": round(trade.pnl, 2),
                "net_pnl": round(trade.pnlcomm, 2),
                "buy_bar": buy_info.get("bar_idx", 0),
                "sell_bar": sell_info.get("bar_idx", 0),
            })

    def can_sell(self):
        """T+1 检查：当日买入的股票下一个交易日才允许卖出"""
        if self.buy_bar is None:
            return True
        return len(self) > self.buy_bar
