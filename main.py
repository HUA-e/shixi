"""
A股量化回测系统 — 命令行入口
用法: python main.py --symbol 000001 --start 20230101 --end 20251231 --strategy ma_cross
"""
import argparse

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

from config import INITIAL_CASH
from backtest.engine import run_backtest
from web.strategy_config import (
    STRATEGY_CLASSES, STRATEGY_CONFIG, get_strategy_default_kwargs,
    convert_params_for_backtest,
)


def print_results(result):
    """格式化打印回测绩效"""
    print(f"\n{'─' * 45}")
    print(f"  初始资金:    {result['initial_value']:>12,.2f}")
    print(f"  最终资金:    {result['final_value']:>12,.2f}")
    print(f"  总收益率:    {result['total_return']:>11.2%}")
    print(f"{'─' * 45}")

    sharpe = result["sharpe"]
    sr = sharpe.get("sharperatio")
    if sr is not None:
        print(f"  夏普比率:    {sr:>10.2f}")

    dd = result["drawdown"]
    print(f"  最大回撤:    {dd.max.drawdown:>10.2f}%")
    print(f"  回撤持续:    {dd.max.len:>8} 天")

    trades = result["trades"]
    total = trades.get("total", {}).get("total", 0)
    won = trades.get("won", {}).get("total", 0)
    lost = trades.get("lost", {}).get("total", 0)
    print(f"  交易次数:    {total:>12}")
    print(f"  盈利/亏损:   {won:>8} / {lost:<8}")
    if total > 0:
        print(f"  胜率:        {won / total:>11.2%}")

    annret = result["annret"]
    if annret:
        print(f"\n  分年度收益率:")
        for year, ret in annret.items():
            print(f"     {year}:  {ret:>8.2%}")

    print(f"{'─' * 45}\n")


def _build_strategy_kwargs(args, strategy_key):
    """根据策略类型从命令行参数构建 kwargs"""
    meta = STRATEGY_CONFIG[strategy_key]
    kwargs = {k: getattr(args, k) for k in meta["params"] if hasattr(args, k)}
    return convert_params_for_backtest(strategy_key, kwargs)


def main():
    parser = argparse.ArgumentParser(
        description="A股量化回测系统 — 基于 Backtrader + AKShare",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --symbol 000001 --start 20230101 --end 20251231
  python main.py --symbol 600519 --start 20200101 --end 20251231 --strategy ma_cross --fast 10 --slow 30
        """,
    )
    parser.add_argument("--symbol", type=str, default="000001",
                        help="股票代码（默认 000001 平安银行）")
    parser.add_argument("--start", type=str, default="20230101",
                        help="回测起始日期 YYYYMMDD")
    parser.add_argument("--end", type=str, default="20251231",
                        help="回测结束日期 YYYYMMDD")
    parser.add_argument("--strategy", type=str, default="ma_cross",
                        choices=list(STRATEGY_CLASSES.keys()), help="策略名称")
    parser.add_argument("--cash", type=float, default=INITIAL_CASH,
                        help=f"初始资金（默认 {INITIAL_CASH:,}）")

    # 动态添加各策略的参数
    parser.add_argument("--fast", type=int, default=5, help="[ma_cross] 快线周期")
    parser.add_argument("--slow", type=int, default=20, help="[ma_cross] 慢线周期")
    parser.add_argument("--lookback", type=int, default=20, help="[momentum] 回顾周期")
    parser.add_argument("--bb-period", type=int, default=20, help="[mean_rev] 布林带周期")
    parser.add_argument("--entry-period", type=int, default=20, help="[turtle] 入场周期")
    parser.add_argument("--exit-period", type=int, default=10, help="[turtle] 出场周期")
    parser.add_argument("--no-plot", action="store_true",
                        help="不显示图表")
    args = parser.parse_args()

    strategy_cls = STRATEGY_CLASSES[args.strategy]
    strategy_kwargs = _build_strategy_kwargs(args, args.strategy)

    print(f"\n{'=' * 50}")
    print(f"  A股量化回测系统")
    print(f"  股票: {args.symbol}  策略: {args.strategy}")
    print(f"  区间: {args.start} ~ {args.end}")
    print(f"  初始资金: {args.cash:,.0f}")
    print(f"{'=' * 50}")

    result = run_backtest(
        strategy_cls, args.symbol, args.start, args.end,
        cash=args.cash, **strategy_kwargs,
    )

    print_results(result)

    if not args.no_plot:
        result["cerebro"].plot()
        plt.show()


if __name__ == "__main__":
    main()
