"""MoneyflowHsgtService：沪深港通资金流向 service（按 trade_date 一次性）"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.collect.application.service.base import CollectResult, RateLimited
from contexts.collect.infrastructure.fetcher.capital.MoneyflowHsgtTushareFetcher import (
    MoneyflowHsgtTushareFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class MoneyflowHsgtService:
    name = "moneyflow_hsgt"
    facet = "capital"
    sub_facet = "north_flow"
    label = "沪深港通资金流向"
    DEFAULT_PARAMS = {"trade_date": None}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: MoneyflowHsgtTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or MoneyflowHsgtTushareFetcher()

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
                    total=1, success=1, saved=saved,
                    message=f"沪深港通 {td}: {len(bos)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")

    async def _save(self, td: date, bos: list) -> int:
        if not bos:
            return 0
        try:
            from contexts.collect.infrastructure.persistence.models.cap_moneyflow_hsgt import (
                CapMoneyflowHsgtDB,
            )
        except ImportError:
            logger.debug("cap_moneyflow_hsgt 表未建，跳过入库")
            return 0
        rows = [
            {
                "trade_date": bo.trade_date,
                "hgt": getattr(bo, "hgt", None),
                "sgt": getattr(bo, "sgt", None),
                "north_money": getattr(bo, "north_money", None),
                "south_money": getattr(bo, "south_money", None),
            }
            for bo in bos
        ]
        async with db_session_factory() as session:
            await session.execute(delete(CapMoneyflowHsgtDB).where(CapMoneyflowHsgtDB.trade_date == td))
            stmt = pg_insert(CapMoneyflowHsgtDB).values(rows)
            r = await session.execute(stmt)
            await session.commit()
            return r.rowcount or 0


__all__ = ["MoneyflowHsgtService"]
