"""BlockTradeRepository：大宗交易仓储

模式：upsert（UK = trade_date + symbol + buyer + seller）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import CapBlockTradeBO
from contexts.market.infrastructure.persistence.models.cap_block_trade import (
    CapBlockTradeDB,
)

logger = logging.getLogger(__name__)


class BlockTradeRepository:
    """大宗交易仓储（实现 domain Protocol）"""

    async def save(self, bos: list[CapBlockTradeBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(CapBlockTradeDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in CapBlockTradeDB.__table__.columns
            if c.name not in (
                "id", "created_at", "updated_at",
                "trade_date", "symbol", "buyer", "seller",
            )
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "symbol", "buyer", "seller"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: CapBlockTradeBO) -> dict:
        return {
            "trade_date": b.trade_date,
            "symbol": b.symbol,
            "name": b.name,
            "price": b.price,
            "vol": b.vol,
            "amount": b.amount,
            "buyer": b.buyer,
            "seller": b.seller,
        }


__all__ = ["BlockTradeRepository"]
