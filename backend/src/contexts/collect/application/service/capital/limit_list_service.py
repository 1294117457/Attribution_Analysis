"""LimitListService：每日涨跌停板 service（按 trade_date 一次性）"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.collect.application.service.base import CollectResult, RateLimited
from contexts.collect.infrastructure.fetcher.capital.LimitListTushareFetcher import (
    LimitListTushareFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class LimitListService:
    name = "limit_list_d"
    facet = "capital"
    sub_facet = "limit"
    label = "每日涨跌停板"
    DEFAULT_PARAMS = {"trade_date": None}
    RATE_LIMIT = ("tushare", 100, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: LimitListTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or LimitListTushareFetcher()

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
                    total=1, success=1, saved=saved, skip=1 if not items else 0,
                    message=f"涨跌停 {td}: {len(items)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")

    async def _save(self, td, items) -> int:
        if not items:
            return 0
        try:
            from contexts.collect.infrastructure.persistence.models.market_limit_list import (
                MarketLimitListDB,
            )
        except ImportError:
            logger.debug("market_limit_list 表未建，跳过入库")
            return 0
        rows = [
            {
                "trade_date": r["trade_date"], "symbol": r["symbol"], "name": r["name"],
                "close_price": r["close_price"], "change_rate": r["change_rate"],
                "limit_type": r["limit_type"], "board_count": r["board_count"],
                "first_limit_time": r["first_limit_time"],
                "board_strength": r["board_strength"], "reason": r["reason"],
            }
            for r in items
        ]
        async with db_session_factory() as session:
            await session.execute(delete(MarketLimitListDB).where(MarketLimitListDB.trade_date == td))
            stmt = pg_insert(MarketLimitListDB).values(rows)
            r = await session.execute(stmt)
            await session.commit()
            return r.rowcount or 0


__all__ = ["LimitListService"]
