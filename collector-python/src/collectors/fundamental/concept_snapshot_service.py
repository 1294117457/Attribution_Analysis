"""ConceptSnapshotService：概念行情快照 service（实时查询 + collect 入口）"""
from __future__ import annotations

import logging

from collectors.base import CollectResult, RateLimited
from collectors.fundamental.ConceptSnapshotAdataFetcher import (
    ConceptSnapshotAdataFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)


class ConceptSnapshotService:
    name = "concept_snapshot"
    facet = "fundamental"
    label = "概念行情快照"
    strategy = "realtime"
    QUERYABLE = True
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: ConceptSnapshotAdataFetcher | None = None) -> None:
        self._fetcher = fetcher or ConceptSnapshotAdataFetcher()

    async def collect(self, params: dict) -> CollectResult:
        ic = params.get("index_code")
        if not ic:
            return CollectResult(fail=1, message="index_code 必填")
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                items = await self._fetcher.fetch(index_code=ic)
                return CollectResult(
                    total=1, success=1 if items else 0, skip=1 if not items else 0,
                    saved=len(items),
                    message=f"概念快照 {ic}: {len(items)} 条",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")

    async def get(self, index_code: str) -> list[dict]:
        return await self._fetcher.fetch(index_code=index_code)


__all__ = ["ConceptSnapshotService"]
