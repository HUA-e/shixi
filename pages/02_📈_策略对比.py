"""
策略对比 — 同一股票同时运行多个策略，对比资金曲线和绩效指标
"""
import streamlit as st
import traceback
import pandas as pd
from datetime import date
import plotly.graph_objects as go

from web.components.styles import inject_styles
from web.strategy_config import (
    STRATEGY_CLASSES, STRATEGY_CONFIG, POPULAR_STOCKS,
    get_strategy_default_kwargs, convert_params_for_backtest,
)
from backtest.engine import run_backtest
try:
    from data.fetcher import fetch_index_hist
except ImportError:
    fetch_index_hist = None

STRATEGY_COLORS = {
    "ma_cross": "#1a73e8",
    "momentum": "#ea4335",
    "mean_rev": "#0f9d58",
    "turtle": "#f9ab00",
}

inject_styles()

st.title("策略对比")
st.caption("同一只股票同时运行多个策略，直观对比绩效差异")

# ── 侧边栏 ─────────────────────────────────────────

with st.sidebar:
    st.header("基础设置")

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
    st.header("选择对比策略")

    selected_strategies = {}
    for key, cfg in STRATEGY_CONFIG.items():
        selected_strategies[key] = st.checkbox(
            f"{cfg['icon']} {cfg['name']}", value=len(selected_strategies) < 3
        )

    run_clicked = st.button("开始对比", type="primary", use_container_width=True)

    st.markdown("---")
    st.caption("策略越多耗时越长，建议选2-3个")

# ── 运行 ─────────────────────────────────────────

if run_clicked:
    active = {k: v for k, v in STRATEGY_CLASSES.items() if selected_strategies[k]}

    if len(active) == 0:
        st.warning("请至少选择一个策略")
    else:
        results = {}
        progress = st.progress(0, text="准备中...")
        total = len(active)

        for i, (key, cls) in enumerate(active.items()):
            progress.progress(i / total, text=f"运行 {STRATEGY_CONFIG[key]['name']} ...")
            try:
                kwargs = get_strategy_default_kwargs(key)
                kwargs = convert_params_for_backtest(key, kwargs)
                result = run_backtest(
                    cls, symbol, start_date, end_date, cash=initial_cash, **kwargs
                )
                results[key] = result
            except Exception as e:
                st.error(f"{STRATEGY_CONFIG[key]['name']} 回测失败: {e}")

        # 获取基准
        try:
            idx_df = fetch_index_hist("000300", start_date, end_date)
            if not idx_df.empty and "close" in idx_df.columns:
                idx_start = float(idx_df["close"].iloc[0])
                benchmark = [
                    round(float(c) / idx_start * initial_cash, 2)
                    for c in idx_df["close"]
                ]
            else:
                benchmark = None
        except Exception:
            benchmark = None

        progress.progress(1.0, text="完成！")
        st.session_state["compare_results"] = results
        st.session_state["compare_benchmark"] = benchmark
        st.session_state["compare_params"] = (symbol, start_date, end_date)

# ── 展示结果 ─────────────────────────────────────────

if "compare_results" not in st.session_state:
    st.info("在侧边栏选择要对比的策略，点击「开始对比」")
    st.stop()

results = st.session_state["compare_results"]
benchmark = st.session_state.get("compare_benchmark")
symbol, start, end = st.session_state.get("compare_params", ("?", "?", "?"))

if not results:
    st.warning("没有成功运行的结果")
    st.stop()

st.success(f"对比完成 — {symbol} {start} ~ {end}")

# ── 综合资金曲线 ─────────────────────────────────────

st.subheader("资金曲线对比")
st.markdown("")

fig = go.Figure()
metrics_rows = []
first_r = list(results.values())[0]
dates = first_r.get("dates", [])

for key, r in results.items():
    nv = r["net_values"]
    cfg = STRATEGY_CONFIG[key]
    name = f"{cfg['icon']} {cfg['name']}"
    color = STRATEGY_COLORS.get(key, "gray")
    returns = r["total_return"]
    dd = r["drawdown"]
    max_dd = getattr(dd.max, "drawdown", 0) if hasattr(dd, "max") else 0
    sharpe = r["sharpe"]
    sr = sharpe.get("sharperatio")

    fig.add_trace(go.Scatter(
        x=dates if dates else list(range(len(nv))),
        y=nv, mode="lines", name=name,
        line=dict(color=color, width=2.2),
        hovertemplate=f"{name}<br>%{{y:,.0f}}<extra></extra>",
    ))

    metrics_rows.append({
        "策略": name,
        "总收益率": f"{returns:.2%}",
        "夏普比率": f"{sr:.2f}" if sr else "N/A",
        "最大回撤": f"{max_dd:.2f}%",
        "最终资金": f"{r['final_value']:,.0f}",
        "交易次数": str(r["trades"].get("total", {}).get("total", 0)),
    })

bh_curve = first_r.get("buy_hold_curve", [])
if bh_curve:
    fig.add_trace(go.Scatter(
        x=dates if dates else list(range(len(bh_curve))),
        y=bh_curve, mode="lines", name="买入持有基准",
        line=dict(color="gray", width=2, dash="dot"), opacity=0.7,
        hovertemplate="买入持有: %{y:,.0f}<extra></extra>",
    ))

if benchmark and len(benchmark) == len(dates):
    fig.add_trace(go.Scatter(
        x=dates, y=benchmark, mode="lines", name="沪深300",
        line=dict(color="#94a3b8", width=1.8, dash="dashdot"), opacity=0.65,
        hovertemplate="沪深300: %{y:,.0f}<extra></extra>",
    ))

fig.add_hline(y=initial_cash, line_dash="dash", line_color="#94a3b8",
              annotation_text="初始资金", opacity=0.5)

xaxis_config = dict(showgrid=True, gridcolor="#e5e7eb", zeroline=False)
if dates:
    xaxis_config["type"] = "date"

fig.update_layout(
    xaxis=xaxis_config,
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
st.subheader("绩效指标对比")

df_metrics = pd.DataFrame(metrics_rows)
st.dataframe(df_metrics, use_container_width=True, hide_index=True)

# ── 年度收益对比 ─────────────────────────────────────

st.subheader("年度收益率对比")

all_years = set()
for r in results.values():
    all_years.update(r.get("annret", {}).keys())
all_years = sorted(all_years)

if all_years:
    fig_bar = go.Figure()
    for key, r in results.items():
        cfg = STRATEGY_CONFIG[key]
        name = f"{cfg['icon']} {cfg['name']}"
        annret = r.get("annret", {})
        values = [annret.get(y, 0) * 100 for y in all_years]
        fig_bar.add_trace(go.Bar(
            name=name, x=[str(y) for y in all_years], y=values,
            marker_color=STRATEGY_COLORS.get(key, "gray"),
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
st.subheader("对比结论提示")

best = max(results.items(), key=lambda x: x[1]["total_return"])
best_sharpe = max(results.items(),
                  key=lambda x: x[1]["sharpe"].get("sharperatio") or -999)
best_dd = min(results.items(),
              key=lambda x: getattr(x[1]["drawdown"].max, "drawdown", 999)
              if hasattr(x[1]["drawdown"], "max") else 999)

st.info(f"""
- **收益最高**: {STRATEGY_CONFIG[best[0]]['name']}（{best[1]['total_return']:.2%}）
- **夏普最优**: {STRATEGY_CONFIG[best_sharpe[0]]['name']}（{best_sharpe[1]['sharpe'].get('sharperatio', 0):.2f}）
- **回撤最小**: {STRATEGY_CONFIG[best_dd[0]]['name']}
- 注意：单次回测结果受参数和时间区间影响较大，建议多周期验证
""")
