"""ConceptListService：概念清单 service

走 repo：ConceptRepository
"""
from __future__ import annotations

import logging

from contexts.collect.application.service.base import CollectResult, RateLimited, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.fundamental.ConceptListAdataFetcher import (
    ConceptListAdataFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import ConceptRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ConceptListService:

    META = ServiceMeta(
        name='concept_list',
        facet='fundamental',
        label='概念清单',
        description='全概念清单（Adata concept_list；全量覆盖）',
        kind=ServiceKind.FULL_REFRESH,
    )
    name = "concept_list"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念清单"
    DEFAULT_PARAMS = {}
    UI_SCHEMA = []
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 1

    def __init__(
        self,
        fetcher: ConceptListAdataFetcher | None = None,
        repo: ConceptRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or ConceptListAdataFetcher()
        self._repo = repo or ConceptRepository()
        self._session = session

    async def collect(self, params: dict) -> CollectResult:
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                bos = await self._fetcher.fetch()
                saved = await self._repo.save(bos, self._session)
                return CollectResult(
                    total=1, success=1, saved=saved, skip=1 if not bos else 0,
                    message=f"概念清单: {len(bos)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")


__all__ = ["ConceptListService"]
