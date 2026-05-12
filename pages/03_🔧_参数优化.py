"""
参数优化 — 网格搜索策略最优参数，热力图可视化
"""
import streamlit as st
import traceback
import itertools
from datetime import date
from web.components.sidebar import POPULAR_STOCKS

from web.components.styles import inject_styles
from web.components.charts import plot_optimization_heatmap
from backtest.engine import run_backtest

from strategies.ma_cross import MACrossStrategy
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.turtle import TurtleStrategy

inject_styles()

st.title("🔧 参数优化")
st.caption("网格搜索策略最优参数组合，用热力图可视化不同参数对收益率的影响")

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
        "初始资金 (元)", min_value=10000, value=100000, step=10000, format="%d"
    )

    st.markdown("---")
    st.header("🎯 选择策略")

    opt_strategy = st.selectbox(
        "优化策略",
        ["ma_cross", "momentum", "mean_rev", "turtle"],
        format_func=lambda x: {
            "ma_cross": "双均线交叉",
            "momentum": "动量突破",
            "mean_rev": "均值回归",
            "turtle": "海龟交易法",
        }[x]
    )

    st.markdown("---")
    st.header("⚙️ 参数范围")

    if opt_strategy == "ma_cross":
        param1_name = "快线周期"
        param1_range = st.text_input(f"{param1_name} 范围", value="3,5,8,10,15,20",
                                     help="逗号分隔")
        param2_name = "慢线周期"
        param2_range = st.text_input(f"{param2_name} 范围", value="10,20,30,40,60",
                                     help="逗号分隔")

    elif opt_strategy == "momentum":
        param1_name = "回顾周期"
        param1_range = st.text_input(f"{param1_name} 范围", value="10,15,20,25,30",
                                     help="逗号分隔")
        param2_name = "移动止损%"
        param2_range = st.text_input(f"{param2_name} 范围", value="3,4,6,8,10",
                                     help="逗号分隔")

    elif opt_strategy == "mean_rev":
        param1_name = "布林带周期"
        param1_range = st.text_input(f"{param1_name} 范围", value="10,15,20,30,40")
        param2_name = "标准差倍数"
        param2_range = st.text_input(f"{param2_name} 范围", value="1.5,2.0,2.5,3.0")

    elif opt_strategy == "turtle":
        param1_name = "入场周期"
        param1_range = st.text_input(f"{param1_name} 范围", value="15,20,30,40,55")
        param2_name = "出场周期"
        param2_range = st.text_input(f"{param2_name} 范围", value="7,10,15,20,25")

    st.markdown("---")

    run_clicked = st.button("🔍 开始优化", type="primary", use_container_width=True)

    st.caption("⚠️ 优化参数越多耗时越长。建议每个参数5-6个值，共25-36次回测")

# ── 运行优化 ─────────────────────────────────────────

if run_clicked:
    try:
        if opt_strategy == "mean_rev":
            param1_values = [int(x.strip()) for x in param1_range.split(",")]
            param2_values = [float(x.strip()) for x in param2_range.split(",")]
        elif opt_strategy == "momentum":
            param1_values = [int(x.strip()) for x in param1_range.split(",")]
            param2_values = [int(x.strip()) for x in param2_range.split(",")]
        else:
            param1_values = [int(x.strip()) for x in param1_range.split(",")]
            param2_values = [int(x.strip()) for x in param2_range.split(",")]
    except ValueError:
        st.error("参数格式错误，请用逗号分隔数字，如 5,10,15,20")
        st.stop()

    total_runs = len(param1_values) * len(param2_values)
    st.info(f"即将运行 {total_runs} 次回测（{len(param1_values)}×{len(param2_values)}）")

    returns_matrix = []
    best_return = -999
    best_params = None

    progress = st.progress(0, text="优化进行中...")
    run_count = 0

    for i, p1 in enumerate(param1_values):
        row = []
        for j, p2 in enumerate(param2_values):
            run_count += 1
            progress.progress(
                run_count / total_runs,
                text=f"回测 {run_count}/{total_runs}: {param1_name}={p1}, {param2_name}={p2}"
            )

            try:
                if opt_strategy == "ma_cross":
                    result = run_backtest(
                        MACrossStrategy, symbol, start_date, end_date,
                        cash=initial_cash, fast=p1, slow=p2,
                    )
                elif opt_strategy == "momentum":
                    result = run_backtest(
                        MomentumStrategy, symbol, start_date, end_date,
                        cash=initial_cash, lookback=p1, trail_pct=p2 / 100,
                    )
                elif opt_strategy == "mean_rev":
                    result = run_backtest(
                        MeanReversionStrategy, symbol, start_date, end_date,
                        cash=initial_cash, bb_period=int(p1), bb_dev=p2,
                    )
                elif opt_strategy == "turtle":
                    result = run_backtest(
                        TurtleStrategy, symbol, start_date, end_date,
                        cash=initial_cash, entry_period=p1, exit_period=p2,
                    )

                ret = result["total_return"]
                row.append(ret)
                if ret > best_return:
                    best_return = ret
                    best_params = (p1, p2)
            except Exception:
                row.append(0)

        returns_matrix.append(row)

    progress.progress(1.0, text="优化完成！")
    st.success(f"✅ 优化完成 — 共 {total_runs} 次回测")

    st.session_state["opt_results"] = {
        "param1_name": param1_name,
        "param2_name": param2_name,
        "param1_values": param1_values,
        "param2_values": param2_values,
        "returns_matrix": returns_matrix,
        "best_return": best_return,
        "best_params": best_params,
    }

# ── 展示结果 ─────────────────────────────────────────

if "opt_results" not in st.session_state:
    st.info("👈 在侧边栏设置参数范围，点击「开始优化」")
    st.stop()

opt = st.session_state["opt_results"]

# ── 热力图 ─────────────────────────────────────────

st.subheader("🔥 参数优化热力图")

fig = plot_optimization_heatmap(
    opt["param1_values"], opt["param2_values"],
    opt["returns_matrix"],
    opt["param1_name"], opt["param2_name"],
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── 最优结果 ─────────────────────────────────────────

st.markdown("---")
st.subheader("🏆 最优参数")

col_best, col_detail = st.columns([1, 2])
with col_best:
    st.metric("最优收益率", f"{opt['best_return']:.2%}")
    st.markdown(f"**{opt['param1_name']}**: {opt['best_params'][0]}")
    st.markdown(f"**{opt['param2_name']}**: {opt['best_params'][1]}")

with col_detail:
    st.info("""
    **使用建议**:\n
    1. 最优参数仅代表历史表现，不等于未来收益\n
    2. 注意热力图中是否有"孤岛"（单一参数组合极高，但周围很低）— 这可能是过拟合信号\n
    3. 建议选择收益稳定且周围区域表现也不错的参数范围\n
    4. 用不同时间段验证参数稳定性
    """)

# ── 参数稳定性提示 ─────────────────────────────────────

st.subheader("📊 参数稳定性分析")

matrix = opt["returns_matrix"]
stability_score = 0
if len(matrix) >= 2 and len(matrix[0]) >= 2:
    # 检查最优参数周围的表现
    best_i = opt["param1_values"].index(opt["best_params"][0])
    best_j = opt["param2_values"].index(opt["best_params"][1])
    neighbors = []
    for di in [-1, 0, 1]:
        for dj in [-1, 0, 1]:
            ni, nj = best_i + di, best_j + dj
            if 0 <= ni < len(matrix) and 0 <= nj < len(matrix[0]) and (di != 0 or dj != 0):
                neighbors.append(matrix[ni][nj])

    if neighbors:
        avg_neighbor = sum(neighbors) / len(neighbors)
        stability = 1 - abs(opt["best_return"] - avg_neighbor) / (abs(opt["best_return"]) + 0.001)
        stability = max(0, min(1, stability))

        if stability > 0.7:
            st.success(f"参数稳定性: 良好 ({stability:.1%}) — 最优参数周围表现一致")
        elif stability > 0.4:
            st.warning(f"参数稳定性: 一般 ({stability:.1%}) — 最优参数可能有一定过拟合风险")
        else:
            st.error(f"参数稳定性: 较差 ({stability:.1%}) — 建议扩大回测时间段验证")
