"""market.domain.services - 跨领域模型的领域服务

3 个核心服务：
- indicator_calculator: K线技术指标计算（MA/MACD/KDJ/RSI/BOLL）
- signal_detector: 技术信号检测（金叉/死叉/超买超卖）
- market_session: 交易日判断（盘前/盘中/盘后）
"""
from contexts.market.domain.services.indicator_calculator import (
    WARMUP_BARS,
    IndicatorCalculator,
)
from contexts.market.domain.services.market_session import market_now, ttl_for
from contexts.market.domain.services.signal_detector import SignalDetector

__all__ = [
    "WARMUP_BARS",
    "IndicatorCalculator",
    "market_now",
    "ttl_for",
    "SignalDetector",
]
