"""股票基本信息全量同步任务

单元 = "all"（整体一次性 fetch + upsert）。
业务入口 POST /stocks/sync 经 CollectManageService.run_one 复用 collect_one，
UnitResult.data 为 SyncStockResponse 字段。
"""
from __future__ import annotations

import logging

from application.collect.task import BaseCollectTask, UnitResult
from application.port.data.reference import StockBasicPort

logger = logging.getLogger(__name__)


class StockBasicCollectTask(BaseCollectTask):
    """股票基本信息全量同步（单元只有一个）"""

    name = "stock_basic"
    facet = StockBasicPort.facet
    sub_facet = StockBasicPort.sub_facet
    label = StockBasicPort.label
    description = StockBasicPort.description
    default_params = {"list_status": "L"}

    async def list_units(self, params: dict) -> list[str]:
        return ["all"]

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        async with self.ctx.stock_info() as svc:
            result = await svc.sync_stocks(list_status=params.get("list_status", "L"))
        return UnitResult(
            success=True,
            detail=result.message,
            saved_count=result.synced_count,
            data=result.model_dump(),
        )


__all__ = ["StockBasicCollectTask"]
