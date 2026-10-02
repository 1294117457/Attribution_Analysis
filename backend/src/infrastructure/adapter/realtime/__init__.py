"""实时接口（按需请求数据源 + Redis 缓存，不入库）

模块组成：
- BaseRealtimeQuery：协议基类（cache_key / fetch / fallback / normalize）
- framework：实时查询框架（缓存 / 单飞 / 同源限流 / 降级 / 统计）—— 技术框架，非业务服务
- registry：实时接口注册中心（main.py lifespan 初始化）
- concept_minute / stock_minute_kline：两个内置实现

交易时段相关领域规则（is_trading_time / ttl_for / market_now）已迁移到 domain.market，
本包提供兼容 shim（从 realtime.base 仍可导入）。
"""
from infrastructure.adapter.realtime.base import BaseRealtimeQuery, is_trading_time, ttl_for
from infrastructure.adapter.realtime.concept_minute import ConceptMinuteQuery
from infrastructure.adapter.realtime.framework import (
    RealtimeQueryError,
    RealtimeQueryFramework,
    RealtimeResult,
    get_realtime_query_framework,
)
from infrastructure.adapter.realtime.registry import get_realtime_registry, setup_realtime_registry
from infrastructure.adapter.realtime.stock_minute_kline import StockMinuteKlineQuery

__all__ = [
    # 基类
    "BaseRealtimeQuery",
    # 框架（替代旧 RealtimeAppService）
    "RealtimeQueryFramework",
    "RealtimeQueryError",
    "RealtimeResult",
    "get_realtime_query_framework",
    # 注册表
    "get_realtime_registry",
    "setup_realtime_registry",
    # 领域规则（兼容 shim）
    "is_trading_time",
    "ttl_for",
    # 实现
    "ConceptMinuteQuery",
    "StockMinuteKlineQuery",
]