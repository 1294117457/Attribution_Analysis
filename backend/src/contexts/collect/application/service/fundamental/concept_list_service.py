"""ConceptListService：概念清单 service（adata 一次性全量）"""
from __future__ import annotations

import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.collect.application.service.base import CollectResult, RateLimited
from contexts.collect.infrastructure.fetcher.fundamental.ConceptListAdataFetcher import (
    ConceptListAdataFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class ConceptListService:
    name = "concept_list"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念清单"
    DEFAULT_PARAMS = {}
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: ConceptListAdataFetcher | None = None) -> None:
        self._fetcher = fetcher or ConceptListAdataFetcher()

    async def collect(self, params: dict) -> CollectResult:
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                items = await self._fetcher.fetch()
                saved = await self._save(items)
                return CollectResult(
                    total=1, success=1, saved=saved, skip=1 if not items else 0,
                    message=f"概念清单: {len(items)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")

    async def _save(self, items) -> int:
        if not items:
            return 0
        from contexts.concept.infrastructure.persistence.models.concept import ConceptDB
        rows = [
            {"index_code": it["index_code"], "concept_code": it.get("concept_code"),
             "name": it["name"]}
            for it in items
        ]
        async with db_session_factory() as session:
            stmt = pg_insert(ConceptDB).values(rows)
            update_cols = {c.name: stmt.excluded[c.name] for c in ConceptDB.__table__.columns
                           if c.name not in ("id", "index_code", "created_at")}
            stmt = stmt.on_conflict_do_update(
                index_elements=["index_code"],
                set_=update_cols,
            )
            r = await session.execute(stmt)
            await session.commit()
            return r.rowcount or 0


__all__ = ["ConceptListService"]
