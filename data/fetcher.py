"""
AKShare 数据获取 — A股历史行情 + 股票列表，带本地CSV缓存和网络重试
主接口: 东方财富 (stock_zh_a_hist) | 备用: 新浪 (stock_zh_a_daily)
"""
import os
import time
import akshare as ak
import pandas as pd

from config import DATA_CACHE_DIR, AKSHARE_RETRIES, AKSHARE_RETRY_DELAY


def _cache_path(filename):
    os.makedirs(DATA_CACHE_DIR, exist_ok=True)
    return os.path.join(DATA_CACHE_DIR, filename)


def _to_sina_symbol(symbol):
    """将股票代码转为新浪格式：000001 -> sz000001, 600519 -> sh600519"""
    if symbol.startswith(("0", "3")):
        return f"sz{symbol}"
    elif symbol.startswith(("6", "9")):
        return f"sh{symbol}"
    else:
        raise ValueError(f"不支持的股票代码格式: {symbol}")


def _try_fetch_eastmoney(symbol, start_date, end_date, period, adjust):
    """尝试通过东方财富获取数据"""
    for attempt in range(AKSHARE_RETRIES):
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol, period=period,
                start_date=start_date, end_date=end_date, adjust=adjust
            )
            if df is not None and not df.empty:
                return df
        except Exception as e:
            if attempt < AKSHARE_RETRIES - 1:
                wait = AKSHARE_RETRY_DELAY * (attempt + 1)
                print(f"  [东方财富 重试 {attempt+1}/{AKSHARE_RETRIES}] 等待 {wait}s ...")
                time.sleep(wait)
            else:
                print(f"  [东方财富] 失败: {e}")
    return None


def _try_fetch_sina(symbol, start_date, end_date, adjust):
    """通过新浪接口获取数据（备用）"""
    sina_sym = _to_sina_symbol(symbol)
    for attempt in range(AKSHARE_RETRIES):
        try:
            df = ak.stock_zh_a_daily(
                symbol=sina_sym, start_date=start_date,
                end_date=end_date, adjust=adjust
            )
            if df is not None and not df.empty:
                return df
        except Exception as e:
            if attempt < AKSHARE_RETRIES - 1:
                wait = AKSHARE_RETRY_DELAY * (attempt + 1)
                print(f"  [新浪 重试 {attempt+1}/{AKSHARE_RETRIES}] 等待 {wait}s ...")
                time.sleep(wait)
            else:
                print(f"  [新浪] 失败: {e}")
    return None


def fetch_stock_hist(symbol, start_date, end_date, period="daily", adjust="qfq"):
    """获取单只A股的历史K线数据（前复权），优先从本地缓存读取。
    主数据源：东方财富  备用数据源：新浪"""
    cache_file = _cache_path(f"{symbol}_{start_date}_{end_date}_{period}_{adjust}.csv")
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True, date_format="%Y-%m-%d")
        if not df.empty:
            return df

    # 优先尝试东方财富
    df = _try_fetch_eastmoney(symbol, start_date, end_date, period, adjust)

    # 东方财富失败则回退到新浪
    if df is None:
        print("  [切换数据源] 东方财富不可用，尝试新浪接口 ...")
        df = _try_fetch_sina(symbol, start_date, end_date, adjust)

    if df is not None and not df.empty:
        df.to_csv(cache_file)
        return df

    raise RuntimeError(f"获取 {symbol} 历史数据失败：所有数据源均不可用")


def fetch_stock_list():
    """获取A股全部股票代码和名称列表（带缓存）"""
    cache_file = _cache_path("stock_list.csv")
    if os.path.exists(cache_file):
        return pd.read_csv(cache_file, dtype={"代码": str})

    # 尝试东方财富，失败则用新浪
    try:
        df = ak.stock_zh_a_spot_em()
        df = df[["代码", "名称"]].copy()
    except Exception:
        try:
            df = ak.stock_info_a_code_name()
        except Exception:
            raise RuntimeError("获取股票列表失败：所有数据源均不可用")

    df.to_csv(cache_file, index=False)
    return df


def fetch_index_hist(symbol="000300", start_date="20240101", end_date="20260512"):
    """
    获取指数历史日线数据（用于基准对比）。
    默认沪深300（000300），也可传入 000001（上证指数）、399001（深证成指）等。
    返回与 fetch_stock_hist 相同格式的 DataFrame。
    """
    akshare_symbol = f"sh{symbol}" if symbol.startswith("0") else f"sz{symbol}"
    cache_file = _cache_path(f"index_{symbol}_{start_date}_{end_date}.csv")
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True, date_format="%Y-%m-%d")
        if not df.empty:
            return df

    for attempt in range(AKSHARE_RETRIES):
        try:
            df = ak.stock_zh_index_daily(symbol=akshare_symbol)
            if df is not None and not df.empty:
                break
        except Exception:
            if attempt < AKSHARE_RETRIES - 1:
                time.sleep(AKSHARE_RETRY_DELAY * (attempt + 1))
            else:
                raise RuntimeError(f"获取指数 {symbol} 数据失败")

    df = df.rename(columns={"date": "date"} if "date" in df.columns else {})
    if "date" not in df.columns:
        df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    df = df.sort_values("date")
    df.to_csv(cache_file)
    return df
