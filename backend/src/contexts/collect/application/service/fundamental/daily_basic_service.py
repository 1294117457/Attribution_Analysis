"""DailyBasicService：每日估值 service

走 repo：FinDailyBasicRepository
"""
from __future__ import annotations

import logging
from datetime import date

from contexts.collect.application.service.base import CollectResult, RateLimited, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.fundamental.DailyBasicTushareFetcher import (
    DailyBasicTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import FinDailyBasicRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DailyBasicService:

    META = ServiceMeta(
        name='daily_basic',
        facet='fundamental',
        label='每日估值',
        description='每日估值（Tushare daily_basic）',
        kind=ServiceKind.INCREMENTAL,
    )
    name = "daily_basic"
    facet = "fundamental"
    sub_facet = "valuation"
    label = "每日估值"
    DEFAULT_PARAMS = {"trade_date": None}
    UI_SCHEMA = [
        {"key": "trade_date", "ui": "date_str", "label": "交易日期", "required": True, "placeholder": "2024-10-17"},
    ]
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(
        self,
        fetcher: DailyBasicTushareFetcher | None = None,
        repo: FinDailyBasicRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or DailyBasicTushareFetcher()
        self._repo = repo or FinDailyBasicRepository()
        self._session = session

    async def collect(self, params: dict) -> CollectResult:
        td = params.get("trade_date")
        if not td:
            td = date.today()
        if not isinstance(td, date):
            td = date.fromisoformat(str(td))
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                bos = await self._fetcher.fetch(trade_date=td)
                saved = await self._repo.save(bos, self._session)
                return CollectResult(
                    total=1, success=1, saved=saved, skip=1 if not bos else 0,
                    message=f"每日估值 {td}: {len(bos)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")


__all__ = ["DailyBasicService"]
