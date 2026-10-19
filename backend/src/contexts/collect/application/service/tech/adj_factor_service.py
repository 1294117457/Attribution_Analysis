"""AdjFactorService：复权因子 service（按 symbol 维度的批量采集）

走 repo：AdjFactorRepository（已抽离）
session 由 DI 工厂注入，透传给 repo.save()。
"""
from __future__ import annotations

import asyncio
import logging

from contexts.collect.application.service.base import CollectResult, RateLimited, list_all_a_symbols, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.tech.AdjFactorTushareFetcher import (
    AdjFactorTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import AdjFactorRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AdjFactorService:

    META = ServiceMeta(
        name='adj_factor',
        facet='tech',
        label='复权因子',
        description='单只股票复权因子（Tushare adj_factor）',
        kind=ServiceKind.INCREMENTAL,
    )
    name = "adj_factor"
    facet = "tech"
    sub_facet = "adj"
    label = "复权因子"
    description = "单只股票复权因子"
    DEFAULT_PARAMS = {"symbols": []}
    UI_SCHEMA = [
        {
            "key": "symbols",
            "ui": "symbols_list",
            "label": "股票代码",
            "required": False,
            "placeholder": "每行一只：000001\n000002\n600000",
            "help": "留空表示全量采集（全市场 5000+ 只）",
        },
    ]
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 5

    def __init__(
        self,
        fetcher: AdjFactorTushareFetcher | None = None,
        repo: AdjFactorRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or AdjFactorTushareFetcher()
        self._repo = repo or AdjFactorRepository()
        self._session = session

    async def collect(self, params: dict) -> CollectResult:
        symbols = params.get("symbols") or []
        if not symbols:
            symbols = await self._list_all_symbols()
            if not symbols:
                return CollectResult(
                    fail=1,
                    message="symbols 为空，且 stock_basic 暂无数据（请先采集 stock_basic）",
                )
        symbols = [str(s).zfill(6) for s in symbols]
        sem = asyncio.Semaphore(self.CONCURRENCY)

        async def one(symbol: str) -> int:
            async with sem:
                await check(self.RATE_LIMIT)
                for attempt in range(3):
                    try:
                        bos = await self._fetcher.fetch(symbol=symbol)
                        return await self._repo.save(bos, self._session)
                    except RateLimited as e:
                        if attempt < 2:
                            import asyncio as _a
                            await _a.sleep(e.retry_after)
                        else:
                            raise
                return 0

        results = await asyncio.gather(*[one(s) for s in symbols], return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, int) and r >= 0)
        saved = sum(r for r in results if isinstance(r, int))
        fail = sum(1 for r in results if isinstance(r, BaseException))
        return CollectResult(
            total=len(symbols), success=success, fail=fail, saved=saved,
            message=f"复权因子: 共 {len(symbols)} 只, 成功 {success}, 写入 {saved}",
        )

    async def _list_all_symbols(self) -> list[str]:
        return await list_all_a_symbols()


__all__ = ["AdjFactorService"]
