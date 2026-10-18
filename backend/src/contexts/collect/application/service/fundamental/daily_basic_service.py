"""DailyBasicService：每日估值 service（按 trade_date 一次性）"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.collect.application.service.base import CollectResult, RateLimited
from contexts.collect.infrastructure.fetcher.fundamental.DailyBasicTushareFetcher import (
    DailyBasicTushareFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class DailyBasicService:
    name = "daily_basic"
    facet = "fundamental"
    sub_facet = "valuation"
    label = "每日估值"
    DEFAULT_PARAMS = {"trade_date": None}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: DailyBasicTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or DailyBasicTushareFetcher()

    async def collect(self, params: dict) -> CollectResult:
        td = params.get("trade_date")
        if not td:
            td = date.today()  # 全量模式：默认今天
        if not isinstance(td, date):
            td = date.fromisoformat(str(td))
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                bos = await self._fetcher.fetch(trade_date=td)
                saved = await self._save(td, bos)
                return CollectResult(
                    total=1, success=1, saved=saved, skip=1 if not bos else 0,
                    message=f"每日估值 {td}: {len(bos)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")

    async def _save(self, td, bos) -> int:
        if not bos:
            return 0
        try:
            from contexts.collect.infrastructure.persistence.models.fin_daily_basic import (
                FinDailyBasicDB,
            )
        except ImportError:
            logger.debug("fin_daily_basic 表未建，跳过入库")
            return 0
        rows = [
            {
                "symbol": bo.symbol, "trade_date": bo.trade_date,
                "close": bo.close, "turnover_rate": bo.turnover_rate,
                "turnover_rate_f": bo.turnover_rate_f, "volume_ratio": bo.volume_ratio,
                "pe": bo.pe, "pe_ttm": bo.pe_ttm, "pb": bo.pb,
                "ps": bo.ps, "ps_ttm": bo.ps_ttm, "dv_ratio": bo.dv_ratio,
                "dv_ttm": bo.dv_ttm, "total_share": bo.total_share,
                "float_share": bo.float_share, "free_share": bo.free_share,
                "total_mv": bo.total_mv, "circ_mv": bo.circ_mv,
            }
            for bo in bos
        ]
        async with db_session_factory() as session:
            await session.execute(delete(FinDailyBasicDB).where(FinDailyBasicDB.trade_date == td))
            stmt = pg_insert(FinDailyBasicDB).values(rows)
            r = await session.execute(stmt)
            await session.commit()
            return r.rowcount or 0


__all__ = ["DailyBasicService"]
