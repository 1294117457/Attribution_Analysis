"""FinTop10HoldersRepository：前十大股东仓储

模式：upsert（UK = symbol + end_date + ann_date + holder_name）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import FinTop10HoldersBO
from contexts.market.infrastructure.persistence.models.fin_top10_holders import (
    FinTop10HolderDB,
)

logger = logging.getLogger(__name__)


class FinTop10HoldersRepository:
    """前十大股东仓储（实现 domain Protocol）"""

    async def save(self, bos: list[FinTop10HoldersBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(FinTop10HolderDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in FinTop10HolderDB.__table__.columns
            if c.name not in (
                "id", "created_at", "updated_at",
                "symbol", "end_date", "ann_date", "holder_name",
            )
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "end_date", "ann_date", "holder_name"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: FinTop10HoldersBO) -> dict:
        return {
            "symbol": b.symbol,
            "ann_date": b.ann_date,
            "end_date": b.end_date,
            "holder_name": b.holder_name,
            "hold_amount": b.hold_amount,
            "hold_ratio": b.hold_ratio,
            "hold_float_ratio": b.hold_float_ratio,
            "hold_change": b.hold_change,
            "holder_type": b.holder_type,
        }


__all__ = ["FinTop10HoldersRepository"]
