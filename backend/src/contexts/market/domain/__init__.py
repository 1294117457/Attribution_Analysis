"""market domain - 领域层入口

按 DDD 方案，market 域的领域模型（Entity/VO/Repository）统一聚合在 entities/ 子目录下。
领域服务（跨聚合根的业务逻辑）聚合在 services/ 子目录下。

常用 import 简写：
    from contexts.market.domain.entities.kline.entity import Kline
    from contexts.market.domain.services.indicator_calculator import IndicatorCalculator
    from contexts.market.domain.exceptions import KlineNotFoundError
"""
from contexts.market.domain import entities, services
from contexts.market.domain.exceptions import (
    CollectionError,
    KlineDataError,
    KlineNotFoundError,
    StockNotFoundError,
)

__all__ = [
    "entities",
    "services",
    "CollectionError",
    "KlineDataError",
    "KlineNotFoundError",
    "StockNotFoundError",
]
