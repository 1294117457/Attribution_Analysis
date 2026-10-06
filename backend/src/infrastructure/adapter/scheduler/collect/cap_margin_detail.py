"""融资融券明细采集任务（Tushare margin_detail）

单元 = 1 个交易日，全市场扫描。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from application.port.collector_port import MarginDetailFetcher, RateLimitError
from infrastructure.adapter import get_registry
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    Cancelled,
    UnitResult,
    UnitTally,
    is_cancelled,
)
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.repositories.cap_margin_detail_repository import (
    CapMarginDetailRepoImpl,
)

logger = logging.getLogger(__name__)

RATE_LIMIT_WAIT = 60.0
RATE_LIMIT_RETRIES = 3


class CapMarginDetailCollectTask(BaseCollectTask):
    name = "cap_margin_detail"
    facet = "capital"
    sub_facet = "margin"
    label = "个股融资融券"
    description = "融资余额 / 融券余额（tushare margin_detail）"
    default_params = {"days": 1}
    sort_order = 20

    async def list_units(self, params: dict) -> list[str]:
        return self._resolve_dates(params)

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        fetcher = get_registry().get(MarginDetailFetcher)
        bos = await self._fetch_with_rate_limit(fetcher, unit)
        if not bos:
            return UnitResult(success=True, detail=unit, skipped=True)
        async with AsyncSessionLocal() as session:
            saved = await CapMarginDetailRepoImpl(session).save_batch(
                [b.to_entity() for b in bos],
            )
        return UnitResult(success=True, detail=unit, saved_count=saved)

    def summary_message(self, tally: UnitTally) -> str:
        return (
            f"完成: 交易日 {tally.success}（无数据 {tally.skip}），失败 {tally.fail}；"
            f"写入 {tally.saved} 条"
        )

    def _check_cancel(self) -> None:
        if is_cancelled(self._task_id):
            raise Cancelled()

    async def _fetch_with_rate_limit(self, fetcher, trade_date: str) -> list:
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            try:
                return await asyncio.to_thread(fetcher.fetch_margin_detail, trade_date)
            except RateLimitError:
                if attempt == RATE_LIMIT_RETRIES:
                    raise
                await self._sleep_cancellable(RATE_LIMIT_WAIT)
        return []

    async def _sleep_cancellable(self, seconds: float) -> None:
        remaining = seconds
        while remaining > 0:
            self._check_cancel()
            step = min(1.0, remaining)
            await asyncio.sleep(step)
            remaining -= step

    @staticmethod
    def _resolve_dates(params: dict) -> list[str]:
        trade_date = params.get("trade_date")
        if trade_date:
            return [str(trade_date).replace("-", "")]
        days = int(params.get("days", 1))
        today = date.today()
        return [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(days)]
