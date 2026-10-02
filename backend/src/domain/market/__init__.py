"""市场领域层（DDD.md §2.4）

市场相关领域知识（交易时段、缓存策略等）属于领域规则，
不属于任何单一实体，作为跨聚合根的领域服务存在。

配套设计文档：docs/dev/step2/04采集管理优化/06实时数据接口.md §3
"""
from domain.market.market_session import (
    MarketSessionService,
    MarketTimeZone,
    is_trading_time,
    market_now,
    ttl_for,
)

__all__ = [
    "MarketSessionService",
    "MarketTimeZone",
    "is_trading_time",
    "market_now",
    "ttl_for",
]