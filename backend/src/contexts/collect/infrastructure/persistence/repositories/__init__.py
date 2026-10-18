"""contexts.collect.infrastructure.persistence.repositories

SQL/ORM 实现 domain 协议（Protocol）。
- KlineRepository / StockInfoRepository  （已有的 tech/fundamental）

所有 repo 不暴露 ORM 对象给上层，方法返回的都是 domain 聚合根。

⚠️ SqlCollectScheduleRepository / SqlCollectRunLogRepository
   已在 step7 拆分中移至 `contexts.scheduler.infrastructure.persistence.repositories`，
   collect 模块不再持有调度相关仓储。
"""
from contexts.collect.infrastructure.persistence.repositories.kline_repo import (
    KlineRepository,
)
from contexts.collect.infrastructure.persistence.repositories.stock_info_repo import (
    StockInfoRepository,
)

__all__ = [
    "KlineRepository",
    "StockInfoRepository",
]
