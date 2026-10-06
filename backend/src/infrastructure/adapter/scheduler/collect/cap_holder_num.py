"""股东户数采集任务（Tushare stk_holdernumber）

单元 = 单只股票；按 stock_basic 列表逐个 fetch。
季频数据，所以只 missing 才采（only_missing 模式）。
"""

from __future__ import annotations

import asyncio
import logging
from sqlalchemy import select

from application.port.collector_port import HolderNumberFetcher, RateLimitError
from infrastructure.adapter import get_registry
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    Cancelled,
    UnitResult,
    UnitTally,
    is_cancelled,
)
from infrastructure.adapter.fetcher.tushare import symbol_to_ts_code
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.models.stock_info import StockInfoDB
from infrastructure.persistence.repositories.cap_holder_num_repository import (
    CapHolderNumRepoImpl,
)

logger = logging.getLogger(__name__)

RATE_LIMIT_WAIT = 60.0
RATE_LIMIT_RETRIES = 3


class CapHolderNumCollectTask(BaseCollectTask):
    name = "cap_holder_num"
    facet = "capital"
    sub_facet = "chip"
    label = "股东户数"
    description = "股东户数 + 季频（tushare stk_holdernumber）"
    default_params = {"only_missing": True}
    sort_order = 20

    async def list_units(self, params: dict) -> list[str]:
        from infrastructure.persistence.models.cap_holder_num import CapHolderNumDB
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(StockInfoDB.symbol)
                .where(StockInfoDB.list_status == "L")
                .order_by(StockInfoDB.symbol)
            )
            symbols = [r[0] for r in rows.all()]
            if params.get("only_missing"):
                # 一次查所有已有 symbol 集合（避免 N+1）
                existing_rows = await session.execute(
                    select(CapHolderNumDB.symbol).distinct()
                )
                existing_set = {r[0] for r in existing_rows.all()}
                symbols = [s for s in symbols if s not in existing_set]
        limit = params.get("limit")
        return symbols[: int(limit)] if limit else symbols

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        fetcher = get_registry().get(HolderNumberFetcher)
        bos = await self._fetch_with_rate_limit(fetcher, unit)
        if not bos:
            return UnitResult(success=True, detail=unit, skipped=True)
        async with AsyncSessionLocal() as session:
            saved = await CapHolderNumRepoImpl(session).save_batch(
                [b.to_entity() for b in bos],
            )
        return UnitResult(success=True, detail=unit, saved_count=saved)

    def summary_message(self, tally: UnitTally) -> str:
        return (
            f"完成: 股票 {tally.success}（无数据 {tally.skip}），失败 {tally.fail}；"
            f"写入 {tally.saved} 条"
        )

    def _check_cancel(self) -> None:
        if is_cancelled(self._task_id):
            raise Cancelled()

    async def _fetch_with_rate_limit(self, fetcher, symbol: str) -> list:
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            try:
                return await asyncio.to_thread(fetcher.fetch_holder_number, symbol)
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
