"""
港股数据获取 — 使用新浪数据源（akshare封装）
"""
import os
import time
import akshare as ak
import pandas as pd

from config import DATA_CACHE_DIR, AKSHARE_RETRIES, AKSHARE_RETRY_DELAY

HK_CACHE = os.path.join(DATA_CACHE_DIR, "hk")
os.makedirs(HK_CACHE, exist_ok=True)


def fetch_hk_stocks(top_n=82):
    """获取港股列表，按成交额降序取前 top_n 只（模拟恒生指数成分股覆盖范围）"""
    cache_file = os.path.join(HK_CACHE, "hk_stocks.csv")
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, dtype={"代码": str})
        if not df.empty:
            return df.head(top_n)

    for attempt in range(AKSHARE_RETRIES):
        try:
            spot = ak.stock_hk_spot()
            break
        except Exception:
            if attempt < AKSHARE_RETRIES - 1:
                time.sleep(AKSHARE_RETRY_DELAY * (attempt + 1))
            else:
                raise RuntimeError("获取港股列表失败")

    df = spot[spot["最新价"] >= 1.0].copy()
    df = df.sort_values("成交额", ascending=False).head(top_n)
    df = df[["代码", "中文名称", "最新价"]].rename(columns={"中文名称": "名称"})
    df.to_csv(cache_file, index=False)
    return df


def fetch_hk_hist(symbol):
    """获取单只港股全部历史日线（前复权），带缓存"""
    cache_file = os.path.join(HK_CACHE, f"{symbol}.csv")
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, parse_dates=["date"])
        if not df.empty:
            return df

    for attempt in range(AKSHARE_RETRIES):
        try:
            df = ak.stock_hk_daily(symbol=symbol, adjust="qfq")
            break
        except Exception:
            if attempt < AKSHARE_RETRIES - 1:
                time.sleep(AKSHARE_RETRY_DELAY * (attempt + 1))
            else:
                raise RuntimeError(f"获取港股 {symbol} 数据失败")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df.to_csv(cache_file, index=False)
    return df
