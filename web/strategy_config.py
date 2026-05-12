"""
策略统一配置 — 所有参数定义的唯一来源
sidebar、main.py、各页面均从此导入
"""
from strategies.ma_cross import MACrossStrategy
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.turtle import TurtleStrategy

POPULAR_STOCKS = [
    "000001 平安银行", "000002 万科A", "000333 美的集团", "000651 格力电器",
    "000858 五粮液", "002415 海康威视", "300750 宁德时代", "600000 浦发银行",
    "600036 招商银行", "600276 恒瑞医药", "600519 贵州茅台", "600585 海螺水泥",
    "600887 伊利股份", "601012 隆基绿能", "601318 中国平安", "601398 工商银行",
    "601888 中国中免", "603259 药明康德", "603288 海天味业",
]

STRATEGY_CLASSES = {
    "ma_cross": MACrossStrategy,
    "momentum": MomentumStrategy,
    "mean_rev": MeanReversionStrategy,
    "turtle": TurtleStrategy,
}

STRATEGY_CONFIG = {
    "ma_cross": {
        "name": "双均线交叉",
        "icon": "📊",
        "desc": "短期均线上穿长期均线时买入，下穿时卖出。最经典的趋势跟踪策略。",
        "suit": "趋势行情",
        "risk": "低",
        "params": {
            "fast": {"label": "快线周期", "type": "int", "min": 2, "max": 60, "default": 5,
                     "help": "短期均线，值越小信号越灵敏"},
            "slow": {"label": "慢线周期", "type": "int", "min": 5, "max": 120, "default": 20,
                     "help": "长期均线，值越大过滤噪音越多"},
        },
        "presets": {
            "⚡ 短线": {"fast": 3, "slow": 10},
            "📐 默认": {"fast": 5, "slow": 20},
            "🗓 中线": {"fast": 10, "slow": 30},
            "🏛 长线": {"fast": 20, "slow": 60},
        },
    },
    "momentum": {
        "name": "动量突破",
        "icon": "🚀",
        "desc": "价格突破N日最高价入场，移动止损跟踪利润。适合强势股。",
        "suit": "牛市/强势股",
        "risk": "中",
        "params": {
            "lookback": {"label": "回顾周期", "type": "int", "min": 5, "max": 60, "default": 20,
                         "help": "突破N日最高价时买入"},
            "ma_period": {"label": "趋势过滤MA", "type": "int", "min": 20, "max": 120, "default": 60,
                          "help": "价格在MA上方才允许买入"},
            "trail_pct": {"label": "移动止损 (%)", "type": "float", "min": 1.0, "max": 15.0, "default": 6.0,
                          "help": "从最高点回撤超过此比例即卖出"},
        },
        "presets": {
            "⚡ 激进": {"lookback": 10, "ma_period": 30, "trail_pct": 8},
            "📐 默认": {"lookback": 20, "ma_period": 60, "trail_pct": 6},
            "🛡 稳健": {"lookback": 30, "ma_period": 90, "trail_pct": 4},
        },
    },
    "mean_rev": {
        "name": "均值回归",
        "icon": "🔄",
        "desc": "价格触及布林带下轨且超卖时买入，回到上轨或超买时卖出。",
        "suit": "震荡市",
        "risk": "中",
        "params": {
            "bb_period": {"label": "布林带周期", "type": "int", "min": 10, "max": 50, "default": 20,
                          "help": "布林带中轨的移动平均周期"},
            "bb_dev": {"label": "标准差倍数", "type": "float", "min": 1.0, "max": 3.0, "default": 2.0,
                       "help": "上下轨宽度，越大越宽"},
            "rsi_period": {"label": "RSI周期", "type": "int", "min": 7, "max": 30, "default": 14,
                           "help": "超买超卖判断周期"},
        },
        "presets": {
            "📐 默认": {"bb_period": 20, "bb_dev": 2.0, "rsi_period": 14},
            "📏 宽轨": {"bb_period": 20, "bb_dev": 2.5, "rsi_period": 14},
            "📐 窄轨": {"bb_period": 10, "bb_dev": 1.5, "rsi_period": 10},
        },
    },
    "turtle": {
        "name": "海龟交易法",
        "icon": "🐢",
        "desc": "突破唐奇安通道入场，ATR动态止损。Richard Dennis的传奇系统。",
        "suit": "中长期趋势",
        "risk": "高",
        "params": {
            "entry_period": {"label": "入场周期", "type": "int", "min": 10, "max": 60, "default": 20,
                             "help": "突破N日最高价入场"},
            "exit_period": {"label": "出场周期", "type": "int", "min": 5, "max": 30, "default": 10,
                            "help": "跌破N日最低价出场"},
            "atr_stop": {"label": "ATR止损倍数", "type": "float", "min": 1.0, "max": 4.0, "default": 2.0,
                         "help": "止损距离 = N × ATR"},
        },
        "presets": {
            "🐢 系统1": {"entry_period": 20, "exit_period": 10, "atr_stop": 2.0},
            "🐢 系统2": {"entry_period": 55, "exit_period": 20, "atr_stop": 2.0},
            "⚡ 激进": {"entry_period": 15, "exit_period": 7, "atr_stop": 1.5},
        },
    },
}


def get_strategy_display_name(key):
    cfg = STRATEGY_CONFIG.get(key, {})
    return f"{cfg.get('icon', '')} {cfg.get('name', key)}"


def get_strategy_default_kwargs(strategy_key):
    """从预设中获取默认回测参数"""
    config = STRATEGY_CONFIG.get(strategy_key)
    if not config:
        return {}
    presets = config["presets"]
    default_preset = presets.get("📐 默认") or presets.get("🐢 系统1") or next(iter(presets.values()))
    return dict(default_preset)


def convert_params_for_backtest(strategy_key, params):
    """将UI参数转换为回测引擎需要的格式（如百分比转小数）"""
    result = dict(params)
    if strategy_key == "momentum" and "trail_pct" in result:
        result["trail_pct"] = result["trail_pct"] / 100
    return result
