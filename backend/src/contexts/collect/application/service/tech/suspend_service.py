"""SuspendService：停复牌 service

走 repo：SuspendRepository
session 由 DI 工厂注入，透传给 repo.save()。
"""
from __future__ import annotations

import logging
from datetime import date

from contexts.collect.application.service.base import CollectResult, RateLimited, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.tech.SuspendTushareFetcher import (
    SuspendTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import SuspendRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SuspendService:

    META = ServiceMeta(
        name='suspend',
        facet='tech',
        label='停复牌',
        description='每日停复牌数据（Tushare suspend）',
        kind=ServiceKind.INCREMENTAL,
    )
    name = "suspend"
    facet = "tech"
    sub_facet = "suspend"
    label = "停复牌"
    DEFAULT_PARAMS = {"trade_date": None}
    UI_SCHEMA = [
        {
            "key": "trade_date",
            "ui": "date_str",
            "label": "交易日期",
            "required": True,
            "placeholder": "2024-10-17",
            "help": "必填，指定停复牌查询日期",
        },
    ]
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(
        self,
        fetcher: SuspendTushareFetcher | None = None,
        repo: SuspendRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or SuspendTushareFetcher()
        self._repo = repo or SuspendRepository()
        self._session = session

    async def collect(self, params: dict) -> CollectResult:
        td = params.get("trade_date")
        if not td:
            return CollectResult(fail=1, message="trade_date 必填")
        if not isinstance(td, date):
            td = date.fromisoformat(str(td))
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                bos = await self._fetcher.fetch(trade_date=td)
                saved = await self._repo.save(bos, self._session)
                return CollectResult(
                    total=1, success=1, saved=saved, skip=1 if not bos else 0,
                    message=f"停复牌 {td}: {len(bos)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")


__all__ = ["SuspendService"]
