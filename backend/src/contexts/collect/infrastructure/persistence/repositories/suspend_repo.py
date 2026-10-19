"""SuspendRepository：停复牌仓储

模式：upsert（UK = symbol + trade_date）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import BaseSuspendBO
from contexts.market.infrastructure.persistence.models.base_suspend import (
    BaseSuspendDB,
)

logger = logging.getLogger(__name__)


class SuspendRepository:
    """停复牌仓储（实现 domain Protocol）"""

    async def save(self, bos: list[BaseSuspendBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(BaseSuspendDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in BaseSuspendDB.__table__.columns
            if c.name not in ("id", "created_at", "updated_at", "symbol", "trade_date")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "trade_date"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: BaseSuspendBO) -> dict:
        return {
            "symbol": b.symbol,
            "trade_date": b.trade_date,
            "suspend_timing": b.suspend_timing,
            "suspend_type": b.suspend_type,
        }


__all__ = ["SuspendRepository"]
