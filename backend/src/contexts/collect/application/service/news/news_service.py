"""NewsService：新闻 service"""
from __future__ import annotations

import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import date

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.collect.application.service.base import CollectResult, RateLimited
from contexts.collect.infrastructure.fetcher.news.NewsTushareFetcher import (
    NewsTushareFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class NewsService:
    name = "news"
    facet = "news"
    sub_facet = "news"
    label = "新闻快讯"
    DEFAULT_PARAMS = {"minutes": 30}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: NewsTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or NewsTushareFetcher()

    async def collect(self, params: dict) -> CollectResult:
        minutes = int(params.get("minutes", 30))
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                items = await self._fetcher.fetch(minutes=minutes)
                saved = await self._save(items)
                return CollectResult(
                    total=1, success=1, saved=saved, skip=1 if not items else 0,
                    message=f"新闻: {len(items)} 条, 写入 {saved}",
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
        try:
            from contexts.collect.infrastructure.persistence.models.news_article import (
                NewsArticleDB,
            )
        except ImportError:
            logger.debug("news_article 表未建，跳过入库")
            return 0
        rows = [
            {
                "published_at": r["published_at"],
                "title": r["title"],
                "content": r.get("content"),
                "source": r.get("source"),
                "url": r.get("url"),
                "symbols": r.get("symbols") or [],
                "category": r.get("category"),
            }
            for r in items
        ]
        async with db_session_factory() as session:
            stmt = pg_insert(NewsArticleDB).values(rows)
            r = await session.execute(stmt)
            await session.commit()
            return r.rowcount or 0


__all__ = ["NewsService"]
