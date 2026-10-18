"""MoneyflowService：个股资金流向 service（按 trade_date 一次性全市场）"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.collect.application.service.base import CollectResult, RateLimited
from contexts.collect.infrastructure.fetcher.capital.MoneyflowTushareFetcher import (
    MoneyflowTushareFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class MoneyflowService:
    name = "moneyflow"
    facet = "capital"
    sub_facet = "moneyflow"
    label = "个股资金流向"
    DEFAULT_PARAMS = {"trade_date": None}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: MoneyflowTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or MoneyflowTushareFetcher()

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
                    message=f"资金流 {td}: 获取 {len(bos)} 条, 写入 {saved} 条",
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
            from contexts.collect.infrastructure.persistence.models.cap_moneyflow import (
                CapMoneyflowDB,
            )
        except ImportError:
            logger.debug("cap_moneyflow 表未建，跳过入库")
            return 0
        rows = [
            {
                "symbol": bo.symbol, "trade_date": bo.trade_date,
                "buy_sm_vol": bo.buy_sm_vol, "buy_sm_amount": bo.buy_sm_amount,
                "sell_sm_vol": bo.sell_sm_vol, "sell_sm_amount": bo.sell_sm_amount,
                "buy_md_vol": bo.buy_md_vol, "buy_md_amount": bo.buy_md_amount,
                "sell_md_vol": bo.sell_md_vol, "sell_md_amount": bo.sell_md_amount,
                "buy_lg_vol": bo.buy_lg_vol, "buy_lg_amount": bo.buy_lg_amount,
                "sell_lg_vol": bo.sell_lg_vol, "sell_lg_amount": bo.sell_lg_amount,
                "buy_elg_vol": bo.buy_elg_vol, "buy_elg_amount": bo.buy_elg_amount,
                "sell_elg_vol": bo.sell_elg_vol, "sell_elg_amount": bo.sell_elg_amount,
                "net_mf_vol": bo.net_mf_vol, "net_mf_amount": bo.net_mf_amount,
            }
            for bo in bos
        ]
        async with db_session_factory() as session:
            await session.execute(delete(CapMoneyflowDB).where(CapMoneyflowDB.trade_date == td))
            stmt = pg_insert(CapMoneyflowDB).values(rows)
            r = await session.execute(stmt)
            await session.commit()
            return r.rowcount or 0


__all__ = ["MoneyflowService"]
