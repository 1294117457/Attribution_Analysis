"""ConceptSnapshotService：概念行情快照 service

走 repo：ConceptSnapshotRepository
保留 get() 实时查询入口。
"""
from __future__ import annotations

import logging

from contexts.collect.application.service.base import CollectResult, RateLimited, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.fundamental.ConceptSnapshotAdataFetcher import (
    ConceptSnapshotAdataFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import ConceptSnapshotRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ConceptSnapshotService:

    META = ServiceMeta(
        name='concept_snapshot',
        facet='fundamental',
        label='概念行情快照',
        description='概念行情快照（Adata concept_snapshot）',
        kind=ServiceKind.REALTIME,
    )
    name = "concept_snapshot"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念行情快照"
    DEFAULT_PARAMS = {"index_code": None}
    UI_SCHEMA = [
        {"key": "index_code", "ui": "index_code_str", "label": "概念指数代码", "required": True, "placeholder": "BK0001"},
    ]
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 1

    def __init__(
        self,
        fetcher: ConceptSnapshotAdataFetcher | None = None,
        repo: ConceptSnapshotRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or ConceptSnapshotAdataFetcher()
        self._repo = repo or ConceptSnapshotRepository()
        self._session = session

    async def collect(self, params: dict) -> CollectResult:
        ic = params.get("index_code")
        if not ic:
            return CollectResult(fail=1, message="index_code 必填")
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                bos = await self._fetcher.fetch(index_code=ic)
                saved = await self._repo.save(bos, self._session)
                return CollectResult(
                    total=1, success=1 if bos else 0, skip=1 if not bos else 0,
                    saved=saved,
                    message=f"概念快照 {ic}: {len(bos)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")

    async def get(self, index_code: str) -> list[dict]:
        """实时查询：直接调 fetcher，不入库"""
        bos = await self._fetcher.fetch(index_code=index_code)
        return [b.model_dump() for b in bos]


__all__ = ["ConceptSnapshotService"]
