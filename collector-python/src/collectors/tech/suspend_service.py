"""SuspendService：停复牌 service（按 trade_date 一次性）"""
from __future__ import annotations

import logging
from datetime import date

from collectors.base import CollectResult, RateLimited
from collectors.tech.SuspendTushareFetcher import (
    SuspendTushareFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)


class SuspendService:
    name = "suspend"
    facet = "tech"
    label = "停复牌"
    strategy = "incremental"
    RANGE = {"start_key": "start_date", "end_key": "end_date", "granularity": "trade_day"}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: SuspendTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or SuspendTushareFetcher()

    async def collect(self, params: dict) -> CollectResult:
        td = params.get("trade_date")
        if not td:
            return CollectResult(fail=1, message="trade_date 必填")
        if not isinstance(td, date):
            td = date.fromisoformat(str(td))
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                bos = await self._fetcher.fetch(trade_date=td)
                saved = await self._save(td, bos)
                return CollectResult(
                    total=1, success=1, saved=saved, skip=1 if not bos else 0,
                    message=f"停复牌 {td}: {len(bos)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")

    async def _save(self, td: date, bos: list) -> int:
        """落库：按 trade_date 删除当日旧记录后插入（当日覆盖语义）。

        ⚠️ tech_suspend 主键是自增 id，**无唯一约束** → 不能用 ON CONFLICT upsert。
        """
        if not bos:
            return 0
        try:
            from models.base_suspend import (
                BaseSuspendDB,
            )
        except ImportError:
            logger.debug("tech_suspend 表未建，跳过入库")
            return 0
        rows = [
            {
                "symbol": bo.symbol, "trade_date": bo.trade_date,
                "suspend_timing": bo.suspend_timing, "suspend_type": bo.suspend_type,
                "data_source": "tushare",
            }
            for bo in bos
        ]
        from sqlalchemy import delete

        from core.db import raw_session_factory

        async with raw_session_factory() as session:
            await session.execute(
                delete(BaseSuspendDB).where(BaseSuspendDB.trade_date == td)
            )
            await session.execute(BaseSuspendDB.__table__.insert(), rows)
            await session.commit()
            return len(rows)


__all__ = ["SuspendService"]
