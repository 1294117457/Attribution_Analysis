"""TopListRepository：龙虎榜每日明细仓储

模式：upsert（UK = trade_date + symbol + reason）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import CapTopListBO
from contexts.market.infrastructure.persistence.models.cap_top_list import (
    CapTopListDB,
)

logger = logging.getLogger(__name__)


class TopListRepository:
    """龙虎榜每日明细仓储（实现 domain Protocol）"""

    async def save(self, bos: list[CapTopListBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(CapTopListDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in CapTopListDB.__table__.columns
            if c.name not in (
                "id", "created_at", "updated_at",
                "trade_date", "symbol", "reason",
            )
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "symbol", "reason"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: CapTopListBO) -> dict:
        return {
            "trade_date": b.trade_date,
            "symbol": b.symbol,
            "name": b.name,
            "close": b.close,
            "pct_change": b.pct_change,
            "turnover_rate": b.turnover_rate,
            "amount": b.amount,
            "l_sell": b.l_sell,
            "l_buy": b.l_buy,
            "l_amount": b.l_amount,
            "net_amount": b.net_amount,
            "net_rate": b.net_rate,
            "amount_rate": b.amount_rate,
            "float_values": b.float_values,
            "reason": b.reason,
        }


__all__ = ["TopListRepository"]
