"""NameChangeService：股票曾用名 service"""
from __future__ import annotations

import logging

from collectors.base import CollectResult, RateLimited, upsert_rows
from collectors.tech.NameChangeTushareFetcher import (
    NameChangeTushareFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)


class NameChangeService:
    name = "name_change"
    facet = "tech"
    label = "股票曾用名"
    strategy = "full"
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: NameChangeTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or NameChangeTushareFetcher()
        # ★ 缓存本次覆盖到的 (symbol, start_date) 集合
        self._covered_keys: list[tuple[str, str]] = []
        self._cached_bos: list | None = None

    async def collect(self, params: dict) -> CollectResult:
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                bos = self._cached_bos
                if bos is None:
                    bos = await self._fetcher.fetch()
                    self._cached_bos = bos
                self._covered_keys = [
                    (bo.symbol, bo.start_date.isoformat()) for bo in bos
                ]
                saved = await self._save(bos)
                return CollectResult(
                    total=1, success=1 if bos else 0,
                    skip=1 if not bos else 0,
                    saved=saved,
                    message=f"曾用名: 共 {len(bos)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")

    async def clear(self, params: dict) -> int:
        """全量覆盖前的清理：删除「本次覆盖域外」的残留曾用名记录。

        ★ 窄化：只删 (symbol, start_date) 不在本次集合中的行。
        ★ 空覆盖集直接返回 0（绝不因为上游空返回就清空全表）。
        ★ 曾用名是「历史事件」，清理只针对上游已不再返回的记录
          （例如同一起始日期的更名记录被上游修订）。
        """
        if self._cached_bos is None:
            await check(self.RATE_LIMIT)
            self._cached_bos = await self._fetcher.fetch()
        keys = list(self._covered_keys) or [
            (bo.symbol, bo.start_date.isoformat()) for bo in self._cached_bos
        ]
        if not keys:
            logger.warning("name_change.clear: 上游返回空，跳过清理")
            return 0

        from sqlalchemy import delete, tuple_

        from core.db import raw_session_factory
        from models.base_name_change import BaseNameChangeDB

        pairs = [(s, d) for s, d in keys]
        async with raw_session_factory() as session:
            r = await session.execute(
                delete(BaseNameChangeDB).where(
                    tuple_(BaseNameChangeDB.symbol, BaseNameChangeDB.start_date)
                    .notin_(pairs)
                )
            )
            await session.commit()
            return r.rowcount or 0

    async def _save(self, bos: list) -> int:
        """落库：按 (symbol, start_date) 幂等 upsert。

        ⚠️ 曾用名是「历史事件」，不设覆盖清理——清掉会把历史抹掉。
        """
        if not bos:
            return 0
        try:
            from models.base_name_change import (
                BaseNameChangeDB,
            )
        except ImportError:
            logger.debug("tech_name_change 表未建，跳过入库")
            return 0
        rows = [
            {
                "symbol": bo.symbol, "name": bo.name, "start_date": bo.start_date,
                "end_date": bo.end_date, "ann_date": bo.ann_date,
                "change_reason": bo.change_reason, "data_source": "tushare",
            }
            for bo in bos
        ]
        return await upsert_rows(
            BaseNameChangeDB, rows, ["symbol", "start_date"],
            immutable_cols=["symbol", "start_date"],
        )


__all__ = ["NameChangeService"]
