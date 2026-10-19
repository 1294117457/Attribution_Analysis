"""NameChangeService：股票曾用名 service

走 repo：NameChangeRepository
session 由 DI 工厂注入，透传给 repo.save()。
"""
from __future__ import annotations

import logging

from contexts.collect.application.service.base import CollectResult, RateLimited, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.tech.NameChangeTushareFetcher import (
    NameChangeTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import NameChangeRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class NameChangeService:

    META = ServiceMeta(
        name='name_change',
        facet='tech',
        label='股票曾用名',
        description='全 A 股股票曾用名（Tushare name_change）',
        kind=ServiceKind.FULL_REFRESH,
    )
    name = "name_change"
    facet = "tech"
    sub_facet = "name"
    label = "股票曾用名"
    DEFAULT_PARAMS = {}
    UI_SCHEMA = []
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(
        self,
        fetcher: NameChangeTushareFetcher | None = None,
        repo: NameChangeRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or NameChangeTushareFetcher()
        self._repo = repo or NameChangeRepository()
        self._session = session

    async def collect(self, params: dict) -> CollectResult:
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                bos = await self._fetcher.fetch()
                saved = await self._repo.save(bos, self._session)
                return CollectResult(
                    total=1, success=1 if bos else 0, saved=saved,
                    skip=1 if not bos else 0,
                    message=f"曾用名: 共 {len(bos)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")


__all__ = ["NameChangeService"]
