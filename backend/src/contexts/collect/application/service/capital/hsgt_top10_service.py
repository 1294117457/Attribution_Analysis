"""HsgtTop10Service：沪深港通前 10 持仓 service（按 trade_date 一次性）"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.collect.application.service.base import CollectResult, RateLimited
from contexts.collect.infrastructure.fetcher.capital.HsgtTop10TushareFetcher import (
    HsgtTop10TushareFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class HsgtTop10Service:
    name = "hsgt_top10"
    facet = "capital"
    sub_facet = "hsgt"
    label = "沪深港通前 10 持仓"
    DEFAULT_PARAMS = {"trade_date": None}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: HsgtTop10TushareFetcher | None = None) -> None:
        self._fetcher = fetcher or HsgtTop10TushareFetcher()

    async def collect(self, params: dict) -> CollectResult:
        td = params.get("trade_date")
        if not td:
            td = date.today()  # 全量模式：默认今天
        if not isinstance(td, date):
            td = date.fromisoformat(str(td))
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                items = await self._fetcher.fetch(trade_date=td)
                saved = await self._save(td, items)
                return CollectResult(
                    total=1, success=1, saved=saved,
                    message=f"沪深港通前 10 {td}: {len(items)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")

    async def _save(self, td: date, items: list) -> int:
        if not items:
            return 0
        from contexts.collect.infrastructure.persistence.models.cap_hsgt_top10 import (
            CapHsgtTop10DB,
        )
        rows = [
            {
                "trade_date": r["trade_date"], "symbol": r["symbol"],
                "holding_days": r["holding_days"], "share_ratio": r["share_ratio"],
                "hold_amount": r["hold_amount"], "net_amount": r["net_amount"],
            }
            for r in items
        ]
        async with db_session_factory() as session:
            await session.execute(delete(CapHsgtTop10DB).where(CapHsgtTop10DB.trade_date == td))
            stmt = pg_insert(CapHsgtTop10DB).values(rows)
            r = await session.execute(stmt)
            await session.commit()
            return r.rowcount or 0


__all__ = ["HsgtTop10Service"]
