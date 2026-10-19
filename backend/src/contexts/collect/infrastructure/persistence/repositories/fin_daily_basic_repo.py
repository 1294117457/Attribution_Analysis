"""FinDailyBasicRepository：日频估值指标仓储

模式：upsert（UK = symbol + trade_date）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import FinDailyBasicBO
from contexts.market.infrastructure.persistence.models.fin_daily_basic import (
    FinDailyBasicDB,
)

logger = logging.getLogger(__name__)


class FinDailyBasicRepository:
    """日频估值指标仓储（实现 domain Protocol）"""

    async def save(self, bos: list[FinDailyBasicBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(FinDailyBasicDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in FinDailyBasicDB.__table__.columns
            if c.name not in ("id", "created_at", "updated_at", "symbol", "trade_date")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "trade_date"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: FinDailyBasicBO) -> dict:
        return {
            "symbol": b.symbol,
            "trade_date": b.trade_date,
            "close": b.close,
            "turnover_rate": b.turnover_rate,
            "turnover_rate_f": b.turnover_rate_f,
            "volume_ratio": b.volume_ratio,
            "pe": b.pe,
            "pe_ttm": b.pe_ttm,
            "pb": b.pb,
            "ps": b.ps,
            "ps_ttm": b.ps_ttm,
            "dv_ratio": b.dv_ratio,
            "dv_ttm": b.dv_ttm,
            "total_share": b.total_share,
            "float_share": b.float_share,
            "free_share": b.free_share,
            "total_mv": b.total_mv,
            "circ_mv": b.circ_mv,
            "limit_status": b.limit_status,
        }


__all__ = ["FinDailyBasicRepository"]
