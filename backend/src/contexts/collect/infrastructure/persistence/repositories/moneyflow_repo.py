"""MoneyflowRepository：个股资金流向仓储

模式：upsert（UK = symbol + trade_date）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import CapMoneyflowBO
from contexts.market.infrastructure.persistence.models.cap_moneyflow import (
    CapMoneyflowDB,
)

logger = logging.getLogger(__name__)


class MoneyflowRepository:
    """个股资金流向仓储（实现 domain Protocol）"""

    async def save(self, bos: list[CapMoneyflowBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(CapMoneyflowDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in CapMoneyflowDB.__table__.columns
            if c.name not in ("id", "created_at", "updated_at", "symbol", "trade_date")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "trade_date"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: CapMoneyflowBO) -> dict:
        return {
            "symbol": b.symbol,
            "trade_date": b.trade_date,
            "buy_sm_vol": b.buy_sm_vol,
            "buy_sm_amount": b.buy_sm_amount,
            "sell_sm_vol": b.sell_sm_vol,
            "sell_sm_amount": b.sell_sm_amount,
            "buy_md_vol": b.buy_md_vol,
            "buy_md_amount": b.buy_md_amount,
            "sell_md_vol": b.sell_md_vol,
            "sell_md_amount": b.sell_md_amount,
            "buy_lg_vol": b.buy_lg_vol,
            "buy_lg_amount": b.buy_lg_amount,
            "sell_lg_vol": b.sell_lg_vol,
            "sell_lg_amount": b.sell_lg_amount,
            "buy_elg_vol": b.buy_elg_vol,
            "buy_elg_amount": b.buy_elg_amount,
            "sell_elg_vol": b.sell_elg_vol,
            "sell_elg_amount": b.sell_elg_amount,
            "net_mf_vol": b.net_mf_vol,
            "net_mf_amount": b.net_mf_amount,
        }


__all__ = ["MoneyflowRepository"]
