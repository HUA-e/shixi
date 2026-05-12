"""
单股回测
"""
import streamlit as st
import traceback
import pandas as pd

from web.components.styles import inject_styles
from web.components.sidebar import render_sidebar
from web.components.charts import (
    plot_equity_curve, plot_drawdown, plot_monthly_heatmap,
    plot_annual_returns, plot_kline,
)
from backtest.engine import run_backtest
from strategies.ma_cross import MACrossStrategy
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.turtle import TurtleStrategy

STRATEGIES = {
    "ma_cross": MACrossStrategy,
    "momentum": MomentumStrategy,
    "mean_rev": MeanReversionStrategy,
    "turtle": TurtleStrategy,
}


def _build_kwargs(params):
    stype = params["strategy"]
    if stype == "ma_cross":
        return {"fast": params.get("fast", 5), "slow": params.get("slow", 20)}
    elif stype == "momentum":
        return {"lookback": params.get("lookback", 20), "ma_period": params.get("ma_period", 60), "trail_pct": params.get("trail_pct", 0.06)}
    elif stype == "mean_rev":
        return {"bb_period": params.get("bb_period", 20), "bb_dev": params.get("bb_dev", 2.0), "rsi_period": params.get("rsi_period", 14)}
    elif stype == "turtle":
        return {"entry_period": params.get("entry_period", 20), "exit_period": params.get("exit_period", 10), "atr_stop": params.get("atr_stop", 2.0)}
    return {}


inject_styles()
params, run_clicked = render_sidebar()

st.title("单股回测")

if run_clicked:
    with st.spinner(f"正在获取 {params['symbol']} 数据并运行回测..."):
        try:
            result = run_backtest(
                STRATEGIES[params["strategy"]], params["symbol"],
                params["start_date"], params["end_date"],
                cash=params["initial_cash"],
                **_build_kwargs(params),
            )
            st.session_state["result"] = result
        except Exception as e:
            st.error(f"回测失败: {e}")
            with st.expander("详细错误信息"):
                st.code(traceback.format_exc())

if "result" not in st.session_state:
    st.info("在左侧边栏配置参数后点击「开始回测」")
    st.stop()

r = st.session_state["result"]
returns = r["total_return"]
bh_return = r.get("buy_hold_return", 0)
sharpe = r["sharpe"]
dd = r["drawdown"]
trades = r["trades"]
sr = sharpe.get("sharperatio")
max_dd = getattr(dd.max, "drawdown", 0) if hasattr(dd, "max") else 0
dd_len = getattr(dd.max, "len", 0) if hasattr(dd, "max") else 0
total_trades = trades.get("total", {}).get("total", 0)
won = trades.get("won", {}).get("total", 0)
win_rate = won / total_trades * 100 if total_trades > 0 else 0

# 4列指标卡片——够宽不会截断
c1, c2, c3, c4 = st.columns(4)
c1.metric("总收益率", f"{returns:+.2%}")
c2.metric("买入持有基准", f"{bh_return:+.2%}")
c3.metric("超额收益", f"{returns - bh_return:+.2%}")
c4.metric("最大回撤", f"{max_dd:.1f}%（持续{dd_len}天）")

c1, c2, c3, c4 = st.columns(4)
c1.metric("夏普比率", f"{sr:.2f}" if sr else "数据不足")
c2.metric("交易次数", f"{total_trades} 次（胜率 {win_rate:.0f}%）")
c3.metric("初始资金", f"{r['initial_value']:,.0f} 元")
c4.metric("最终资金", f"{r['final_value']:,.0f} 元")

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("资金曲线")
fig = plot_equity_curve(r["net_values"], r["initial_value"], r.get("buy_hold_curve"), r.get("trade_records", []))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("回撤分析")
fig = plot_drawdown(r["net_values"])
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("月度收益热力图")
fig = plot_monthly_heatmap(r.get("monthly_returns", {}))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("年度收益率")
fig = plot_annual_returns(r.get("annret", {}))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("K线图")
df = r.get("clean_df")
if df is not None and not df.empty:
    fig = plot_kline(df)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# 交易明细
st.markdown("---")
st.subheader("交易明细")
trade_records = r.get("trade_records", [])
if trade_records:
    rows = []
    for t in trade_records:
        pnl = t.get('net_pnl', 0)
        rows.append({
            "买入日期": t.get("buy_date", ""),
            "买入价": f"{t.get('buy_price', 0):.2f} 元",
            "卖出日期": t.get("sell_date", ""),
            "卖出价": f"{t.get('sell_price', 0):.2f} 元",
            "数量": f"{t.get('size', 0):,} 股",
            "盈亏": f"{'盈利' if pnl >= 0 else '亏损'} {abs(pnl):,.2f} 元",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("该回测区间内没有产生交易")

st.markdown("---")
st.caption("免责声明：回测结果不代表未来表现，不构成投资建议。投资有风险，入市需谨慎。")
