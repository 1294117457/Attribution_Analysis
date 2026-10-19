"""HsgtTop10Repository：沪深股通十大成交股仓储

模式：upsert（UK = trade_date + market_type + symbol + rank）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import CapHsgtTop10BO
from contexts.collect.infrastructure.persistence.models.cap_hsgt_top10 import (
    CapitalHsgtTop10DB,
)

logger = logging.getLogger(__name__)


class HsgtTop10Repository:
    """沪深股通十大成交股仓储（实现 domain Protocol）"""

    async def save(self, bos: list[CapHsgtTop10BO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(CapitalHsgtTop10DB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in CapitalHsgtTop10DB.__table__.columns
            if c.name not in (
                "id", "created_at", "updated_at",
                "trade_date", "market_type", "symbol", "rank",
            )
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "market_type", "symbol", "rank"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: CapHsgtTop10BO) -> dict:
        return {
            "trade_date": b.trade_date,
            "symbol": b.symbol,
            "name": b.name,
            "market_type": b.market_type,
            "rank": b.rank,
            "close": b.close,
            "p_change": b.p_change,
            "amount": b.amount,
            "net_amount": b.net_amount,
            "buy": b.buy,
            "sell": b.sell,
        }


__all__ = ["HsgtTop10Repository"]
