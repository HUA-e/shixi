"""
A股量化回测系统  ·  Streamlit Web 仪表盘
启动: streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="A股量化回测系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": None,
    },
)

from web.components.styles import inject_styles
inject_styles()

# ── 顶部标题 ──────────────────────────────────────

st.title("A股量化回测系统")
st.caption("专业级量化策略回测平台  ·  4种经典策略  ·  交互式图表  ·  免费开源")
st.markdown("---")

# ── 策略卡片 ──────────────────────────────────────

st.markdown("### 🎯 内置策略")
st.caption("四种经典策略，覆盖趋势跟踪、均值回归、动量突破等主流风格")

strategies = [
    {
        "icon": "📊", "name": "双均线交叉",
        "desc": "短期均线上穿长期均线时买入，下穿时卖出。最经典的趋势跟踪策略，简单直观。",
        "tags": [("趋势跟踪", "tag-blue"), ("新手友好", "tag-green")],
        "suit": "趋势行情", "risk": "低",
    },
    {
        "icon": "🚀", "name": "动量突破",
        "desc": "价格突破N日新高时入场，配合移动止损锁定利润。强势股的利器。",
        "tags": [("趋势跟踪", "tag-blue"), ("进阶", "tag-purple")],
        "suit": "牛市/强势股", "risk": "中",
    },
    {
        "icon": "🔄", "name": "均值回归",
        "desc": "价格触及布林带下轨且RSI超卖时买入。利用价格回归均值的特性获利。",
        "tags": [("震荡交易", "tag-amber"), ("进阶", "tag-purple")],
        "suit": "震荡市/横盘", "risk": "中",
    },
    {
        "icon": "🐢", "name": "海龟交易法",
        "desc": "突破唐奇安通道入场，ATR动态止损。Richard Dennis 证明「交易可教」的传奇系统。",
        "tags": [("趋势跟踪", "tag-blue"), ("专业", "tag-purple")],
        "suit": "中长期趋势", "risk": "高",
    },
]

cols = st.columns(4)
for i, s in enumerate(strategies):
    with cols[i]:
        with st.container(border=True):
            st.markdown(f"### {s['icon']} {s['name']}")
            st.caption(s['desc'])
            tag_str = " ".join([t for t, _ in s["tags"]])
            st.caption(f"🏷 {tag_str}  |  {s['suit']}  |  风险 {s['risk']}")

st.markdown("<br>", unsafe_allow_html=True)

# ── 快速开始 ──────────────────────────────────────

st.markdown("### 三步开始")

q1, q2, q3 = st.columns(3)
with q1:
    with st.container(border=True):
        st.markdown("#### 1 选择股票与策略")
        st.caption("在左侧导航进入「单股回测」，输入股票代码，选择交易策略")
with q2:
    with st.container(border=True):
        st.markdown("#### 2 调整参数")
        st.caption("使用预设方案或手动微调，每个参数都有详细说明")
with q3:
    with st.container(border=True):
        st.markdown("#### 3 查看分析结果")
        st.caption("交互式图表、月度热力图、对比买入持有基准、风险分析")

st.markdown("---")

st.markdown("### 功能导航")

f1, f2, f3 = st.columns(3)
with f1:
    st.info("**单股回测** — 核心功能。选择一只股票，配置策略参数，运行完整回测分析。")
with f2:
    st.success("**策略对比** — 同一只股票同时运行多个策略，直观对比资金曲线和绩效。")
with f3:
    st.warning("**参数优化** — 网格搜索最优参数组合，热力图可视化，附带过拟合风险提示。")

st.markdown("---")
st.caption("免责声明：本系统仅供量化策略研究学习使用。回测结果不代表未来表现，不构成任何投资建议。")
