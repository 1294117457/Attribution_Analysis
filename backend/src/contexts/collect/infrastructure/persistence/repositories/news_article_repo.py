"""NewsArticleRepository：新闻快讯仓储

模式：upsert（UK = source + url）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.infrastructure.persistence.models.news_article import (
    NewsArticleDB,
)

logger = logging.getLogger(__name__)


class NewsArticleRepository:
    """新闻快讯仓储（实现 domain Protocol）

    fetcher 返回 list[dict]（无 BO），service 内 dict → row
    """

    async def save_dicts(self, items: list[dict], session: AsyncSession) -> int:
        if not items:
            return 0
        rows = []
        for r in items:
            rows.append({
                "published_at": r["published_at"],
                "title": r["title"],
                "content": r.get("content"),
                "source": r.get("source"),
                "url": r.get("url"),
                "channels": r.get("channels"),
                "symbols": r.get("symbols") or [],
                "category": r.get("category"),
                "sentiment": r.get("sentiment"),
            })
        stmt = pg_insert(NewsArticleDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in NewsArticleDB.__table__.columns
            if c.name not in ("id", "created_at", "updated_at", "source", "url")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "url"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)


__all__ = ["NewsArticleRepository"]
