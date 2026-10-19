"""AdjFactorRepository：复权因子仓储

模式：upsert（UK = symbol + trade_date）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import BaseAdjFactorBO
from contexts.market.infrastructure.persistence.models.base_adj_factor import (
    BaseAdjFactorDB,
)

logger = logging.getLogger(__name__)


class AdjFactorRepository:
    """复权因子仓储（实现 domain Protocol）"""

    async def save(self, bos: list[BaseAdjFactorBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(BaseAdjFactorDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in BaseAdjFactorDB.__table__.columns
            if c.name not in ("id", "created_at", "updated_at", "symbol", "trade_date")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "trade_date"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: BaseAdjFactorBO) -> dict:
        return {
            "symbol": b.symbol,
            "trade_date": b.trade_date,
            "adj_factor": b.adj_factor,
        }


__all__ = ["AdjFactorRepository"]
