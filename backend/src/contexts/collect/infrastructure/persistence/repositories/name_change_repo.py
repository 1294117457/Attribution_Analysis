"""NameChangeRepository：股票曾用名仓储

模式：upsert（UK = symbol + start_date）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import BaseNameChangeBO
from contexts.market.infrastructure.persistence.models.base_name_change import (
    BaseNameChangeDB,
)

logger = logging.getLogger(__name__)


class NameChangeRepository:
    """股票曾用名仓储（实现 domain Protocol）"""

    async def save(self, bos: list[BaseNameChangeBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(BaseNameChangeDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in BaseNameChangeDB.__table__.columns
            if c.name not in ("id", "created_at", "updated_at", "symbol", "start_date")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "start_date"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: BaseNameChangeBO) -> dict:
        return {
            "symbol": b.symbol,
            "name": b.name,
            "start_date": b.start_date,
            "end_date": b.end_date,
            "ann_date": b.ann_date,
            "change_reason": b.change_reason,
        }


__all__ = ["NameChangeRepository"]
