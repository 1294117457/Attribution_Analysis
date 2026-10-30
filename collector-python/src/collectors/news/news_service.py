"""NewsService：新闻 service"""
from __future__ import annotations

import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import date

from core.db import raw_session_factory
from collectors.base import CollectResult, RateLimited, fetch_with_retry
from collectors.news.NewsTushareFetcher import (
    NewsTushareFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)


class NewsService:
    name = "news"
    facet = "news"
    label = "新闻快讯"
    strategy = "incremental"
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: NewsTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or NewsTushareFetcher()

    async def collect(self, params: dict) -> CollectResult:
        minutes = int(params.get("minutes", 30))
        # ★ fetch_with_retry：限流退避重试；**权限不足记 skip 而非 fail**
        #   （news 接口需要 Tushare 更高积分档位，账号无权限时不该报「采集失败」）
        ok, items, msg = await fetch_with_retry(
            lambda: self._fetcher.fetch(minutes=minutes),
            rate_limit=self.RATE_LIMIT,
        )
        if not ok:
            return CollectResult(total=1, skip=1, message=msg)
        saved = await self._save(items)
        return CollectResult(
            total=1, success=1, saved=saved, skip=1 if not items else 0,
            message=f"新闻: {len(items)} 条, 写入 {saved}",
        )

    async def _save(self, items) -> int:
        if not items:
            return 0
        try:
            from models.news_article import (
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
        async with raw_session_factory() as session:
            # ★ 分块（防 PG 参数上限）+ 按 (source, url) 去重（防 ON CONFLICT 二次命中）
            from collectors.base import chunk_rows_for_insert, dedupe_rows

            total = 0
            for chunk in chunk_rows_for_insert(
                NewsArticleDB, dedupe_rows(rows, ["source", "url"])
            ):
                stmt = pg_insert(NewsArticleDB).values(chunk)
                r = await session.execute(stmt)
                total += r.rowcount or 0
            await session.commit()
            return total


__all__ = ["NewsService"]
