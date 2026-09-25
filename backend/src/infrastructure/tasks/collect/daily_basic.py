"""日频估值采集任务

迁移自 route/api/v1/collect_task.py::_collect_daily_basic
保留原行为：按 trade_date 维度单元，顺序循环。

配套设计文档：docs/dev/07collect-class/01-collect-task-class-design.md §5.2
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from infrastructure.collectors import get_registry
from infrastructure.collectors.protocols import DailyBasicFetcher
from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.repositories.fin_daily_basic_repository import (
    FinDailyBasicRepoImpl,
)
from infrastructure.tasks.collect.base import (
    BaseCollectTask,
    TaskSummary,
    UnitResult,
)

logger = logging.getLogger(__name__)


class DailyBasicCollectTask(BaseCollectTask):
    """日频估值采集（按 trade_date 维度单元）"""

    name = "daily_basic"

    # ── estimate_total ────────────────────────────────────────────────

    async def estimate_total(self, params: dict) -> int:
        """按 days / trade_date 计单元数"""
        return len(self._resolve_dates(params))

    # ── run：业务主循环 ───────────────────────────────────────────────

    async def run(
        self,
        params: dict,
        on_unit_done,
    ) -> TaskSummary:
        dates = self._resolve_dates(params)
        fetcher = get_registry().get(DailyBasicFetcher)

        success = fail = total_saved = 0
        logger.info(
            "DailyBasic 任务 %d 启动: %d 个日期 %s",
            self._task_id, len(dates), dates,
        )

        for d in dates:
            try:
                bo_list = await asyncio.to_thread(fetcher.fetch_daily_basic, d)
                if bo_list:
                    entities = [bo.to_entity() for bo in bo_list]
                    async with AsyncSessionLocal() as session:
                        repo = FinDailyBasicRepoImpl(session)
                        saved = await repo.save_batch(entities)
                        await session.commit()
                        total_saved += saved
                    await on_unit_done(
                        UnitResult(success=True, detail=d, saved_count=saved),
                        d,
                    )
                    logger.info("任务 %d 估值 %s: 写入 %d 条",
                                self._task_id, d, saved)
                else:
                    logger.info("任务 %d 估值 %s: 无数据（非交易日？）",
                                self._task_id, d)
                    await on_unit_done(
                        UnitResult(success=True, detail=d, saved_count=0,
                                   skipped=True),
                        d,
                    )
                success += 1
            except Exception as e:
                logger.warning("任务 %d 估值 %s 失败: %s", self._task_id, d, e)
                await on_unit_done(
                    UnitResult(success=False, detail=d, error=str(e)),
                    d,
                )
                fail += 1

        return TaskSummary(
            success=success,
            fail=fail,
            total_count=len(dates),
            message=(
                f"完成: {success} 天, {total_saved} 条"
            ),
        )

    # ── helper ────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_dates(params: dict) -> list[str]:
        """按 trade_date / days 解析需要采集的日期列表"""
        trade_date = params.get("trade_date")
        if trade_date:
            return [trade_date]
        days = params.get("days", 1)
        today = date.today()
        return [
            (today - timedelta(days=i)).strftime("%Y%m%d")
            for i in range(days)
        ]
