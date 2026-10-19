"""NewsService：新闻 service

走 repo：NewsArticleRepository
"""
from __future__ import annotations

import logging

from contexts.collect.application.service.base import CollectResult, RateLimited, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.news.NewsTushareFetcher import (
    NewsTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import NewsArticleRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class NewsService:

    META = ServiceMeta(
        name='news',
        facet='news',
        label='新闻快讯',
        description='Tushare 新闻快讯',
        kind=ServiceKind.INCREMENTAL,
    )
    name = "news"
    facet = "news"
    sub_facet = "news"
    label = "新闻快讯"
    DEFAULT_PARAMS = {"minutes": 30}
    UI_SCHEMA = [
        {
            "key": "minutes",
            "ui": "minutes_int",
            "label": "回溯分钟数",
            "required": True,
            "placeholder": "30",
            "help": "回溯 N 分钟内的新闻（默认 30）",
        },
    ]
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(
        self,
        fetcher: NewsTushareFetcher | None = None,
        repo: NewsArticleRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or NewsTushareFetcher()
        self._repo = repo or NewsArticleRepository()
        self._session = session

    async def collect(self, params: dict) -> CollectResult:
        minutes = int(params.get("minutes", 30))
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                items = await self._fetcher.fetch(minutes=minutes)
                saved = await self._repo.save_dicts(items, self._session)
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


__all__ = ["NewsService"]
