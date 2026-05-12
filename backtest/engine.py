"""
回测引擎 — 封装 Cerebro 配置，提供一键回测接口
返回增强结果：净值序列、月度收益、逐笔交易、买入持有基准
"""
import backtrader as bt
import pandas as pd
import numpy as np

from config import INITIAL_CASH, SLIPPAGE, RISK_FREE_RATE
from backtest.commission import AStockCommission
from backtest.analyzers import NetValue
from data.fetcher import fetch_stock_hist
from data.cleaner import clean_for_backtrader


class TradeRecorder(bt.Analyzer):
    """记录每笔交易的日期、方向、价格、数量、盈亏"""
    def __init__(self):
        self.trades = []

    def notify_trade(self, trade):
        if trade.isclosed and trade.history:
            size = trade.history[0].event.size
            self.trades.append({
                "date": self.strategy.datetime.date(0).isoformat(),
                "direction": "买入" if size > 0 else "卖出",
                "price": round(trade.history[0].event.price, 2),
                "size": abs(size),
                "pnl": round(trade.pnlcomm, 2),
                "net_pnl": round(trade.pnl, 2),
                "bar_idx": len(self.strategy),
            })

    def get_analysis(self):
        return self.trades


class MonthlyReturn(bt.Analyzer):
    """逐月收益率"""
    def __init__(self):
        self._values = []
        self._dates = []

    def next(self):
        self._values.append(self.strategy.broker.getvalue())
        self._dates.append(self.strategy.datetime.date(0))

    def get_analysis(self):
        if len(self._values) < 2:
            return {}
        s = pd.Series(self._values, index=pd.to_datetime(self._dates))
        monthly = s.resample("ME").last().pct_change().dropna()
        return (monthly * 100).round(2).to_dict()


def run_backtest(strategy_cls, symbol, start_date, end_date,
                 cash=None, plot=False, position_percent=95, **strategy_kwargs):
    """
    一键回测入口。

    参数:
        strategy_cls:  backtrader 策略类
        symbol:        股票代码
        start_date:    起始日期 YYYYMMDD
        end_date:      结束日期 YYYYMMDD
        cash:          初始资金

    返回:
        dict: {
            initial_value, final_value, total_return,
            sharpe, drawdown, trades, annret,
            net_values, clean_df, monthly_returns,
            trade_records, buy_hold_return
        }
    """
    raw = fetch_stock_hist(symbol, start_date, end_date)
    df = clean_for_backtrader(raw)

    if len(df) < 50:
        raise ValueError(
            f"数据不足：仅获取到 {len(df)} 个交易日数据。"
            f"请扩大日期范围或选择更长的时间区间（建议至少1年以上）。"
        )

    data = bt.feeds.PandasData(dataname=df)

    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(strategy_cls, **strategy_kwargs)

    initial_cash = cash if cash is not None else INITIAL_CASH
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.addcommissioninfo(AStockCommission())
    cerebro.broker.set_slippage_perc(perc=SLIPPAGE)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=position_percent)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe",
                        riskfreerate=RISK_FREE_RATE, annualize=True)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="annret")
    cerebro.addanalyzer(NetValue, _name="netvalue")
    cerebro.addanalyzer(MonthlyReturn, _name="monthly")

    start_value = round(cerebro.broker.getvalue(), 2)
    results = cerebro.run()
    final_value = round(cerebro.broker.getvalue(), 2)
    strat = results[0]

    # 净值序列取整
    net_vals = [round(v, 2) for v in strat.analyzers.netvalue.get_analysis()]

    # 买入持有基准
    bh_start = float(df.iloc[0]["close"])
    bh_end = float(df.iloc[-1]["close"])
    buy_hold_return = (bh_end - bh_start) / bh_start

    # 基准净值曲线取整
    bh_curve = [round(float(c) / bh_start * initial_cash, 2) for c in df["close"]]

    outcome = {
        "initial_value": start_value,
        "final_value": final_value,
        "total_return": (final_value - start_value) / start_value,
        "sharpe": strat.analyzers.sharpe.get_analysis(),
        "drawdown": strat.analyzers.drawdown.get_analysis(),
        "trades": strat.analyzers.trades.get_analysis(),
        "annret": strat.analyzers.annret.get_analysis(),
        "net_values": net_vals,
        "trade_records": getattr(strat, "trade_log", []),
        "monthly_returns": strat.analyzers.monthly.get_analysis(),
        "buy_hold_return": buy_hold_return,
        "buy_hold_curve": bh_curve,
        "clean_df": df,
        "strategy": strat,
        "cerebro": cerebro,
    }

    if plot:
        cerebro.plot()

    return outcome
