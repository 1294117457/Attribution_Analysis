"""MoneyflowHsgtRepository：沪深港通资金流向（按股票）仓储

模式：upsert（UK = trade_date + symbol + market_type）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import CapMoneyflowHsgtBO
from contexts.collect.infrastructure.persistence.models.cap_moneyflow_hsgt import (
    CapitalMoneyflowHsgtDB,
)

logger = logging.getLogger(__name__)


class MoneyflowHsgtRepository:
    """沪深港通资金流向仓储（实现 domain Protocol）"""

    async def save(self, bos: list[CapMoneyflowHsgtBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(CapitalMoneyflowHsgtDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in CapitalMoneyflowHsgtDB.__table__.columns
            if c.name not in (
                "id", "created_at", "updated_at",
                "trade_date", "symbol", "market_type",
            )
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "symbol", "market_type"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: CapMoneyflowHsgtBO) -> dict:
        return {
            "trade_date": b.trade_date,
            "symbol": b.symbol,
            "name": b.name,
            "market_type": b.market_type,
            "close": b.close,
            "p_change": b.p_change,
            "pct_change": b.pct_change,
            "rank": b.rank,
            "amount": b.amount,
            "net_amount": b.net_amount,
            "buy": b.buy,
            "sell": b.sell,
        }


__all__ = ["MoneyflowHsgtRepository"]
