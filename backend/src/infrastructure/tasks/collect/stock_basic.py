"""股票基本信息全量同步任务

迁移自 route/api/v1/collect_task.py::_collect_stock_basic
保留原行为：单元 = 1（整体一次性 fetch + upsert）。

配套设计文档：docs/dev/07collect-class/01-collect-task-class-design.md §5.3
"""

from __future__ import annotations

import logging

from application.stock_service import StockAppService
from infrastructure.collectors import get_registry
from infrastructure.collectors.protocols import StockBasicFetcher
from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.tasks.collect.base import (
    BaseCollectTask,
    TaskSummary,
    UnitResult,
)

logger = logging.getLogger(__name__)


class StockBasicCollectTask(BaseCollectTask):
    """股票基本信息全量同步（无明确单元，total=1）"""

    name = "stock_basic"

    # ── estimate_total ────────────────────────────────────────────────

    async def estimate_total(self, params: dict) -> int:
        """无明确单元，预估为 1"""
        return 1

    # ── run：业务主循环 ───────────────────────────────────────────────

    async def run(
        self,
        params: dict,
        on_unit_done,
    ) -> TaskSummary:
        fetcher = get_registry().get(StockBasicFetcher)
        logger.info("StockBasic 任务 %d 启动", self._task_id)

        try:
            async with AsyncSessionLocal() as session:
                svc = StockAppService(session=session)
                result = await svc.sync_stocks(
                    fetcher, list_status=params.get("list_status", "L")
                )
                await session.commit()

            await on_unit_done(
                UnitResult(
                    success=True,
                    detail="stock_basic",
                    saved_count=result.synced_count,
                ),
                "stock_basic",
            )
            return TaskSummary(
                success=1,
                fail=0,
                total_count=result.synced_count,
                message=result.message,
            )
        except Exception as e:
            logger.exception("StockBasic 任务 %d 失败", self._task_id)
            await on_unit_done(
                UnitResult(success=False, detail="stock_basic", error=str(e)),
                "stock_basic",
            )
            return TaskSummary(
                success=0,
                fail=1,
                message=str(e),
            )
