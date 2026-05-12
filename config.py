"""
全局配置 — 所有可调参数集中管理，方便修改
"""

# --- 回测资金与费率 ---
INITIAL_CASH = 100_000       # 初始资金（元）
COMMISSION = 0.00025         # 佣金 万分之2.5
STAMP_DUTY = 0.0005          # 印花税 万分之5（仅卖出时收取）
MIN_COMMISSION = 5.0         # 最低佣金（元）
SLIPPAGE = 0.0005            # 滑点 万分之5
RISK_FREE_RATE = 0.02        # 无风险利率（用于夏普比率）

# --- 数据 ---
DATA_CACHE_DIR = "data_cache"  # 本地CSV缓存目录
AKSHARE_RETRIES = 3            # 网络请求重试次数
AKSHARE_RETRY_DELAY = 2        # 重试间隔（秒）

# --- 策略默认参数 ---
MA_CROSS_FAST = 5              # 双均线快线周期
MA_CROSS_SLOW = 20             # 双均线慢线周期

# --- 风控默认值 ---
MAX_DRAWDOWN_LIMIT = 0.15      # 最大回撤硬止损（15%）
POSITION_PERCENT = 0.95        # 每次交易使用资金比例
