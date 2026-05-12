"""
策略对比 — 同一股票同时运行多个策略，对比资金曲线和绩效指标
"""
import streamlit as st
import traceback
import pandas as pd
from datetime import date
from web.components.sidebar import POPULAR_STOCKS

from web.components.styles import inject_styles
from web.components.charts import plot_equity_curve
from backtest.engine import run_backtest

from strategies.ma_cross import MACrossStrategy
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.turtle import TurtleStrategy

STRATEGIES = {
    "📊 双均线交叉": MACrossStrategy,
    "🚀 动量突破": MomentumStrategy,
    "🔄 均值回归": MeanReversionStrategy,
    "🐢 海龟交易法": TurtleStrategy,
}

DEFAULT_PARAMS = {
    "📊 双均线交叉": {"fast": 5, "slow": 20},
    "🚀 动量突破": {"lookback": 20, "ma_period": 60, "trail_pct": 0.06},
    "🔄 均值回归": {"bb_period": 20, "bb_dev": 2.0, "rsi_period": 14},
    "🐢 海龟交易法": {"entry_period": 20, "exit_period": 10, "atr_stop": 2.0},
}

STRATEGY_COLORS = {
    "📊 双均线交叉": "#1a73e8",
    "🚀 动量突破": "#ea4335",
    "🔄 均值回归": "#0f9d58",
    "🐢 海龟交易法": "#f9ab00",
}

inject_styles()

st.title("📈 策略对比")
st.caption("同一只股票同时运行多个策略，直观对比绩效差异")

# ── 侧边栏 ─────────────────────────────────────────

with st.sidebar:
    st.header("🔍 基础设置")

    stock_options = POPULAR_STOCKS + ["__custom__ 手动输入代码..."]
    selected = st.selectbox("股票", stock_options,
                             format_func=lambda x: x if x != "__custom__ 手动输入代码..." else "✏️ 手动输入代码...")
    if selected.startswith("__custom__"):
        symbol = st.text_input("输入6位代码", value="000001", placeholder="如 000001", max_chars=6)
    else:
        symbol = selected.split()[0]
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("起始日期", value=date(2024, 1, 1),
                                   min_value=date(2000, 1, 1), max_value=date.today(),
                                   format="YYYY/MM/DD").strftime("%Y%m%d")
    with col2:
        end_date = st.date_input("结束日期", value=date(2024, 12, 31),
                                 min_value=date(2000, 1, 1), max_value=date.today(),
                                 format="YYYY/MM/DD").strftime("%Y%m%d")

    initial_cash = st.number_input(
        "初始资金 (元)", min_value=10000, max_value=10000000,
        value=100000, step=10000, format="%d"
    )

    st.markdown("---")
    st.header("🎯 选择对比策略")

    selected = {}
    for name, cls in STRATEGIES.items():
        selected[name] = st.checkbox(name, value=len(selected) < 3)

    run_clicked = st.button("🚀 开始对比", type="primary", use_container_width=True)

    st.markdown("---")
    st.caption("⚠️ 策略越多耗时越长，建议选2-3个")

# ── 运行 ─────────────────────────────────────────

if run_clicked:
    active_strategies = {k: v for k, v in STRATEGIES.items() if selected[k]}

    if len(active_strategies) == 0:
        st.warning("请至少选择一个策略")
    else:
        results = {}
        progress = st.progress(0, text="准备中...")
        total = len(active_strategies)

        for i, (name, cls) in enumerate(active_strategies.items()):
            progress.progress((i) / total, text=f"运行 {name} ...")
            try:
                kwargs = DEFAULT_PARAMS[name]
                result = run_backtest(
                    cls, symbol, start_date, end_date, cash=initial_cash, **kwargs
                )
                results[name] = result
            except Exception as e:
                st.error(f"{name} 回测失败: {e}")

        progress.progress(1.0, text="完成！")
        st.session_state["compare_results"] = results
        st.session_state["compare_params"] = (symbol, start_date, end_date)

# ── 展示结果 ─────────────────────────────────────────

if "compare_results" not in st.session_state:
    st.info("👈 在侧边栏选择要对比的策略，点击「开始对比」")
    st.stop()

results = st.session_state["compare_results"]
symbol, start, end = st.session_state.get("compare_params", ("?", "?", "?"))

if not results:
    st.warning("没有成功运行的结果")
    st.stop()

st.success(f"✅ 对比完成 — {symbol} {start} ~ {end}")

# ── 综合资金曲线 ─────────────────────────────────────

import plotly.graph_objects as go

st.subheader("💰 资金曲线对比")
st.markdown("")  # 微间距

fig = go.Figure()

metrics_rows = []
for name, r in results.items():
    nv = r["net_values"]
    color = STRATEGY_COLORS.get(name, "gray")
    returns = r["total_return"]
    dd = r["drawdown"]
    max_dd = getattr(dd.max, "drawdown", 0) if hasattr(dd, "max") else 0

    fig.add_trace(go.Scatter(
        y=nv, mode="lines", name=name,
        line=dict(color=color, width=2.2),
        hovertemplate=f"{name}<br>%{{y:,.0f}}<extra></extra>",
    ))

    metrics_rows.append({
        "策略": name,
        "总收益率": f"{returns:.2%}",
        "最大回撤": f"{max_dd:.2f}%",
        "最终资金": f"{r['final_value']:,.0f}",
        "交易次数": str(r["trades"].get("total", {}).get("total", 0)),
    })

first_r = list(results.values())[0]
bh_curve = first_r.get("buy_hold_curve", [])
if bh_curve:
    fig.add_trace(go.Scatter(
        y=bh_curve, mode="lines", name="买入持有基准",
        line=dict(color="gray", width=2, dash="dot"), opacity=0.7,
        hovertemplate="买入持有: %{y:,.0f}<extra></extra>",
    ))
fig.add_hline(y=initial_cash, line_dash="dash", line_color="#94a3b8",
              annotation_text="初始资金", opacity=0.5)
fig.update_layout(
    xaxis=dict(title="交易日", showgrid=True, gridcolor="#e5e7eb", zeroline=False),
    yaxis=dict(title="账户价值（元）", showgrid=True, gridcolor="#e5e7eb", tickformat=",.0f", zeroline=False),
    hovermode="x unified",
    plot_bgcolor="white", paper_bgcolor="white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
               bgcolor="rgba(255,255,255,0.9)", bordercolor="#e5e7eb", borderwidth=1),
    margin=dict(l=60, r=30, t=30, b=30),
    height=480,
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br><br>", unsafe_allow_html=True)
st.subheader("📊 绩效指标对比")

df_metrics = pd.DataFrame(metrics_rows)
st.dataframe(df_metrics, use_container_width=True, hide_index=True)

# ── 年度收益对比 ─────────────────────────────────────

st.subheader("📅 年度收益率对比")

all_years = set()
for r in results.values():
    all_years.update(r.get("annret", {}).keys())
all_years = sorted(all_years)

if all_years:
    fig_bar = go.Figure()
    for name, r in results.items():
        annret = r.get("annret", {})
        values = [annret.get(y, 0) * 100 for y in all_years]
        fig_bar.add_trace(go.Bar(
            name=name, x=[str(y) for y in all_years], y=values,
            marker_color=STRATEGY_COLORS.get(name, "gray"),
            text=[f"{v:.1f}%" for v in values], textposition="outside",
            textfont=dict(size=10),
        ))

    fig_bar.update_layout(
        barmode="group",
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="收益率（%）", showgrid=True, gridcolor="#e5e7eb", zeroline=False),
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=60, r=30, t=20, b=30),
        height=400,
    )
    fig_bar.add_hline(y=0, line_color="#94a3b8", line_width=0.5)
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

# ── 建议 ─────────────────────────────────────────

st.markdown("---")
st.subheader("💡 对比结论提示")

best = max(results.items(), key=lambda x: x[1]["total_return"])
best_dd = min(results.items(),
               key=lambda x: getattr(x[1]["drawdown"].max, "drawdown", 999)
               if hasattr(x[1]["drawdown"], "max") else 999)

st.info(f"""
- **收益最高**: {best[0]}（{best[1]['total_return']:.2%}）
- **回撤最小**: {best_dd[0]}
- 注意：单次回测结果受参数和时间区间影响较大，建议多周期验证
""")
