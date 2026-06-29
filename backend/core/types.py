"""基础枚举类型"""

from enum import Enum


class MarketType(str, Enum):
    """市场类型"""

    SH = "sh"  # 上海
    SZ = "sz"  # 深圳
    BJ = "bj"  # 北京


class AnomalyType(str, Enum):
    """异常类型"""

    PRICE_SPIKE = "price_spike"  # 价格突刺
    PRICE_DROP = "price_drop"  # 价格暴跌
    VOLUME_SPIKE = "volume_spike"  # 成交量突刺
    VOLATILITY = "volatility"  # 波动率异常
    ZSCORE = "zscore"  # Z-Score 异常


class SentimentType(str, Enum):
    """情感类型"""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class CollectStatus(str, Enum):
    """采集状态"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
