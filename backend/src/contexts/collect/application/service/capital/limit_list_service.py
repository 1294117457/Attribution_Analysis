"""LimitListService：每日涨跌停板 service

走 repo：LimitListRepository
"""
from __future__ import annotations

import logging
from datetime import date

from contexts.collect.application.service.base import CollectResult, RateLimited, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.capital.LimitListTushareFetcher import (
    LimitListTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import LimitListRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class LimitListService:

    META = ServiceMeta(
        name='limit_list_d',
        facet='capital',
        label='每日涨跌停板',
        description='每日涨跌停板（Tushare limit_list_d）',
        kind=ServiceKind.INCREMENTAL,
    )
    name = "limit_list_d"
    facet = "capital"
    sub_facet = "limit"
    label = "每日涨跌停板"
    DEFAULT_PARAMS = {"trade_date": None}
    UI_SCHEMA = [
        {"key": "trade_date", "ui": "date_str", "label": "交易日期", "required": True, "placeholder": "2024-10-17"},
    ]
    RATE_LIMIT = ("tushare", 100, 60)
    CONCURRENCY = 1

    def __init__(
        self,
        fetcher: LimitListTushareFetcher | None = None,
        repo: LimitListRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or LimitListTushareFetcher()
        self._repo = repo or LimitListRepository()
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
                    message=f"涨跌停 {td}: {len(bos)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")


__all__ = ["LimitListService"]
