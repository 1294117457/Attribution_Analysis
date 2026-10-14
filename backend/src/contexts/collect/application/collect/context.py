"""采集上下文：所有 IO 依赖 + 并发配置

di 组装时构造一次，setup_collect 时绑定到每个 handler。
"""
from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Callable

from contexts.collect.application.port.collect_port import (
    CollectProgressPort,
    CollectTaskStorePort,
    ConceptStorePort,
    RawDataStorePort,
    StockUniversePort,
)
from contexts.data.application.port import DataGatewayPort

if False:  # TYPE_CHECKING 替代：避免循环 import
    from application.service import StockInfoService


@dataclass(frozen=True)
class CollectContext:
    """采集用例子系统的依赖容器"""

    gateway: DataGatewayPort
    raw_store: RawDataStorePort
    stocks: StockUniversePort
    concepts: ConceptStorePort
    tasks: CollectTaskStorePort
    progress: CollectProgressPort
    # 日 K / 股票清单复用 StockInfoService：每次调用开一个带 session 的 Service，退出时 commit
    stock_info: Callable[[], AbstractAsyncContextManager]
    concurrency: int = 1            # 原 settings.COLLECT_CONCURRENCY
    max_concurrency: int = 8        # 原 settings.COLLECT_MAX_CONCURRENCY


__all__ = ["CollectContext"]
