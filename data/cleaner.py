"""
数据清洗 — AKShare 中文列名映射到 backtrader 标准格式
"""
import pandas as pd

COL_MAP = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
}


def clean_for_backtrader(df):
    """将 akshare 返回的 DataFrame 转为 backtrader PandasData 所需格式"""
    df = df.rename(columns=COL_MAP)
    keep_cols = ["date", "open", "close", "high", "low", "volume"]
    df = df[keep_cols].copy()

    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)

    # 价格取整2位小数，成交量取整
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].round(2)
    df["volume"] = df["volume"].round(0).astype(int)

    df["openinterest"] = 0
    df.ffill(inplace=True)

    return df
