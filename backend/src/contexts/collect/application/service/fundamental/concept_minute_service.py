"""ConceptMinuteService：概念实时分时 service（实时查询 + collect 入口）"""
from __future__ import annotations

import logging

from contexts.collect.application.service.base import CollectResult, RateLimited, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.fundamental.ConceptMinuteAdataFetcher import (
    ConceptMinuteAdataFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class ConceptMinuteService:

    META = ServiceMeta(
        name='concept_minute',
        facet='fundamental',
        label='概念实时分时',
        description='概念实时分时（Adata concept_minute）',
        kind=ServiceKind.REALTIME,
        rate_limit=("adata", 100, 60),
        concurrency=1,
    )

    def __init__(self, fetcher: ConceptMinuteAdataFetcher | None = None) -> None:
        self._fetcher = fetcher or ConceptMinuteAdataFetcher()

    async def collect(self, params: dict) -> CollectResult:
        ic = params.get("index_code")
        if not ic:
            return CollectResult(fail=1, message="index_code 必填")
        await check(self.META.rate_limit)
        for attempt in range(3):
            try:
                items = await self._fetcher.fetch(index_code=ic)
                return CollectResult(
                    total=1, success=1 if items else 0, skip=1 if not items else 0,
                    saved=len(items),
                    message=f"概念分时 {ic}: {len(items)} 条",
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


__all__ = ["ConceptMinuteService"]
