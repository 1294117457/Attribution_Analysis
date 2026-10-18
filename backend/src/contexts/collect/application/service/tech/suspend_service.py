"""SuspendService：停复牌 service（按 trade_date 一次性）"""
from __future__ import annotations

import logging
from datetime import date

from contexts.collect.application.service.base import CollectResult, RateLimited
from contexts.collect.infrastructure.fetcher.tech.SuspendTushareFetcher import (
    SuspendTushareFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class SuspendService:
    name = "suspend"
    facet = "tech"
    sub_facet = "suspend"
    label = "停复牌"
    DEFAULT_PARAMS = {"trade_date": None}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: SuspendTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or SuspendTushareFetcher()

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
                return CollectResult(
                    total=1, success=1 if bos else 0,
                    skip=1 if not bos else 0,
                    message=f"停复牌 {td}: {len(bos)} 条",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")


__all__ = ["SuspendService"]
