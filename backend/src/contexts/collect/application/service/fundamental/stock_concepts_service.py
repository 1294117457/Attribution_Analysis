"""StockConceptsService：股票所属概念 service（按 symbol 维度批量）"""
from __future__ import annotations

import asyncio
import logging

from contexts.collect.application.service.base import CollectResult, RateLimited, list_all_a_symbols
from contexts.collect.infrastructure.fetcher.fundamental.StockConceptsAdataFetcher import (
    StockConceptsAdataFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class StockConceptsService:
    name = "stock_concepts"
    facet = "fundamental"
    sub_facet = "concept"
    label = "股票所属概念"
    DEFAULT_PARAMS = {"symbols": []}
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 5

    def __init__(self, fetcher: StockConceptsAdataFetcher | None = None) -> None:
        self._fetcher = fetcher or StockConceptsAdataFetcher()

    async def collect(self, params: dict) -> CollectResult:
        symbols = params.get("symbols") or []
        if not symbols:
            symbols = await list_all_a_symbols()
            if not symbols:
                return CollectResult(
                    fail=1,
                    message="symbols 为空，且 stock_basic 暂无数据（请先采集 stock_basic）",
                )
        symbols = [str(s).zfill(6) for s in symbols]
        sem = asyncio.Semaphore(self.CONCURRENCY)

        async def one(s: str) -> int:
            async with sem:
                await check(self.RATE_LIMIT)
                for attempt in range(3):
                    try:
                        items = await self._fetcher.fetch(symbol=s)
                        return len(items)
                    except RateLimited as e:
                        if attempt < 2:
                            import asyncio as _a
                            await _a.sleep(e.retry_after)
                        else:
                            raise
                return 0

        results = await asyncio.gather(*[one(s) for s in symbols], return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, int))
        fail = sum(1 for r in results if isinstance(r, BaseException))
        return CollectResult(
            total=len(symbols), success=success, fail=fail,
            message=f"股票所属概念: 共 {len(symbols)} 只, 成功 {success}",
        )


__all__ = ["StockConceptsService"]
