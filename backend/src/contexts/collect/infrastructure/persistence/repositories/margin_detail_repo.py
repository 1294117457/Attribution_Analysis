"""MarginDetailRepository：个股两融明细仓储

模式：upsert（UK = symbol + trade_date）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import CapMarginDetailBO
from contexts.market.infrastructure.persistence.models.cap_margin_detail import (
    CapMarginDetailDB,
)

logger = logging.getLogger(__name__)


class MarginDetailRepository:
    """个股两融明细仓储（实现 domain Protocol）"""

    async def save(self, bos: list[CapMarginDetailBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(CapMarginDetailDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in CapMarginDetailDB.__table__.columns
            if c.name not in ("id", "created_at", "updated_at", "symbol", "trade_date")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "trade_date"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: CapMarginDetailBO) -> dict:
        return {
            "symbol": b.symbol,
            "trade_date": b.trade_date,
            "name": b.name,
            "rzye": b.rzye,
            "rqye": b.rqye,
            "rzmre": b.rzmre,
            "rqyl": b.rqyl,
            "rzche": b.rzche,
            "rqchl": b.rqchl,
            "rqmcl": b.rqmcl,
            "rzrqye": b.rzrqye,
        }


__all__ = ["MarginDetailRepository"]
