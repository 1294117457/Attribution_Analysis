"""实时接口（按需请求数据源 + Redis 缓存，不入库）"""

from infrastructure.adapter.realtime.base import BaseRealtimeQuery, is_trading_time, ttl_for
from infrastructure.adapter.realtime.concept_minute import ConceptMinuteQuery
from infrastructure.adapter.realtime.registry import get_realtime_registry, setup_realtime_registry
from infrastructure.adapter.realtime.stock_minute_kline import StockMinuteKlineQuery

__all__ = [
    "BaseRealtimeQuery",
    "ConceptMinuteQuery",
    "StockMinuteKlineQuery",
    "get_realtime_registry",
    "is_trading_time",
    "setup_realtime_registry",
    "ttl_for",
]
