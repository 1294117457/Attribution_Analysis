"""股票曾用名采集任务（Tushare namechange）

单元 = "all"（一次拉全市场）。
"""

from __future__ import annotations

import asyncio
import logging

from application.port.collector_port import NameChangeFetcher, RateLimitError
from infrastructure.adapter import get_registry
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    Cancelled,
    UnitResult,
    UnitTally,
    is_cancelled,
)
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.repositories.base_name_change_repository import (
    BaseNameChangeRepoImpl,
)

logger = logging.getLogger(__name__)

RATE_LIMIT_WAIT = 60.0
RATE_LIMIT_RETRIES = 3


class BaseNameChangeCollectTask(BaseCollectTask):
    name = "base_name_change"
    facet = "tech"
    sub_facet = "base"
    label = "股票曾用名"
    description = "历史 K 线展示（tushare namechange）"
    default_params = {}
    sort_order = 30

    async def list_units(self, params: dict) -> list[str]:
        if params.get("symbol"):
            return [str(params["symbol"]).zfill(6)]
        return ["all"]

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        fetcher = get_registry().get(NameChangeFetcher)
        bos = await self._fetch_with_rate_limit(
            fetcher, unit if unit != "all" else None,
        )
        if not bos:
            return UnitResult(success=True, detail=unit, skipped=True)
        async with AsyncSessionLocal() as session:
            saved = await BaseNameChangeRepoImpl(session).save_batch(
                [b.to_entity() for b in bos],
            )
        return UnitResult(success=True, detail=unit, saved_count=saved)

    def summary_message(self, tally: UnitTally) -> str:
        return (
            f"完成: 抓取 {tally.success} 批，失败 {tally.fail}；"
            f"写入 {tally.saved} 条"
        )

    def _check_cancel(self) -> None:
        if is_cancelled(self._task_id):
            raise Cancelled()

    async def _fetch_with_rate_limit(self, fetcher, symbol) -> list:
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            try:
                return await asyncio.to_thread(fetcher.fetch_name_change, symbol)
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
