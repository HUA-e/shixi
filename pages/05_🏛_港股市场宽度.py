"""
港股恒生指数 — 200MA / 50MA / 21EMA / 10EMA 多头排列比例
"""
import streamlit as st
import pandas as pd
from web.components.styles import inject_styles
from data.hk_fetcher import fetch_hk_stocks, fetch_hk_hist

N_STOCKS = 82  # 恒生指数成分股数量

inject_styles()

st.title("港股市场宽度")
st.caption("恒生指数 — 价格同时站上 200MA / 50MA / 21EMA / 10EMA 的股票比例")

# ── 侧边栏 ──────────────────────────

with st.sidebar:
    run = st.button("刷新数据", type="primary", use_container_width=True)
    st.caption("数据来源：新浪财经")
    st.caption("首次加载约需 1-2 分钟，后续秒出")

# ── 数据计算 ──────────────────────────

if run:
    with st.spinner("获取港股列表..."):
        stocks_df = fetch_hk_stocks(N_STOCKS)

    results = []
    total = len(stocks_df)
    progress = st.progress(0, text=f"0/{total}")

    for i, (_, row) in enumerate(stocks_df.iterrows()):
        sym, name = row["代码"], row["名称"]
        progress.progress((i + 1) / total, text=f"{i+1}/{total} {sym} {name}")
        try:
            df = fetch_hk_hist(sym)
            if df is None or len(df) < 200:
                continue

            df["200MA"] = df["close"].rolling(200).mean()
            df["50MA"] = df["close"].rolling(50).mean()
            df["21EMA"] = df["close"].ewm(span=21, adjust=False).mean()
            df["10EMA"] = df["close"].ewm(span=10, adjust=False).mean()

            valid = df.dropna()
            if valid.empty:
                continue

            last = valid.iloc[-1]
            results.append({
                "代码": sym,
                "名称": name,
                "最新价": round(float(last["close"]), 2),
                "10EMA": bool(last["close"] > last["10EMA"]),
                "21EMA": bool(last["close"] > last["21EMA"]),
                "50MA": bool(last["close"] > last["50MA"]),
                "200MA": bool(last["close"] > last["200MA"]),
            })
        except Exception:
            continue

    progress.progress(1.0, text="完成")

    if not results:
        st.error("没有成功获取到任何股票数据")
        st.stop()

    # 计算各项比例
    total_valid = len(results)
    above_all = sum(
        1 for r in results
        if r["10EMA"] and r["21EMA"] and r["50MA"] and r["200MA"]
    )
    above_200 = sum(1 for r in results if r["200MA"])
    above_50 = sum(1 for r in results if r["50MA"])
    above_21 = sum(1 for r in results if r["21EMA"])
    above_10 = sum(1 for r in results if r["10EMA"])

    st.session_state["hk_results"] = results
    st.session_state["hk_counts"] = {
        "total": total_valid,
        "above_all": above_all,
        "above_200": above_200,
        "above_50": above_50,
        "above_21": above_21,
        "above_10": above_10,
    }

# ── 展示 ──────────────────────────────

if "hk_results" not in st.session_state:
    st.info("点击左侧「刷新数据」开始")
    st.stop()

results = st.session_state["hk_results"]
counts = st.session_state["hk_counts"]
total = counts["total"]
ratio = counts["above_all"] / total * 100

# 颜色
if ratio > 60:
    color = "#10b981"
    label = "强势 · 多数股票多头排列"
elif ratio > 30:
    color = "#f59e0b"
    label = "中性 · 市场分化"
else:
    color = "#ef4444"
    label = "弱势 · 极少数股票走强"

# ── 核心指标 ──────────────────────────

st.markdown("---")

c1, c2 = st.columns(2)
with c1:
    st.markdown(
        f"<div style='text-align:center;padding:24px;border-radius:12px;"
        f"background:{color}15;border:2px solid {color}30;'>"
        f"<span style='font-size:14px;color:#64748b;'>四线之上比例</span><br>"
        f"<span style='font-size:72px;font-weight:bold;color:{color};'>{ratio:.1f}%</span><br>"
        f"<span style='font-size:16px;color:{color};'>{counts['above_all']}/{total} 只 · {label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
with c2:
    st.metric("站上 200MA", f"{counts['above_200']/total*100:.1f}%  ({counts['above_200']}/{total})")
    st.metric("站上 50MA", f"{counts['above_50']/total*100:.1f}%  ({counts['above_50']}/{total})")
    st.metric("站上 21EMA", f"{counts['above_21']/total*100:.1f}%  ({counts['above_21']}/{total})")
    st.metric("站上 10EMA", f"{counts['above_10']/total*100:.1f}%  ({counts['above_10']}/{total})")

# ── 股票明细 ──────────────────────────

st.markdown("---")
st.subheader("股票明细")

rows = []
for r in sorted(results, key=lambda x: x["最新价"], reverse=True):
    all_above = r["10EMA"] and r["21EMA"] and r["50MA"] and r["200MA"]
    rows.append({
        "代码": r["代码"],
        "名称": r["名称"],
        "最新价": f"{r['最新价']:.2f}",
        "10EMA": "✅" if r["10EMA"] else "❌",
        "21EMA": "✅" if r["21EMA"] else "❌",
        "50MA": "✅" if r["50MA"] else "❌",
        "200MA": "✅" if r["200MA"] else "❌",
        "四线之上": "🟢" if all_above else "—",
    })

st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=400)
st.caption("EMA = 指数移动平均线 · MA = 简单移动平均线")
