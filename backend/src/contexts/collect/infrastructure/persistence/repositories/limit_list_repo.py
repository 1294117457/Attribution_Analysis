"""LimitListRepository：每日涨跌停板仓储

模式：upsert（UK = trade_date + symbol + limit_type）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import CapLimitListDBO
from contexts.collect.infrastructure.persistence.models.capital_limit_list_d import (
    CapitalLimitListDDB,
)

logger = logging.getLogger(__name__)


class LimitListRepository:
    """每日涨跌停板仓储（实现 domain Protocol）"""

    async def save(self, bos: list[CapLimitListDBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(CapitalLimitListDDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in CapitalLimitListDDB.__table__.columns
            if c.name not in (
                "id", "created_at", "updated_at",
                "trade_date", "symbol", "limit_type",
            )
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "symbol", "limit_type"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: CapLimitListDBO) -> dict:
        return {
            "trade_date": b.trade_date,
            "symbol": b.symbol,
            "industry": b.industry,
            "name": b.name,
            "close": b.close,
            "pct_chg": b.pct_chg,
            "amount": b.amount,
            "limit_amount": b.limit_amount,
            "float_mv": b.float_mv,
            "total_mv": b.total_mv,
            "turnover_ratio": b.turnover_ratio,
            "fd_amount": b.fd_amount,
            "first_time": b.first_time,
            "last_time": b.last_time,
            "open_times": b.open_times,
            "up_stat": b.up_stat,
            "limit_times": b.limit_times,
            "limit_type": b.limit_type,
        }


__all__ = ["LimitListRepository"]
