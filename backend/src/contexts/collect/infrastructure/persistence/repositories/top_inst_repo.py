"""TopInstRepository：龙虎榜机构席位明细仓储

模式：upsert（UK = trade_date + symbol + exalter + side）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import CapTopInstBO
from contexts.market.infrastructure.persistence.models.cap_top_inst import (
    CapTopInstDB,
)

logger = logging.getLogger(__name__)


class TopInstRepository:
    """龙虎榜机构席位明细仓储（实现 domain Protocol）"""

    async def save(self, bos: list[CapTopInstBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(CapTopInstDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in CapTopInstDB.__table__.columns
            if c.name not in (
                "id", "created_at", "updated_at",
                "trade_date", "symbol", "exalter", "side",
            )
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "symbol", "exalter", "side"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: CapTopInstBO) -> dict:
        return {
            "trade_date": b.trade_date,
            "symbol": b.symbol,
            "exalter": b.exalter,
            "side": b.side,
            "reason": b.reason,
            "buy": b.buy,
            "buy_rate": b.buy_rate,
            "sell": b.sell,
            "sell_rate": b.sell_rate,
            "net_buy": b.net_buy,
        }


__all__ = ["TopInstRepository"]
