"""ConceptIndexDailyService：概念指数日 K service

走 repo：ConceptIndexRepository
"""
from __future__ import annotations

import asyncio
import logging

from contexts.collect.application.service.base import CollectResult, RateLimited, list_all_concept_codes, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.fundamental.ConceptIndexDailyAdataFetcher import (
    ConceptIndexDailyAdataFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import ConceptIndexRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ConceptIndexDailyService:

    META = ServiceMeta(
        name='concept_index_daily',
        facet='fundamental',
        label='概念指数日 K',
        description='概念指数日 K 线（Adata concept_index_daily）',
        kind=ServiceKind.INCREMENTAL,
    )
    name = "concept_index_daily"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念指数日 K"
    DEFAULT_PARAMS = {"index_codes": []}
    UI_SCHEMA = [
        {
            "key": "index_codes",
            "ui": "index_codes_list",
            "label": "概念指数代码",
            "required": False,
            "placeholder": "每行一个：BK0001\nBK0002",
            "help": "留空表示全量采集（先采集 concept_list 拿到全部概念）",
        },
    ]
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 1

    def __init__(
        self,
        fetcher: ConceptIndexDailyAdataFetcher | None = None,
        repo: ConceptIndexRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or ConceptIndexDailyAdataFetcher()
        self._repo = repo or ConceptIndexRepository()
        self._session = session

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
                        bos = await self._fetcher.fetch(index_code=c)
                        return await self._repo.save(bos, self._session)
                    except RateLimited as e:
                        if attempt < 2:
                            import asyncio as _a
                            await _a.sleep(e.retry_after)
                        else:
                            raise
                return 0

        results = await asyncio.gather(*[one(c) for c in index_codes], return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, int) and r >= 0)
        saved = sum(r for r in results if isinstance(r, int))
        fail = sum(1 for r in results if isinstance(r, BaseException))
        return CollectResult(
            total=len(index_codes), success=success, fail=fail, saved=saved,
            message=f"概念指数日 K: 共 {len(index_codes)} 个概念, 成功 {success}, 写入 {saved}",
        )


__all__ = ["ConceptIndexDailyService"]
