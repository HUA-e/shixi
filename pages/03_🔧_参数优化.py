"""
参数优化 — 网格搜索策略最优参数，热力图可视化
"""
import streamlit as st
import traceback
from datetime import date
from web.strategy_config import STRATEGY_CLASSES, STRATEGY_CONFIG, convert_params_for_backtest, POPULAR_STOCKS
from web.components.styles import inject_styles
from web.components.charts import plot_optimization_heatmap
from backtest.engine import run_backtest

inject_styles()

st.title("参数优化")
st.caption("网格搜索策略最优参数组合，用热力图可视化不同参数对收益率的影响")

# ── 优化参数对：从统一配置读取前两个参数 ──────────────

OPT_PARAMS = {
    "ma_cross": ("fast", "slow"),
    "momentum": ("lookback", "trail_pct"),
    "mean_rev": ("bb_period", "bb_dev"),
    "turtle": ("entry_period", "exit_period"),
}

# ── 侧边栏 ─────────────────────────────────────────

with st.sidebar:
    st.header("基础设置")

    stock_options = POPULAR_STOCKS + ["__custom__ 手动输入代码..."]
    sel = st.selectbox("股票", stock_options,
                       format_func=lambda x: x if x != "__custom__ 手动输入代码..." else "✏️ 手动输入代码...")
    if sel.startswith("__custom__"):
        symbol = st.text_input("输入6位代码", value="000001", placeholder="如 000001", max_chars=6)
    else:
        symbol = sel.split()[0]

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
    st.header("选择策略")

    keys = list(STRATEGY_CONFIG.keys())
    labels = [f"{v['icon']} {v['name']}" for v in STRATEGY_CONFIG.values()]
    idx = st.selectbox("策略", range(len(keys)),
                       format_func=lambda i: labels[i],
                       label_visibility="collapsed")
    opt_strategy = keys[idx]
    meta = STRATEGY_CONFIG[opt_strategy]

    st.markdown("---")
    st.header("参数范围")

    p1_key, p2_key = OPT_PARAMS[opt_strategy]
    p1_meta = meta["params"][p1_key]
    p2_meta = meta["params"][p2_key]

    param1_name = p1_meta["label"]
    param1_range = st.text_input(
        f"{param1_name} 范围",
        value=",".join(str(v) for v in sorted({
            p1_meta["default"],
            p1_meta["min"],
            p1_meta["max"],
            (p1_meta["min"] + p1_meta["max"]) // 2 if p1_meta["type"] == "int" else (p1_meta["min"] + p1_meta["max"]) / 2,
            (p1_meta["min"] + p1_meta["default"]) // 2 if p1_meta["type"] == "int" else (p1_meta["min"] + p1_meta["default"]) / 2,
        })),
        help="逗号分隔"
    )

    param2_name = p2_meta["label"]
    param2_defaults = sorted({
        p2_meta["default"],
        p2_meta["min"],
        p2_meta["max"],
        round((p2_meta["min"] + p2_meta["max"]) / 2, 1),
        round((p2_meta["min"] + p2_meta["default"]) / 2, 1),
    })
    param2_range = st.text_input(
        f"{param2_name} 范围",
        value=",".join(str(v) for v in param2_defaults),
        help="逗号分隔"
    )

    st.markdown("---")

    run_clicked = st.button("开始优化", type="primary", use_container_width=True)

    st.caption("优化参数越多耗时越长。建议每个参数5-6个值，共25-36次回测")

# ── 运行优化 ─────────────────────────────────────────

if run_clicked:
    try:
        if p1_meta["type"] == "float":
            param1_values = [float(x.strip()) for x in param1_range.split(",")]
        else:
            param1_values = [int(x.strip()) for x in param1_range.split(",")]
        if p2_meta["type"] == "float":
            param2_values = [float(x.strip()) for x in param2_range.split(",")]
        else:
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
    strategy_cls = STRATEGY_CLASSES[opt_strategy]

    for i, p1 in enumerate(param1_values):
        row = []
        for j, p2 in enumerate(param2_values):
            run_count += 1
            progress.progress(
                run_count / total_runs,
                text=f"回测 {run_count}/{total_runs}: {param1_name}={p1}, {param2_name}={p2}"
            )

            try:
                kwargs = {p1_key: p1, p2_key: p2}
                kwargs = convert_params_for_backtest(opt_strategy, kwargs)
                result = run_backtest(
                    strategy_cls, symbol, start_date, end_date,
                    cash=initial_cash, **kwargs,
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
    st.success(f"优化完成 — 共 {total_runs} 次回测")

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
    st.info("在侧边栏设置参数范围，点击「开始优化」")
    st.stop()

opt = st.session_state["opt_results"]

# ── 热力图 ─────────────────────────────────────────

st.subheader("参数优化热力图")

fig = plot_optimization_heatmap(
    opt["param1_values"], opt["param2_values"],
    opt["returns_matrix"],
    opt["param1_name"], opt["param2_name"],
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── 最优结果 ─────────────────────────────────────────

st.markdown("---")
st.subheader("最优参数")

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

# ── 参数稳定性分析 ─────────────────────────────────────

st.subheader("参数稳定性分析")

matrix = opt["returns_matrix"]
if len(matrix) >= 2 and len(matrix[0]) >= 2:
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
