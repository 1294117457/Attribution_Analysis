"""BlockTradeService：大宗交易 service（按 trade_date 一次性）"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.collect.application.service.base import CollectResult, RateLimited
from contexts.collect.infrastructure.fetcher.capital.BlockTradeTushareFetcher import (
    BlockTradeTushareFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class BlockTradeService:
    name = "block_trade"
    facet = "capital"
    sub_facet = "block"
    label = "大宗交易"
    DEFAULT_PARAMS = {"trade_date": None}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: BlockTradeTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or BlockTradeTushareFetcher()

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
                    message=f"大宗交易 {td}: {len(bos)} 条, 写入 {saved}",
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
            from contexts.collect.infrastructure.persistence.models.cap_block_trade import (
                CapBlockTradeDB,
            )
        except ImportError:
            logger.debug("cap_block_trade 表未建，跳过入库")
            return 0
        rows = [
            {
                "trade_date": bo.trade_date, "symbol": bo.symbol, "name": bo.name,
                "price": bo.price, "vol": bo.vol, "amount": bo.amount,
                "buyer": bo.buyer, "seller": bo.seller,
            }
            for bo in bos
        ]
        async with db_session_factory() as session:
            await session.execute(delete(CapBlockTradeDB).where(CapBlockTradeDB.trade_date == td))
            stmt = pg_insert(CapBlockTradeDB).values(rows)
            r = await session.execute(stmt)
            await session.commit()
            return r.rowcount or 0


__all__ = ["BlockTradeService"]
