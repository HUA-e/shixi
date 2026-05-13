"""
港股市场宽度 — 200MA / 50MA / 21EMA / 10EMA 多头排列比例
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO

from web.components.styles import inject_styles
from data.hk_fetcher import fetch_hk_stock_list, fetch_hk_stock_hist

inject_styles()

st.title("港股市场宽度")
st.caption("恒生指数成分股中，价格同时站上 200MA / 50MA / 21EMA / 10EMA 的股票比例")

# ── 侧边栏 ──────────────────────────

with st.sidebar:
    st.header("参数设置")
    top_n = st.slider("分析股票数量（按成交额排名）", 20, 200, 100, 10)
    min_price = st.slider("最低股价（过滤仙股）", 0.5, 10.0, 1.0, 0.5)
    lookback_days = st.slider("历史回溯天数", 30, 365, 90, 30)
    workers = st.slider("并行线程数", 1, 10, 6, 1)
    run = st.button("刷新数据", type="primary", use_container_width=True)
    st.caption(f"数据来源：新浪财经 · 共 {top_n} 只港股")
    st.caption("首次加载较慢（需拉取历史数据），后续使用缓存秒出")

# ── 核心计算 ──────────────────────────

MA_PERIODS = {
    "10EMA": 10,
    "21EMA": 21,
    "50MA": 50,
    "200MA": 200,
}


def compute_stock_status(symbol, name, hist_days):
    """获取单只股票历史数据，计算每日是否满足4条均线条件"""
    try:
        df = fetch_hk_stock_hist(symbol)
        if df.empty or len(df) < 200:
            return None

        df["200MA"] = df["close"].rolling(200).mean()
        df["50MA"] = df["close"].rolling(50).mean()
        df["21EMA"] = df["close"].ewm(span=21, adjust=False).mean()
        df["10EMA"] = df["close"].ewm(span=10, adjust=False).mean()

        df = df.dropna()
        if df.empty:
            return None

        df["above_all"] = (
            (df["close"] > df["200MA"])
            & (df["close"] > df["50MA"])
            & (df["close"] > df["21EMA"])
            & (df["close"] > df["10EMA"])
        )
        df["above_200"] = df["close"] > df["200MA"]
        df["above_50"] = df["close"] > df["50MA"]
        df["above_21"] = df["close"] > df["21EMA"]
        df["above_10"] = df["close"] > df["10EMA"]

        return {
            "symbol": symbol,
            "name": name,
            "df": df,
            "latest": {
                "close": float(df["close"].iloc[-1]),
                "above_all": bool(df["above_all"].iloc[-1]),
                "above_200": bool(df["above_200"].iloc[-1]),
                "above_50": bool(df["above_50"].iloc[-1]),
                "above_21": bool(df["above_21"].iloc[-1]),
                "above_10": bool(df["above_10"].iloc[-1]),
            },
        }
    except Exception:
        return None


if run:
    with st.spinner("获取港股列表..."):
        stock_list = fetch_hk_stock_list(min_price=min_price, top_n=top_n)
        st.session_state["hk_stock_list"] = stock_list

    results = []
    total = len(stock_list)
    progress = st.progress(0, text=f"0/{total} ...")
    completed = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(compute_stock_status, row["代码"], row["名称"], lookback_days): row
            for _, row in stock_list.iterrows()
        }
        for f in as_completed(futures):
            completed += 1
            progress.progress(completed / total, text=f"{completed}/{total}")
            r = f.result()
            if r is not None:
                results.append(r)

    if not results:
        st.error("没有成功获取到任何股票数据")
        st.stop()

    # 计算每日市场宽度
    first_df = results[0]["df"]
    all_dates = first_df["date"].dt.strftime("%Y-%m-%d").tolist()

    # 对齐所有数据的日期，计算每日满足条件的比例
    date_series = first_df["date"]
    daily_ratios = []
    for _, r in enumerate(results):
        r["df"] = r["df"].set_index("date")

    for i, d in enumerate(date_series):
        day_count = 0
        above_count = 0
        for r in results:
            if d in r["df"].index:
                day_count += 1
                if r["df"].loc[d, "above_all"]:
                    above_count += 1
        ratio = above_count / day_count * 100 if day_count > 0 else 0
        daily_ratios.append({"date": d, "ratio": round(ratio, 1)})

    st.session_state["hk_results"] = results
    st.session_state["hk_daily_ratios"] = daily_ratios
    st.session_state["hk_last_update"] = date.today().isoformat()

# ── 展示 ──────────────────────────────

if "hk_results" not in st.session_state:
    st.info("在侧边栏点击「刷新数据」开始分析")
    st.stop()

results = st.session_state["hk_results"]
daily_ratios = st.session_state["hk_daily_ratios"]
last_update = st.session_state.get("hk_last_update", "?")

current_ratio = daily_ratios[-1]["ratio"]
above_count = sum(1 for r in results if r["latest"]["above_all"])
total_stocks = len(results)

# 颜色
if current_ratio > 60:
    ratio_color = "#10b981"  # 绿
    ratio_label = "强势"
elif current_ratio > 30:
    ratio_color = "#f59e0b"  # 黄
    ratio_label = "中性"
else:
    ratio_color = "#ef4444"  # 红
    ratio_label = "弱势"

st.success(f"数据更新于 {last_update}")

# ── 当前快照 ──────────────────────────

st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    st.metric("分析股票数", f"{total_stocks} 只")
with col2:
    st.markdown(
        f"<div style='text-align:center;padding:20px;border-radius:12px;background:{ratio_color}15;'>"
        f"<span style='font-size:14px;color:#64748b;'>市场宽度 — 四条均线之上</span><br>"
        f"<span style='font-size:64px;font-weight:bold;color:{ratio_color};'>{current_ratio:.0f}%</span><br>"
        f"<span style='font-size:18px;color:{ratio_color};'>{above_count}/{total_stocks} 只 · {ratio_label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
with col3:
    ma200 = sum(1 for r in results if r["latest"]["above_200"])
    ma50 = sum(1 for r in results if r["latest"]["above_50"])
    ma21 = sum(1 for r in results if r["latest"]["above_21"])
    ma10 = sum(1 for r in results if r["latest"]["above_10"])
    st.metric("站上200MA", f"{ma200/total_stocks*100:.0f}% ({ma200})")
    st.metric("站上50MA", f"{ma50/total_stocks*100:.0f}% ({ma50})")
    st.metric("站上21EMA", f"{ma21/total_stocks*100:.0f}% ({ma21})")
    st.metric("站上10EMA", f"{ma10/total_stocks*100:.0f}% ({ma10})")

# ── 历史趋势 ──────────────────────────

st.markdown("---")
st.subheader("市场宽度历史趋势")

df_ratios = pd.DataFrame(daily_ratios)
df_ratios["date"] = pd.to_datetime(df_ratios["date"])

# 只显示最近 lookback_days 天
cutoff = pd.Timestamp.now() - pd.Timedelta(days=lookback_days)
df_display = df_ratios[df_ratios["date"] >= cutoff]

fig = go.Figure()

# 背景色带
fig.add_hrect(y0=60, y1=100, fillcolor="#10b981", opacity=0.08, line_width=0)
fig.add_hrect(y0=30, y1=60, fillcolor="#f59e0b", opacity=0.08, line_width=0)
fig.add_hrect(y0=0, y1=30, fillcolor="#ef4444", opacity=0.08, line_width=0)

fig.add_trace(go.Scatter(
    x=df_display["date"], y=df_display["ratio"],
    mode="lines+markers", name="市场宽度",
    line=dict(color=ratio_color, width=2.5),
    marker=dict(size=4),
    fill="tozeroy", fillcolor=f"rgba({','.join(str(int(ratio_color[i:i+2], 16)) for i in (1, 3, 5))}, 0.15)",
    hovertemplate="%{x|%Y-%m-%d}<br>宽度: %{y:.1f}%<extra></extra>",
))

fig.add_hline(y=60, line_dash="dash", line_color="#10b981", opacity=0.5, annotation_text="强势线 60%")
fig.add_hline(y=30, line_dash="dash", line_color="#ef4444", opacity=0.5, annotation_text="弱势线 30%")

fig.update_layout(
    title=dict(text=f"港股市场宽度 · 近{lookback_days}天", font=dict(size=16)),
    xaxis=dict(title="", showgrid=True, gridcolor="#e5e7eb"),
    yaxis=dict(title="占比（%）", showgrid=True, gridcolor="#e5e7eb", range=[0, 100]),
    plot_bgcolor="white", paper_bgcolor="white",
    hovermode="x unified",
    height=420,
    margin=dict(l=60, r=30, t=40, b=30),
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── 股票明细表 ────────────────────────

st.markdown("---")
st.subheader("股票明细")

tab_cols = []
for r in sorted(results, key=lambda x: x["latest"]["close"], reverse=True):
    l = r["latest"]
    tab_cols.append({
        "代码": r["symbol"],
        "名称": r["name"],
        "最新价": f"{l['close']:.2f}",
        "10EMA": "✅" if l["above_10"] else "❌",
        "21EMA": "✅" if l["above_21"] else "❌",
        "50MA": "✅" if l["above_50"] else "❌",
        "200MA": "✅" if l["above_200"] else "❌",
        "四线之上": "🟢" if l["above_all"] else "⚪",
    })

table_df = pd.DataFrame(tab_cols)
st.dataframe(table_df, use_container_width=True, hide_index=True, height=400)

# ── 导出 ──────────────────────────────

csv = table_df.to_csv(index=False)
st.download_button(
    "📥 导出股票明细 CSV", csv,
    file_name=f"hk_breadth_{date.today().isoformat()}.csv",
    mime="text/csv",
)

# ── 四线解释 ──────────────────────────

with st.expander("📖 均线说明"):
    st.markdown("""
    | 均线 | 类型 | 含义 |
    |------|------|------|
    | **10日线** | EMA（指数移动平均） | 短线动能，反应最快 |
    | **21日线** | EMA（指数移动平均） | 短趋势，约一个月交易周期 |
    | **50日线** | MA（简单移动平均） | 中期趋势，约一个季度 |
    | **200日线** | MA（简单移动平均） | 长期趋势，约一年 |

    **市场宽度用法：**
    - **> 60%**：多数股票处于多头排列，市场强势，适合做多
    - **30%-60%**：市场分化，需精选个股
    - **< 30%**：极少数股票走强，市场弱势，适宜防守或空仓
    - **趋势方向比绝对值更重要**：宽度从低点回升是回暖信号，从高回落是降温信号
    """)

st.markdown("---")
st.caption("数据来源：新浪财经 · 仅供研究参考，不构成投资建议")
