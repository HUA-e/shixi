"""
单股回测 — 策略回测、交互式图表、CSV导出、基准对比
"""
import streamlit as st
import traceback
import pandas as pd
from datetime import date
from io import StringIO

from web.components.styles import inject_styles
from web.components.sidebar import render_sidebar
from web.components.charts import (
    plot_equity_curve, plot_drawdown, plot_monthly_heatmap,
    plot_annual_returns, plot_kline,
)
from web.strategy_config import STRATEGY_CLASSES, STRATEGY_CONFIG
from backtest.engine import run_backtest
from data.fetcher import fetch_index_hist
from config import INITIAL_CASH


def _build_kwargs(params, meta):
    """从扁平参数字典中提取策略专属参数"""
    return {k: params[k] for k in meta["params"] if k in params}


def _make_trade_csv(records):
    """将交易记录转为CSV字符串"""
    if not records:
        return ""
    df = pd.DataFrame(records)
    cols = ["buy_date", "buy_price", "sell_date", "sell_price", "size", "pnl", "net_pnl"]
    df = df[[c for c in cols if c in df.columns]]
    df.columns = ["买入日期", "买入价", "卖出日期", "卖出价", "数量(股)", "毛利", "净利"]
    return df.to_csv(index=False)


def _make_equity_csv(dates, net_values, bh_curve=None):
    """将净值曲线转为CSV字符串"""
    data = {"日期": dates, "策略权益": net_values}
    if bh_curve and len(bh_curve) == len(dates):
        data["买入持有"] = bh_curve
    return pd.DataFrame(data).to_csv(index=False)


inject_styles()
params, run_clicked = render_sidebar()
meta = STRATEGY_CONFIG[params["strategy"]]

st.title("单股回测")

if run_clicked:
    with st.spinner(f"正在获取 {params['symbol']} 数据并运行回测..."):
        try:
            result = run_backtest(
                STRATEGY_CLASSES[params["strategy"]], params["symbol"],
                params["start_date"], params["end_date"],
                cash=params["initial_cash"],
                **_build_kwargs(params, meta),
            )

            # 获取沪深300基准
            try:
                idx_df = fetch_index_hist(
                    "000300", params["start_date"], params["end_date"]
                )
                if not idx_df.empty and "close" in idx_df.columns:
                    idx_start = float(idx_df["close"].iloc[0])
                    idx_curve = [
                        round(float(c) / idx_start * params["initial_cash"], 2)
                        for c in idx_df["close"]
                    ]
                    if len(idx_curve) != len(result["net_values"]):
                        idx_curve = None
                else:
                    idx_curve = None
            except Exception:
                idx_curve = None

            result["benchmark_curve"] = idx_curve
            result["benchmark_label"] = "沪深300"
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

# 指标卡片
c1, c2 = st.columns(2)
c3, c4 = st.columns(2)
c5, c6 = st.columns(2)
c7, c8 = st.columns(2)
c1.metric("总收益率", f"{returns:+.2%}")
c2.metric("买入持有基准", f"{bh_return:+.2%}")
c3.metric("超额收益", f"{returns - bh_return:+.2%}")
c4.metric("最大回撤", f"{max_dd:.1f}%（持续{dd_len}天）")
c5.metric("夏普比率", f"{sr:.2f}" if sr else "数据不足")
c6.metric("交易次数", f"{total_trades} 次（胜率 {win_rate:.0f}%）")
c7.metric("初始资金", f"{r['initial_value']:,.0f} 元")
c8.metric("最终资金", f"{r['final_value']:,.0f} 元")

st.markdown("<br>", unsafe_allow_html=True)

# --- 资金曲线 ---
st.subheader("资金曲线")
fig = plot_equity_curve(
    r["net_values"], r["initial_value"],
    buy_hold_curve=r.get("buy_hold_curve"),
    trades=r.get("trade_records", []),
    dates=r.get("dates"),
    benchmark_curve=r.get("benchmark_curve"),
    benchmark_label=r.get("benchmark_label", "沪深300"),
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# --- 导出按钮 ---
col_dl1, col_dl2 = st.columns(2)
with col_dl1:
    equity_csv = _make_equity_csv(
        r.get("dates", []), r["net_values"], r.get("buy_hold_curve")
    )
    if equity_csv:
        st.download_button(
            "📥 导出净值曲线 CSV", equity_csv,
            file_name=f"equity_{params['symbol']}_{params['start_date']}_{params['end_date']}.csv",
            mime="text/csv",
        )
with col_dl2:
    trade_csv = _make_trade_csv(r.get("trade_records", []))
    if trade_csv:
        st.download_button(
            "📥 导出交易明细 CSV", trade_csv,
            file_name=f"trades_{params['symbol']}_{params['start_date']}_{params['end_date']}.csv",
            mime="text/csv",
        )

st.markdown("<br>", unsafe_allow_html=True)

# --- 回撤分析 ---
st.subheader("回撤分析")
fig = plot_drawdown(r["net_values"], dates=r.get("dates"))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# --- 月度热力图 ---
st.subheader("月度收益热力图")
fig = plot_monthly_heatmap(r.get("monthly_returns", {}))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# --- 年度收益率 ---
st.subheader("年度收益率")
fig = plot_annual_returns(r.get("annret", {}))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# --- K线图 ---
st.subheader("K线图")
df = r.get("clean_df")
if df is not None and not df.empty:
    fig = plot_kline(df)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# --- 交易明细 ---
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
