"""日频估值采集任务

单元 = 交易日（YYYYMMDD），collect_one 采一天全市场估值并落库。
业务入口 POST /stocks/sync-daily-basic 经 CollectAppService.run_one 复用 collect_one。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from infrastructure.adapter import get_registry
from application.port.collector_port import DailyBasicFetcher
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.repositories.fin_daily_basic_repository import (
    FinDailyBasicRepoImpl,
)
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    UnitResult,
    UnitTally,
)

logger = logging.getLogger(__name__)


class DailyBasicCollectTask(BaseCollectTask):
    """日频估值采集（按 trade_date 维度单元）"""

    name = "daily_basic"
    facet = "fundamental"
    sub_facet = "valuation"
    label = "日频估值"
    description = "PE / PB / PS / 股息率 + 股本市值 + 换手率 / 量比"
    default_params = {"days": 1}

    async def list_units(self, params: dict) -> list[str]:
        return self._resolve_dates(params)

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        fetcher = get_registry().get(DailyBasicFetcher)
        bo_list = await asyncio.to_thread(fetcher.fetch_daily_basic, unit)
        if not bo_list:
            logger.info("估值 %s: 无数据（非交易日？）", unit)
            return UnitResult(success=True, detail=unit, skipped=True)

        async with AsyncSessionLocal() as session:
            saved = await FinDailyBasicRepoImpl(session).save_batch(
                [bo.to_entity() for bo in bo_list]
            )
            await session.commit()
        logger.info("估值 %s: 写入 %d 条", unit, saved)
        return UnitResult(success=True, detail=unit, saved_count=saved)

    def summary_message(self, tally: UnitTally) -> str:
        return (
            f"完成: {tally.success} 天（非交易日 {tally.skip}），"
            f"失败 {tally.fail}；写入 {tally.saved} 条"
        )

    @staticmethod
    def _resolve_dates(params: dict) -> list[str]:
        """按 trade_date / days 解析需要采集的日期列表"""
        trade_date = params.get("trade_date")
        if trade_date:
            return [str(trade_date).replace("-", "")]
        days = int(params.get("days", 1))
        today = date.today()
        return [
            (today - timedelta(days=i)).strftime("%Y%m%d")
            for i in range(days)
        ]
