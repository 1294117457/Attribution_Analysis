"""ConceptMembersService：概念成分股 service（按 index_code 维度批量）"""
from __future__ import annotations

import asyncio
import logging

from contexts.collect.application.service.base import CollectResult, RateLimited, list_all_concept_codes
from contexts.collect.infrastructure.fetcher.fundamental.ConceptMembersAdataFetcher import (
    ConceptMembersAdataFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class ConceptMembersService:
    name = "concept_members"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念成分股"
    DEFAULT_PARAMS = {"index_codes": []}
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 3

    def __init__(self, fetcher: ConceptMembersAdataFetcher | None = None) -> None:
        self._fetcher = fetcher or ConceptMembersAdataFetcher()

    async def collect(self, params: dict) -> CollectResult:
        index_codes = params.get("index_codes") or []
        if not index_codes:
            index_codes = await list_all_concept_codes()
            if not index_codes:
                return CollectResult(
                    fail=1,
                    message="index_codes 为空，且 concept 暂无数据（请先采集 concept_list）",
                )
        sem = asyncio.Semaphore(self.CONCURRENCY)

        async def one(c: str) -> int:
            async with sem:
                await check(self.RATE_LIMIT)
                for attempt in range(3):
                    try:
                        items = await self._fetcher.fetch(index_code=c)
                        return len(items)
                    except RateLimited as e:
                        if attempt < 2:
                            import asyncio as _a
                            await _a.sleep(e.retry_after)
                        else:
                            raise
                return 0

        results = await asyncio.gather(*[one(c) for c in index_codes], return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, int))
        fail = sum(1 for r in results if isinstance(r, BaseException))
        return CollectResult(
            total=len(index_codes), success=success, fail=fail,
            message=f"概念成分股: 共 {len(index_codes)} 个概念, 成功 {success}",
        )


__all__ = ["ConceptMembersService"]
