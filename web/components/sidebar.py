"""
侧边栏 — 股票搜索、策略选择、参数配置
"""
import streamlit as st
from datetime import date

from web.strategy_config import (
    STRATEGY_CONFIG, POPULAR_STOCKS, convert_params_for_backtest,
)


def _render_stock_selector():
    """渲染股票选择器：热门股票下拉 + 全市场搜索"""
    st.sidebar.markdown("### ① 选择股票")

    mode = st.sidebar.radio(
        "选择方式", ["⭐ 热门股票", "🔍 搜索全部"],
        label_visibility="collapsed", horizontal=True
    )

    if mode == "⭐ 热门股票":
        stock_options = POPULAR_STOCKS + ["__custom__ ✏️ 手动输入..."]
        selected = st.sidebar.selectbox(
            "股票", stock_options,
            format_func=lambda x: x if "__custom__" not in x else "✏️ 手动输入代码..."
        )
        if selected.startswith("__custom__"):
            return st.sidebar.text_input(
                "输入6位代码", value="000001", placeholder="如 000001", max_chars=6
            )
        return selected.split()[0]

    # 全市场搜索
    search_query = st.sidebar.text_input(
        "输入代码或名称", value="", placeholder="如 000001 或 平安",
        max_chars=20
    )
    if len(search_query) >= 2:
        try:
            from data.fetcher import fetch_stock_list
            df = fetch_stock_list()
            code = df["代码"].astype(str).str.strip()
            name = df["名称"].astype(str).str.strip()
            mask = code.str.contains(search_query) | name.str.contains(search_query)
            matches = df[mask].head(30)
            if not matches.empty:
                opts = [f"{r['代码']} {r['名称']}" for _, r in matches.iterrows()]
                sel = st.sidebar.selectbox(f"匹配 {len(matches)} 只", opts)
                if sel:
                    return sel.split()[0]
            else:
                st.sidebar.caption("无匹配结果")
        except Exception:
            st.sidebar.caption("股票列表加载失败，请使用热门股票")
            return "000001"

    return st.sidebar.text_input(
        "手动输入代码", value="000001", placeholder="如 000001", max_chars=6,
        label_visibility="collapsed" if search_query else "visible"
    )


def render_sidebar():
    """渲染侧边栏，返回 (参数字典, 是否点击回测)"""
    st.sidebar.markdown("### A股量化回测")
    st.sidebar.caption("Backtrader + AKShare · 免费开源")
    st.sidebar.markdown("---")

    # Step 1: 股票选择
    symbol = _render_stock_selector()
    params = {"symbol": symbol}

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

    # Step 2: 策略选择
    st.sidebar.markdown("### ② 选择策略")

    keys = list(STRATEGY_CONFIG.keys())
    labels = [f"{v['icon']} {v['name']}" for v in STRATEGY_CONFIG.values()]
    idx = st.sidebar.selectbox("策略", range(len(keys)),
                               format_func=lambda i: labels[i],
                               label_visibility="collapsed")
    params["strategy"] = keys[idx]
    meta = STRATEGY_CONFIG[params["strategy"]]

    with st.sidebar.expander(f"{meta['icon']} {meta['name']} — 简介", expanded=False):
        st.caption(meta['desc'])
        st.caption(f"适合 {meta['suit']}  ·  风险 {meta['risk']}")

    st.sidebar.markdown("---")

    # Step 3: 参数配置
    st.sidebar.markdown("### ③ 调整参数")

    presets = meta["presets"]
    preset_names = list(presets.keys())
    selected_preset = st.sidebar.selectbox(
        "预设方案", preset_names,
        index=preset_names.index(
            st.session_state.get(f"preset_{params['strategy']}", "📐 默认")
            if "📐 默认" in preset_names else preset_names[0]
        )
    )
    st.session_state[f"preset_{params['strategy']}"] = selected_preset
    preset_vals = presets.get(selected_preset, presets.get("📐 默认", {}))

    for key, cfg in meta["params"].items():
        default_val = preset_vals.get(key, cfg["default"])
        if cfg["type"] == "float":
            params[key] = st.sidebar.slider(
                cfg["label"], float(cfg["min"]), float(cfg["max"]),
                float(default_val), 0.1, help=cfg["help"]
            )
        else:
            params[key] = st.sidebar.slider(
                cfg["label"], int(cfg["min"]), int(cfg["max"]),
                int(default_val), help=cfg["help"]
            )

    st.sidebar.markdown("---")

    # Step 4: 执行
    st.sidebar.markdown("### ④ 开始回测")
    run = st.sidebar.button("🚀 开始回测", type="primary", use_container_width=True)

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.caption("数据来源：东方财富 / 新浪")
    st.sidebar.caption("⚠️ 仅供研究，不构成投资建议")

    # 将 UI 参数转换为回测引擎格式
    params = convert_params_for_backtest(params["strategy"], params)

    return params, run
