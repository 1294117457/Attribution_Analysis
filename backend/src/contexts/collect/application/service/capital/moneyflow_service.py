"""MoneyflowService：个股资金流向 service

走 repo：MoneyflowRepository
session 由 DI 工厂注入，透传给 repo.save()。
"""
from __future__ import annotations

import logging
from datetime import date

from contexts.collect.application.service.base import CollectResult, RateLimited, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.capital.MoneyflowTushareFetcher import (
    MoneyflowTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import MoneyflowRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MoneyflowService:

    META = ServiceMeta(
        name='moneyflow',
        facet='capital',
        label='个股资金流向',
        description='每日个股资金流向（Tushare moneyflow）',
        kind=ServiceKind.INCREMENTAL,
    )
    name = "moneyflow"
    facet = "capital"
    sub_facet = "moneyflow"
    label = "个股资金流向"
    DEFAULT_PARAMS = {"trade_date": None}
    UI_SCHEMA = [
        {"key": "trade_date", "ui": "date_str", "label": "交易日期", "required": True, "placeholder": "2024-10-17"},
    ]
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(
        self,
        fetcher: MoneyflowTushareFetcher | None = None,
        repo: MoneyflowRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or MoneyflowTushareFetcher()
        self._repo = repo or MoneyflowRepository()
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
                    total=1, success=1, saved=saved,
                    message=f"资金流 {td}: 获取 {len(bos)} 条, 写入 {saved} 条",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")


__all__ = ["MoneyflowService"]
