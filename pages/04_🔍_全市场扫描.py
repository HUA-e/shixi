"""
全市场扫描 — 同一策略跑多只股票，按收益率排名
"""
import streamlit as st
import pandas as pd
from datetime import date
from io import StringIO

from web.components.styles import inject_styles
from web.strategy_config import (
    STRATEGY_CLASSES, STRATEGY_CONFIG, POPULAR_STOCKS,
    get_strategy_default_kwargs, convert_params_for_backtest,
)
from backtest.engine import run_backtest
from data.fetcher import fetch_stock_list

inject_styles()

st.title("全市场扫描")
st.caption("批量回测多只股票，快速发现最适合该策略的标的")

# ── 侧边栏 ─────────────────────────────────────────

with st.sidebar:
    st.header("扫描设置")

    # 策略选择
    keys = list(STRATEGY_CONFIG.keys())
    labels = [f"{v['icon']} {v['name']}" for v in STRATEGY_CONFIG.values()]
    idx = st.selectbox("策略", range(len(keys)),
                       format_func=lambda i: labels[i],
                       label_visibility="collapsed")
    strategy_key = keys[idx]
    meta = STRATEGY_CONFIG[strategy_key]

    # 日期
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
        "初始资金 (元)", min_value=10000, value=100000, step=10000, format="%d"
    )

    st.markdown("---")
    st.header("股票池")

    pool_mode = st.radio(
        "选择方式", ["⭐ 热门股票 (19只)", "✏️ 自定义代码"],
        label_visibility="collapsed"
    )

    if pool_mode == "⭐ 热门股票 (19只)":
        symbols = [s.split()[0] for s in POPULAR_STOCKS]
        st.caption(f"已选 {len(symbols)} 只股票")
    else:
        code_input = st.text_area(
            "输入股票代码（每行一个，或用逗号/空格分隔）",
            value="000001\n000333\n600519\n300750",
            height=120,
            placeholder="000001\n600519\n..."
        )
        import re
        symbols = re.split(r'[\s,;\n]+', code_input.strip())
        symbols = [s.strip() for s in symbols if len(s.strip()) == 6 and s.strip().isdigit()]
        st.caption(f"识别到 {len(symbols)} 个有效代码")

    st.markdown("---")
    with st.expander(f"{meta['icon']} {meta['name']} 参数"):
        default_kwargs = get_strategy_default_kwargs(strategy_key)
        for k, v in default_kwargs.items():
            st.caption(f"{k}: {v}")

    run_clicked = st.button("开始扫描", type="primary", use_container_width=True)
    st.caption(f"将运行 {len(symbols)} 次回测，可能需要几分钟")

# ── 运行扫描 ─────────────────────────────────────────

if run_clicked:
    if not symbols:
        st.error("没有有效的股票代码")
        st.stop()

    results = []
    errors = []
    progress = st.progress(0, text="准备扫描...")
    total = len(symbols)
    kwargs = convert_params_for_backtest(strategy_key, get_strategy_default_kwargs(strategy_key))
    cls = STRATEGY_CLASSES[strategy_key]

    for i, sym in enumerate(symbols):
        progress.progress(i / total, text=f"扫描 {i+1}/{total}: {sym} ...")
        try:
            r = run_backtest(
                cls, sym, start_date, end_date,
                cash=initial_cash, **kwargs,
            )
            trades = r["trades"]
            total_trades = trades.get("total", {}).get("total", 0)
            won = trades.get("won", {}).get("total", 0)
            sharpe = r["sharpe"]
            dd = r["drawdown"]
            max_dd = getattr(dd.max, "drawdown", 0) if hasattr(dd, "max") else 0

            results.append({
                "代码": sym,
                "总收益率": r["total_return"],
                "夏普比率": sharpe.get("sharperatio"),
                "最大回撤": max_dd,
                "交易次数": total_trades,
                "胜率": won / total_trades if total_trades > 0 else 0,
                "最终资金": r["final_value"],
                "_result": r,
            })
        except Exception as e:
            errors.append({"代码": sym, "错误": str(e)[:80]})

    progress.progress(1.0, text="扫描完成！")
    st.session_state["scan_results"] = results
    st.session_state["scan_errors"] = errors
    st.session_state["scan_meta"] = {
        "strategy_key": strategy_key,
        "symbols_count": total,
    }

# ── 展示结果 ─────────────────────────────────────────

if "scan_results" not in st.session_state:
    st.info("在侧边栏配置扫描参数，点击「开始扫描」")
    st.stop()

results = st.session_state["scan_results"]
errors = st.session_state.get("scan_errors", [])
meta = st.session_state.get("scan_meta", {})

st.success(f"扫描完成 — {meta.get('symbols_count', '?')} 只股票，{len(results)} 成功，{len(errors)} 失败")

if not results:
    st.warning("没有成功的回测结果")
    st.stop()

# ── 排名表 ─────────────────────────────────────────

st.subheader("收益率排名")

df = pd.DataFrame(results)
df_display = df.drop(columns=["_result"], errors="ignore").copy()
df_display = df_display.sort_values("总收益率", ascending=False).reset_index(drop=True)
df_display.index = range(1, len(df_display) + 1)
df_display.index.name = "排名"

# 格式化
df_display["总收益率"] = df_display["总收益率"].apply(lambda x: f"{x:+.2%}")
df_display["夏普比率"] = df_display["夏普比率"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
df_display["最大回撤"] = df_display["最大回撤"].apply(lambda x: f"{x:.2f}%")
df_display["胜率"] = df_display["胜率"].apply(lambda x: f"{x:.0%}" if x > 0 else "N/A")
df_display["最终资金"] = df_display["最终资金"].apply(lambda x: f"{x:,.0f}")

# 颜色标注
def _color_return(val):
    if val.startswith("+"):
        return "color: #10b981; font-weight: bold"
    elif val.startswith("-"):
        return "color: #ef4444; font-weight: bold"
    return ""

styled = df_display.style.applymap(_color_return, subset=["总收益率"])
st.dataframe(styled, use_container_width=True)

# ── 导出 ─────────────────────────────────────────

csv = df.drop(columns=["_result"], errors="ignore").to_csv(index=False)
st.download_button(
    "📥 导出扫描结果 CSV", csv,
    file_name=f"scan_{meta.get('strategy_key','strategy')}_{date.today().strftime('%Y%m%d')}.csv",
    mime="text/csv",
)

# ── 错误详情 ───────────────────────────────────────

if errors:
    st.markdown("---")
    with st.expander(f"⚠️ {len(errors)} 只股票回测失败"):
        st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)

# ── 最佳标的详情 ────────────────────────────────────

st.markdown("---")
st.subheader("最佳标的详情")

best_results = df.sort_values("总收益率", ascending=False).head(3)
for i, (_, row) in enumerate(best_results.iterrows()):
    r = row["_result"]
    trades = r["trades"]
    total_trades = trades.get("total", {}).get("total", 0)
    won = trades.get("won", {}).get("total", 0)

    with st.expander(
        f"#{i+1} {row['代码']} — {row['总收益率']:+.2%}  |  夏普 {row['夏普比率']:.2f}  |  回撤 {row['最大回撤']:.1f}%"
    ):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总收益率", f"{row['总收益率']:+.2%}")
        c2.metric("最大回撤", f"{row['最大回撤']:.1f}%")
        c3.metric("夏普比率", f"{row['夏普比率']:.2f}")
        c4.metric("交易次数", f"{total_trades} (胜率 {won/total_trades:.0%})" if total_trades > 0 else "0")

        from web.components.charts import plot_equity_curve, plot_drawdown
        fig1 = plot_equity_curve(
            r["net_values"], r["initial_value"],
            buy_hold_curve=r.get("buy_hold_curve"),
            dates=r.get("dates"),
        )
        st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

st.markdown("---")
st.caption("批量扫描依赖网络数据获取，扫描速度受限于AKShare接口响应。建议每次不超过30只股票。")
