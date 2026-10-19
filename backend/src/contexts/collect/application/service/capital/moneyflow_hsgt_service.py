"""MoneyflowHsgtService：沪深港通资金流向 service

走 repo：MoneyflowHsgtRepository
"""
from __future__ import annotations

import logging
from datetime import date

from contexts.collect.application.service.base import CollectResult, RateLimited, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.capital.MoneyflowHsgtTushareFetcher import (
    MoneyflowHsgtTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import MoneyflowHsgtRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MoneyflowHsgtService:

    META = ServiceMeta(
        name='moneyflow_hsgt',
        facet='capital',
        label='沪深港通资金流向',
        description='每日沪深港通资金流向（Tushare moneyflow_hsgt）',
        kind=ServiceKind.INCREMENTAL,
    )
    name = "moneyflow_hsgt"
    facet = "capital"
    sub_facet = "north_flow"
    label = "沪深港通资金流向"
    DEFAULT_PARAMS = {"trade_date": None}
    UI_SCHEMA = [
        {"key": "trade_date", "ui": "date_str", "label": "交易日期", "required": True, "placeholder": "2024-10-17"},
    ]
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(
        self,
        fetcher: MoneyflowHsgtTushareFetcher | None = None,
        repo: MoneyflowHsgtRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or MoneyflowHsgtTushareFetcher()
        self._repo = repo or MoneyflowHsgtRepository()
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
                    message=f"沪深港通 {td}: {len(bos)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")


__all__ = ["MoneyflowHsgtService"]
