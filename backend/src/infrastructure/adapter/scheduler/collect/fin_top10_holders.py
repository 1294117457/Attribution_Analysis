"""前十大股东采集任务（Tushare top10_holders）

单元 = 单只股票；按股票循环 fetch 拉前十大股东。
"""

from __future__ import annotations

import asyncio
import logging
from sqlalchemy import select

from application.port.collector_port import Top10HoldersFetcher, RateLimitError
from infrastructure.adapter import get_registry
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    Cancelled,
    UnitResult,
    UnitTally,
    is_cancelled,
)
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.models.stock_info import StockInfoDB
from infrastructure.persistence.repositories.fin_top10_holders_repository import (
    FinTop10HoldersRepoImpl,
)

logger = logging.getLogger(__name__)

RATE_LIMIT_WAIT = 60.0
RATE_LIMIT_RETRIES = 3


class FinTop10HoldersCollectTask(BaseCollectTask):
    name = "fin_top10_holders"
    facet = "fundamental"
    sub_facet = "holder"
    label = "前十大股东"
    description = "股权结构（tushare top10_holders）"
    default_params = {}
    sort_order = 10

    async def list_units(self, params: dict) -> list[str]:
        if params.get("symbol"):
            return [str(params["symbol"]).zfill(6)]
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(StockInfoDB.symbol)
                .where(StockInfoDB.list_status == "L")
                .order_by(StockInfoDB.symbol)
            )
            symbols = [r[0] for r in rows.all()]
        limit = params.get("limit")
        return symbols[: int(limit)] if limit else symbols

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        fetcher = get_registry().get(Top10HoldersFetcher)
        bos = await self._fetch_with_rate_limit(fetcher, unit, params.get("period"))
        if not bos:
            return UnitResult(success=True, detail=unit, skipped=True)
        async with AsyncSessionLocal() as session:
            saved = await FinTop10HoldersRepoImpl(session).save_batch(
                [b.to_entity() for b in bos],
            )
        return UnitResult(success=True, detail=unit, saved_count=saved)

    def summary_message(self, tally: UnitTally) -> str:
        return (
            f"完成: 股票 {tally.success}（无股东 {tally.skip}），失败 {tally.fail}；"
            f"写入 {tally.saved} 条"
        )

    def _check_cancel(self) -> None:
        if is_cancelled(self._task_id):
            raise Cancelled()

    async def _fetch_with_rate_limit(self, fetcher, symbol, period) -> list:
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            try:
                return await asyncio.to_thread(fetcher.fetch_top10_holders, symbol, period)
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
