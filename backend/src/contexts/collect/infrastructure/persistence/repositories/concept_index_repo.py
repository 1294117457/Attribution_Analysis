"""ConceptIndexRepository：概念指数日 K 仓储

模式：upsert（UK = index_code + trade_date）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.concept.application.bo.concept import ConceptIndexTHBO
from contexts.concept.infrastructure.persistence.models.concept import ConceptIndexTHDB

logger = logging.getLogger(__name__)


class ConceptIndexRepository:
    """概念指数日 K 仓储（实现 domain Protocol）"""

    async def save(self, bos: list[ConceptIndexTHBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(ConceptIndexTHDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in ConceptIndexTHDB.__table__.columns
            if c.name not in (
                "id", "captured_at",
                "index_code", "trade_date",
            )
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["index_code", "trade_date"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: ConceptIndexTHBO) -> dict:
        return {
            "index_code": b.index_code,
            "concept_name": b.concept_name,
            "trade_date": b.trade_date,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
            "amount": b.amount,
            "change": b.change,
            "change_pct": b.change_pct,
        }


__all__ = ["ConceptIndexRepository"]
