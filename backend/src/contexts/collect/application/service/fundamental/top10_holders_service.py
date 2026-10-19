"""Top10HoldersService：前 10 大股东 service

走 repo：FinTop10HoldersRepository
"""
from __future__ import annotations

import asyncio
import logging

from contexts.collect.application.service.base import CollectResult, RateLimited, list_all_a_symbols, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.fundamental.Top10HoldersTushareFetcher import (
    Top10HoldersTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import FinTop10HoldersRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class Top10HoldersService:

    META = ServiceMeta(
        name='top10_holders',
        facet='fundamental',
        label='前 10 大股东',
        description='前 10 大股东（Tushare top10_holders）',
        kind=ServiceKind.INCREMENTAL,
    )
    name = "top10_holders"
    facet = "fundamental"
    sub_facet = "holder"
    label = "前 10 大股东"
    DEFAULT_PARAMS = {"symbols": []}
    UI_SCHEMA = [
        {
            "key": "symbols",
            "ui": "symbols_list",
            "label": "股票代码",
            "required": True,
            "placeholder": "每行一只：000001\n000002\n600000",
            "help": "必填，至少一只股票",
        },
    ]
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 5

    def __init__(
        self,
        fetcher: Top10HoldersTushareFetcher | None = None,
        repo: FinTop10HoldersRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or Top10HoldersTushareFetcher()
        self._repo = repo or FinTop10HoldersRepository()
        self._session = session

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
                        bos = await self._fetcher.fetch(symbol=s)
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
            message=f"前 10 大股东: 共 {len(symbols)} 只, 成功 {success}, 写入 {saved}",
        )


__all__ = ["Top10HoldersService"]
