"""DividendRepository：分红送股仓储

模式：upsert（UK = symbol + end_date + div_proc）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import BaseDividendBO
from contexts.market.infrastructure.persistence.models.base_dividend import (
    BaseDividendDB,
)

logger = logging.getLogger(__name__)


class DividendRepository:
    """分红送股仓储（实现 domain Protocol）"""

    async def save(self, bos: list[BaseDividendBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(BaseDividendDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in BaseDividendDB.__table__.columns
            if c.name not in ("id", "created_at", "updated_at", "symbol", "end_date", "div_proc")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "end_date", "div_proc"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: BaseDividendBO) -> dict:
        return {
            "symbol": b.symbol,
            "end_date": b.end_date,
            "ann_date": b.ann_date,
            "record_date": b.record_date,
            "ex_date": b.ex_date,
            "pay_date": b.pay_date,
            "div_proc": b.div_proc,
            "stk_div": b.stk_div,
            "stk_bo_rate": b.stk_bo_rate,
            "stk_co_rate": b.stk_co_rate,
            "cash_div": b.cash_div,
            "cash_div_tax": b.cash_div_tax,
            "div_listdate": b.div_listdate,
            "imp_ann_date": b.imp_ann_date,
        }


__all__ = ["DividendRepository"]
