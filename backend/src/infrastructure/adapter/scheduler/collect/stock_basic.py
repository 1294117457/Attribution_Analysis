"""股票基本信息全量同步任务

单元 = "all"（整体一次性 fetch + upsert）。
业务入口 POST /stocks/sync 经 CollectAppService.run_one 复用 collect_one，
UnitResult.data 为 SyncStockResponse 字段。
"""

from __future__ import annotations

import logging

from application.service.stock_app_service import StockAppService
from infrastructure.adapter import get_registry
from application.port.collector_port import StockBasicFetcher
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    UnitResult,
)

logger = logging.getLogger(__name__)


class StockBasicCollectTask(BaseCollectTask):
    """股票基本信息全量同步（单元只有一个）"""

    name = "stock_basic"
    facet = "fundamental"
    sub_facet = "core"
    label = "股票基本信息"
    description = "全量代码/名称/行业/上市信息（5000+ 只）"
    default_params = {"list_status": "L"}

    async def list_units(self, params: dict) -> list[str]:
        return ["all"]

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        fetcher = get_registry().get(StockBasicFetcher)
        async with AsyncSessionLocal() as session:
            result = await StockAppService(session=session).sync_stocks(
                fetcher, list_status=params.get("list_status", "L")
            )
            await session.commit()
        return UnitResult(
            success=True,
            detail=result.message,
            saved_count=result.synced_count,
            data=result.model_dump(),
        )
