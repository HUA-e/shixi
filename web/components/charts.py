"""
交互式图表 — 资金曲线、回撤、月度热力图、年度收益、K线图
"""
import plotly.graph_objects as go
import pandas as pd
import numpy as np

COLORS = {
    "primary": "#2563eb",
    "success": "#10b981",
    "danger": "#ef4444",
    "grid": "#e5e7eb",
}
# 统一图表边距，保证标题和图例不粘连
MARGIN = dict(l=60, r=30, t=60, b=40)
TITLE_FONT = dict(size=16, color="#1e293b")


def plot_equity_curve(net_values, initial_value, buy_hold_curve=None, trades=None):
    fig = go.Figure()
    x = list(range(len(net_values)))

    fig.add_trace(go.Scatter(
        x=x, y=net_values, mode="lines", name="策略权益",
        line=dict(color=COLORS["primary"], width=2.5),
        hovertemplate="策略权益: %{y:,.0f}<extra></extra>",
    ))
    fig.add_hline(y=initial_value, line_dash="dash", line_color="#94a3b8",
                  annotation_text="初始资金", annotation_position="right", opacity=0.6)

    if buy_hold_curve and len(buy_hold_curve) == len(net_values):
        fig.add_trace(go.Scatter(
            x=x, y=buy_hold_curve, mode="lines", name="买入持有",
            line=dict(color="#94a3b8", width=1.5, dash="dot"), opacity=0.7,
            hovertemplate="买入持有: %{y:,.0f}<extra></extra>",
        ))

    if trades:
        for t in trades:
            try:
                bi, bp = t.get("buy_bar"), t.get("buy_price", 0)
                si, sp = t.get("sell_bar"), t.get("sell_price", 0)
                if bi is not None:
                    fig.add_trace(go.Scatter(
                        x=[bi], y=[bp], mode="markers",
                        marker=dict(color=COLORS["success"], size=10, symbol="triangle-up",
                                   line=dict(color="white", width=1)),
                        showlegend=False,
                        text=[f"买入 {t.get('buy_date','')} @ {bp:.2f}"], hoverinfo="text",
                    ))
                if si is not None:
                    fig.add_trace(go.Scatter(
                        x=[si], y=[sp], mode="markers",
                        marker=dict(color=COLORS["danger"], size=10, symbol="triangle-down",
                                   line=dict(color="white", width=1)),
                        showlegend=False,
                        text=[f"卖出 {t.get('sell_date','')} @ {sp:.2f}"], hoverinfo="text",
                    ))
            except Exception:
                pass

    fig.update_layout(
        title=dict(text="资金曲线", font=TITLE_FONT),
        xaxis=dict(title="交易日", showgrid=True, gridcolor=COLORS["grid"], zeroline=False),
        yaxis=dict(title="账户价值（元）", showgrid=True, gridcolor=COLORS["grid"],
                   tickformat=",.0f", zeroline=False),
        hovermode="x unified",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=MARGIN,
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0,
                   bgcolor="rgba(255,255,255,0.8)", bordercolor="#e5e7eb", borderwidth=1),
    )
    return fig


def plot_drawdown(net_values):
    if not net_values or len(net_values) < 2:
        return go.Figure()

    peak = net_values[0]
    drawdowns = []
    for v in net_values:
        peak = max(peak, v)
        drawdowns.append((v - peak) / peak * 100)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(drawdowns))), y=drawdowns, mode="lines",
        fill="tozeroy", fillcolor="rgba(239,68,68,0.1)",
        line=dict(color=COLORS["danger"], width=1.5),
        name="回撤",
        hovertemplate="回撤: %{y:.2f}%<extra></extra>",
    ))

    max_dd = min(drawdowns)
    max_dd_idx = drawdowns.index(max_dd)
    fig.add_trace(go.Scatter(
        x=[max_dd_idx], y=[max_dd], mode="markers+text",
        marker=dict(color=COLORS["danger"], size=8),
        text=[f"最大 {max_dd:.1f}%"], textposition="bottom center",
        name="最大回撤", showlegend=False,
    ))

    fig.update_layout(
        title=dict(text="回撤分析", font=TITLE_FONT),
        xaxis=dict(title="交易日", showgrid=True, gridcolor=COLORS["grid"], zeroline=False),
        yaxis=dict(title="回撤（%）", showgrid=True, gridcolor=COLORS["grid"], zeroline=False),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=MARGIN,
    )
    return fig


def plot_monthly_heatmap(monthly_returns):
    if not monthly_returns:
        return go.Figure()

    records = []
    for ds, ret in monthly_returns.items():
        try:
            d = pd.Timestamp(ds)
            records.append({"year": d.year, "month": d.month, "return": ret})
        except Exception:
            continue
    if not records:
        return go.Figure()

    df = pd.DataFrame(records)
    pivoted = df.pivot(index="year", columns="month", values="return")
    months = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]

    fig = go.Figure(data=go.Heatmap(
        z=pivoted.values,
        x=[months[m-1] for m in pivoted.columns],
        y=[str(y) for y in pivoted.index],
        text=[[f"{v:.1f}%" if pd.notna(v) else "" for v in row] for row in pivoted.values],
        texttemplate="%{text}",
        colorscale=[[0, "#ef4444"], [0.5, "#ffffff"], [1, "#10b981"]],
        zmid=0, showscale=True,
        colorbar=dict(title="收益%", thickness=15),
        hovertemplate="%{y} %{x}<br>收益: %{z:.2f}%<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="月度收益热力图", font=TITLE_FONT),
        xaxis=dict(title="", side="top"),
        yaxis=dict(title="", autorange="reversed"),
        plot_bgcolor="white", paper_bgcolor="white",
        height=max(160, 80 + 40 * len(pivoted)),
        margin=MARGIN,
    )
    return fig


def plot_annual_returns(annret):
    if not annret:
        return go.Figure()

    years = list(annret.keys())
    values = [annret[y] * 100 for y in years]
    colors = [COLORS["success"] if v >= 0 else COLORS["danger"] for v in values]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[str(y) for y in years], y=values,
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in values], textposition="outside",
        textfont=dict(size=12),
        hovertemplate="%{x}年: %{y:.2f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="#64748b", line_width=0.5)

    fig.update_layout(
        title=dict(text="年度收益率", font=TITLE_FONT),
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="收益率（%）", showgrid=True, gridcolor=COLORS["grid"], zeroline=False),
        plot_bgcolor="white", paper_bgcolor="white",
        showlegend=False,
        margin=MARGIN,
    )
    return fig


def plot_kline(df, ma_periods=(5, 20, 60), trades=None):
    if df is None or df.empty:
        return go.Figure()

    plot_df = df.tail(180).copy().reset_index()
    date_col = plot_df.columns[0]
    plot_df[date_col] = pd.to_datetime(plot_df[date_col])

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=plot_df[date_col],
        open=plot_df["open"], high=plot_df["high"],
        low=plot_df["low"], close=plot_df["close"],
        name="K线",
        increasing=dict(line=dict(color=COLORS["danger"]), fillcolor=COLORS["danger"]),
        decreasing=dict(line=dict(color=COLORS["success"]), fillcolor=COLORS["success"]),
        hovertemplate="%{x|%Y-%m-%d}<br>开 %{open:.2f} 高 %{high:.2f}<br>低 %{low:.2f} 收 %{close:.2f}<extra></extra>",
    ))

    ma_colors = {5: "#f59e0b", 20: COLORS["primary"], 60: "#8b5cf6"}
    for p in ma_periods:
        if len(plot_df) < p:
            continue
        ma = plot_df["close"].rolling(window=p).mean()
        fig.add_trace(go.Scatter(
            x=plot_df[date_col], y=ma, mode="lines",
            line=dict(width=1.2, color=ma_colors.get(p, "#94a3b8")),
            name=f"MA{p}",
        ))

    if trades:
        for t in trades:
            try:
                bd_str, sd_str = t.get("buy_date", ""), t.get("sell_date", "")
                bp, sp = t.get("buy_price", 0), t.get("sell_price", 0)
                if bp and bd_str:
                    fig.add_trace(go.Scatter(
                        x=[pd.to_datetime(bd_str)], y=[bp], mode="markers",
                        marker=dict(color=COLORS["success"], size=12, symbol="triangle-up",
                                   line=dict(color="white", width=1)),
                        name="买入", showlegend=False,
                        text=[f"买入 {bd_str} @ {bp:.2f}"], hoverinfo="text",
                    ))
                if sp and sd_str:
                    fig.add_trace(go.Scatter(
                        x=[pd.to_datetime(sd_str)], y=[sp], mode="markers",
                        marker=dict(color=COLORS["danger"], size=12, symbol="triangle-down",
                                   line=dict(color="white", width=1)),
                        name="卖出", showlegend=False,
                        text=[f"卖出 {sd_str} @ {sp:.2f}"], hoverinfo="text",
                    ))
            except Exception:
                pass

    fig.update_layout(
        title=dict(text="K线图", font=TITLE_FONT),
        xaxis=dict(title="", showgrid=True, gridcolor=COLORS["grid"], zeroline=False),
        yaxis=dict(title="价格（元）", showgrid=True, gridcolor=COLORS["grid"], zeroline=False),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0,
                   bgcolor="rgba(255,255,255,0.8)"),
        margin=MARGIN,
        height=500,
    )
    return fig


def plot_optimization_heatmap(param1_values, param2_values, returns_matrix, param1_name, param2_name):
    fig = go.Figure(data=go.Heatmap(
        z=returns_matrix,
        x=[str(v) for v in param2_values],
        y=[str(v) for v in param1_values],
        colorscale=[[0, "#ef4444"], [0.5, "#ffffff"], [1, "#10b981"]],
        zmid=0,
        text=[[f"{v:.2%}" for v in row] for row in returns_matrix],
        texttemplate="%{text}",
        colorbar=dict(title="收益率", thickness=15),
        hovertemplate=f"{param2_name}: %{{x}}<br>{param1_name}: %{{y}}<br>收益: %{{z:.2%}}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text=f"参数优化 · {param1_name} × {param2_name}", font=TITLE_FONT),
        xaxis=dict(title=param2_name),
        yaxis=dict(title=param1_name),
        plot_bgcolor="white", paper_bgcolor="white",
        height=450,
        margin=MARGIN,
    )
    return fig
