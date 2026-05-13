"""
港股数据获取 — 股票列表 + 历史K线，带本地缓存
"""
import os
import time
import akshare as ak
import pandas as pd

from config import DATA_CACHE_DIR, AKSHARE_RETRIES, AKSHARE_RETRY_DELAY

HK_CACHE_DIR = os.path.join(DATA_CACHE_DIR, "hk")
os.makedirs(HK_CACHE_DIR, exist_ok=True)


def fetch_hk_stock_list(min_price=1.0, top_n=100):
    """
    获取港股列表，按成交额降序取前 top_n 只（过滤仙股）。
    返回 DataFrame，含 代码、名称、最新价。
    """
    cache_file = os.path.join(HK_CACHE_DIR, "hk_stock_list.csv")
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, dtype={"代码": str})
        if not df.empty:
            return df

    for attempt in range(AKSHARE_RETRIES):
        try:
            spot = ak.stock_hk_spot()
            break
        except Exception:
            if attempt < AKSHARE_RETRIES - 1:
                time.sleep(AKSHARE_RETRY_DELAY * (attempt + 1))
            else:
                raise RuntimeError("获取港股列表失败")

    df = spot[spot["最新价"] >= min_price].copy()
    df = df.sort_values("成交额", ascending=False).head(top_n)
    df = df[["代码", "中文名称", "最新价"]].copy()
    df.columns = ["代码", "名称", "最新价"]
    df.to_csv(cache_file, index=False)
    return df


def fetch_hk_stock_hist(symbol, start_date="20240101", end_date="20260513"):
    """获取单只港股历史日线数据（前复权），带缓存"""
    cache_file = os.path.join(HK_CACHE_DIR, f"{symbol}_{start_date}_{end_date}.csv")
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
    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    df = df.sort_values("date").reset_index(drop=True)
    df.to_csv(cache_file, index=False)
    return df
