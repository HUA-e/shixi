"""
侧边栏 — 清晰引导、参数配置、预设方案
"""
import streamlit as st
from datetime import date

# 热门A股列表（代码 + 名称），方便快速选择
POPULAR_STOCKS = [
    "000001 平安银行", "000002 万科A", "000333 美的集团", "000651 格力电器",
    "000858 五粮液", "002415 海康威视", "300750 宁德时代", "600000 浦发银行",
    "600036 招商银行", "600276 恒瑞医药", "600519 贵州茅台", "600585 海螺水泥",
    "600887 伊利股份", "601012 隆基绿能", "601318 中国平安", "601398 工商银行",
    "601888 中国中免", "603259 药明康德", "603288 海天味业",
]

STRATEGY_META = {
    "ma_cross": {
        "name": "双均线交叉",
        "icon": "📊",
        "desc": "短期均线上穿长期均线时买入，下穿时卖出。最经典的趋势跟踪策略。",
        "suit": "趋势行情",
        "risk": "低",
        "params": {
            "fast": {"label": "快线周期", "min": 2, "max": 60, "default": 5,
                     "help": "短期均线，值越小信号越灵敏"},
            "slow": {"label": "慢线周期", "min": 5, "max": 120, "default": 20,
                     "help": "长期均线，值越大过滤噪音越多"},
        },
        "presets": {
            "⚡ 短线": {"fast": 3, "slow": 10},
            "📐 默认": {"fast": 5, "slow": 20},
            "🗓 中线": {"fast": 10, "slow": 30},
            "🏛 长线": {"fast": 20, "slow": 60},
        },
    },
    "momentum": {
        "name": "动量突破",
        "icon": "🚀",
        "desc": "价格突破N日最高价入场，移动止损跟踪利润。适合强势股。",
        "suit": "牛市/强势股",
        "risk": "中",
        "params": {
            "lookback": {"label": "回顾周期", "min": 5, "max": 60, "default": 20,
                         "help": "突破N日最高价时买入"},
            "ma_period": {"label": "趋势过滤MA", "min": 20, "max": 120, "default": 60,
                          "help": "价格在MA上方才允许买入"},
            "trail_pct": {"label": "移动止损 (%)", "min": 1, "max": 15, "default": 6,
                          "help": "从最高点回撤超过此比例即卖出"},
        },
        "presets": {
            "⚡ 激进": {"lookback": 10, "ma_period": 30, "trail_pct": 8},
            "📐 默认": {"lookback": 20, "ma_period": 60, "trail_pct": 6},
            "🛡 稳健": {"lookback": 30, "ma_period": 90, "trail_pct": 4},
        },
    },
    "mean_rev": {
        "name": "均值回归",
        "icon": "🔄",
        "desc": "价格触及布林带下轨且超卖时买入，回到上轨或超买时卖出。",
        "suit": "震荡市",
        "risk": "中",
        "params": {
            "bb_period": {"label": "布林带周期", "min": 10, "max": 50, "default": 20,
                          "help": "布林带中轨的移动平均周期"},
            "bb_dev": {"label": "标准差倍数", "min": 1.0, "max": 3.0, "default": 2.0,
                       "help": "上下轨宽度，越大越宽"},
            "rsi_period": {"label": "RSI周期", "min": 7, "max": 30, "default": 14,
                           "help": "超买超卖判断周期"},
        },
        "presets": {
            "📐 默认": {"bb_period": 20, "bb_dev": 2.0, "rsi_period": 14},
            "📏 宽轨": {"bb_period": 20, "bb_dev": 2.5, "rsi_period": 14},
            "📐 窄轨": {"bb_period": 10, "bb_dev": 1.5, "rsi_period": 10},
        },
    },
    "turtle": {
        "name": "海龟交易法",
        "icon": "🐢",
        "desc": "突破唐奇安通道入场，ATR动态止损。Richard Dennis的传奇系统。",
        "suit": "中长期趋势",
        "risk": "高",
        "params": {
            "entry_period": {"label": "入场周期", "min": 10, "max": 60, "default": 20,
                             "help": "突破N日最高价入场"},
            "exit_period": {"label": "出场周期", "min": 5, "max": 30, "default": 10,
                            "help": "跌破N日最低价出场"},
            "atr_stop": {"label": "ATR止损倍数", "min": 1.0, "max": 4.0, "default": 2.0,
                         "help": "止损距离 = N × ATR"},
        },
        "presets": {
            "🐢 系统1": {"entry_period": 20, "exit_period": 10, "atr_stop": 2.0},
            "🐢 系统2": {"entry_period": 55, "exit_period": 20, "atr_stop": 2.0},
            "⚡ 激进": {"entry_period": 15, "exit_period": 7, "atr_stop": 1.5},
        },
    },
}


def render_sidebar():
    """渲染侧边栏，返回 (参数字典, 是否点击回测)"""
    st.sidebar.markdown("### A股量化回测")
    st.sidebar.caption("Backtrader + AKShare · 免费开源")

    st.sidebar.markdown("---")

    # === Step 1: 股票选择 ===
    st.sidebar.markdown("### ① 选择股票")
    params = {}

    stock_options = POPULAR_STOCKS + ["__custom__ 手动输入代码..."]
    selected = st.sidebar.selectbox("股票", stock_options,
                                     format_func=lambda x: x if x != "__custom__ 手动输入代码..." else "✏️ 手动输入代码...")
    if selected.startswith("__custom__"):
        params["symbol"] = st.sidebar.text_input("输入6位代码", value="000001",
                                                  placeholder="如 000001", max_chars=6)
    else:
        params["symbol"] = selected.split()[0]

    c1, c2 = st.sidebar.columns(2)
    with c1:
        start_d = st.date_input("开始日期", value=date(2024, 1, 1),
                                min_value=date(2000, 1, 1), max_value=date.today())
        params["start_date"] = start_d.strftime("%Y%m%d")
    with c2:
        end_d = st.date_input("结束日期", value=date(2024, 12, 31),
                              min_value=date(2000, 1, 1), max_value=date.today())
        params["end_date"] = end_d.strftime("%Y%m%d")

    params["initial_cash"] = st.sidebar.number_input(
        "初始资金（元）", 10000, 10000000, 100000, 10000, format="%d"
    )

    st.sidebar.markdown("---")

    # === Step 2: 策略选择 ===
    st.sidebar.markdown("### ② 选择策略")

    keys = list(STRATEGY_META.keys())
    labels = [f"{v['icon']} {v['name']}" for v in STRATEGY_META.values()]
    idx = st.sidebar.selectbox("策略", range(len(keys)),
                               format_func=lambda i: labels[i],
                               label_visibility="collapsed")
    params["strategy"] = keys[idx]
    meta = STRATEGY_META[params["strategy"]]

    # 策略简介
    with st.sidebar.expander(f"{meta['icon']} {meta['name']} — 简介", expanded=False):
        st.caption(meta['desc'])
        st.caption(f"适合 {meta['suit']}  ·  风险 {meta['risk']}")

    st.sidebar.markdown("---")

    # === Step 3: 参数配置 ===
    st.sidebar.markdown("### ③ 调整参数")

    # 预设按钮
    presets = meta["presets"]
    preset_names = list(presets.keys())
    preset_cols = st.sidebar.columns(len(preset_names))

    selected_preset = st.session_state.get(f"preset_{params['strategy']}", "📐 默认")
    for i, name in enumerate(preset_names):
        with preset_cols[i]:
            btn_type = "primary" if name == selected_preset else "secondary"
            if st.button(name, key=f"p_{params['strategy']}_{i}",
                        use_container_width=True, type=btn_type):
                st.session_state[f"preset_{params['strategy']}"] = name
                st.rerun()

    preset_vals = presets.get(selected_preset, presets.get("📐 默认", {}))

    # 参数滑块
    for key, cfg in meta["params"].items():
        default_val = preset_vals.get(key, cfg["default"])
        if isinstance(cfg["default"], float):
            params[key] = st.sidebar.slider(
                cfg["label"], cfg["min"], cfg["max"],
                float(default_val), 0.1, help=cfg["help"]
            )
        else:
            params[key] = st.sidebar.slider(
                cfg["label"], cfg["min"], cfg["max"],
                int(default_val), help=cfg["help"]
            )

    st.sidebar.markdown("---")

    # === Step 4: 执行 ===
    st.sidebar.markdown("### ④ 开始回测")
    run = st.sidebar.button("🚀 开始回测", type="primary", use_container_width=True)

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.caption("数据来源：东方财富 / 新浪")
    st.sidebar.caption("⚠️ 仅供研究，不构成投资建议")

    return params, run
