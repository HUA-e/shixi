"""
设计系统 — 仅添加结构样式，颜色交给 Streamlit 主题自动处理（亮暗模式均可用）
"""
import streamlit as st


def inject_styles():
    st.markdown("""
    <style>
    /* 隐藏底部 "Made with Streamlit" */
    footer { display: none !important; }

    /* 全局禁止文字截断省略号 */
    .stMarkdown, .stMarkdown p, .stMarkdown span,
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] div[data-testid="stMetricValue"],
    .stDataFrame td, .stDataFrame th,
    .stSelectbox div, .stTextInput label, button {
        overflow: visible !important;
        white-space: normal !important;
        text-overflow: clip !important;
    }

    /* 指标卡片圆角+间距 */
    div[data-testid="stMetric"] {
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 700;
    }

    /* 主标题区 */
    .main-header {
        border-radius: 20px;
        padding: 48px 56px;
        margin-bottom: 32px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
    }
    .main-header h1 {
        font-size: 2.6rem;
        font-weight: 800;
    }
    .main-header p {
        font-size: 1.15rem;
        opacity: 0.85;
    }

    /* 策略卡片 */
    .strategy-card {
        border-radius: 16px;
        padding: 28px 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: box-shadow 0.25s ease, transform 0.25s ease;
        height: 100%;
    }
    .strategy-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transform: translateY(-2px);
    }
    .strategy-card .icon { font-size: 2.2rem; margin-bottom: 12px; }
    .strategy-card h3 {
        font-size: 1.1rem; font-weight: 700; margin-bottom: 8px;
    }
    .strategy-card .desc {
        font-size: 0.85rem; line-height: 1.6; opacity: 0.8;
    }
    .strategy-card .tags { margin-top: 14px; display: flex; gap: 6px; flex-wrap: wrap; }
    .strategy-card .tag {
        font-size: 0.7rem; padding: 3px 10px; border-radius: 14px; font-weight: 600;
    }

    .step-num {
        width: 40px; height: 40px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 1.05rem; flex-shrink: 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    .tech-badge {
        display: inline-block; padding: 5px 14px;
        border-radius: 8px; font-size: 0.8rem;
        margin: 4px; font-weight: 500;
    }

    .section-divider {
        border: none; border-top: 2px solid rgba(128,128,128,0.2); margin: 28px 0;
    }

    details[data-testid="stExpander"] {
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
