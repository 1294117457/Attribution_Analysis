"""NameChangeService：股票曾用名 service"""
from __future__ import annotations

import logging

from contexts.collect.application.service.base import CollectResult, RateLimited
from contexts.collect.infrastructure.fetcher.tech.NameChangeTushareFetcher import (
    NameChangeTushareFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class NameChangeService:
    name = "name_change"
    facet = "tech"
    sub_facet = "name"
    label = "股票曾用名"
    DEFAULT_PARAMS = {}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: NameChangeTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or NameChangeTushareFetcher()

    async def collect(self, params: dict) -> CollectResult:
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                bos = await self._fetcher.fetch()
                return CollectResult(
                    total=1, success=1 if bos else 0,
                    skip=1 if not bos else 0,
                    message=f"曾用名: 共 {len(bos)} 条",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")


__all__ = ["NameChangeService"]
