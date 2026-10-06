"""龙虎榜每日汇总仓储实现（cap_top_lists）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.cap_top_list.entity import CapTopList
from domain.entitys.cap_top_list.repository import CapTopListRepository
from infrastructure.persistence.models.cap_top_list import CapTopListDB
from infrastructure.persistence.repositories._symboled_dated_repo import chunks


class CapTopListRepoImpl:
    """龙虎榜每日仓储实现

    注意：UK 是 (trade_date, symbol, reason)，不是标准 (symbol, trade_date)。
    所以 save_batch 自己实现（不能直接复用 save_batch_symboled_dated）。
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_entity(row: CapTopListDB) -> CapTopList:
        return CapTopList(
            id=row.id, trade_date=row.trade_date, symbol=row.symbol,
            data_source=row.data_source,
            name=row.name, close=row.close, pct_change=row.pct_change,
            turnover_rate=row.turnover_rate, amount=row.amount,
            l_sell=row.l_sell, l_buy=row.l_buy, l_amount=row.l_amount,
            net_amount=row.net_amount, net_rate=row.net_rate,
            amount_rate=row.amount_rate, float_values=row.float_values,
            reason=row.reason,
        )

    async def save(self, entity: CapTopList) -> CapTopList:
        await self.save_batch([entity])
        return entity

    async def save_batch(self, entities: list[CapTopList]) -> int:
        if not entities:
            return 0
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        total = 0
        for batch in chunks(entities, 500):
            rows = [
                {
                    "trade_date": e.trade_date,
                    "symbol": e.symbol,
                    "data_source": e.data_source,
                    "name": e.name,
                    "close": e.close,
                    "pct_change": e.pct_change,
                    "turnover_rate": e.turnover_rate,
                    "amount": e.amount,
                    "l_sell": e.l_sell,
                    "l_buy": e.l_buy,
                    "l_amount": e.l_amount,
                    "net_amount": e.net_amount,
                    "net_rate": e.net_rate,
                    "amount_rate": e.amount_rate,
                    "float_values": e.float_values,
                    "reason": e.reason,
                }
                for e in batch
            ]
            stmt = pg_insert(CapTopListDB).values(rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_cap_top_lists_uk",
                set_={c: stmt.excluded[c] for c in rows[0] if c not in ("trade_date", "symbol", "reason")},
            )
            result = await self._session.execute(stmt)
            total += result.rowcount or len(batch)
        await self._session.commit()
        return total

    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapTopList]:
        stmt = select(CapTopListDB).where(CapTopListDB.symbol == symbol)
        if start_date:
            stmt = stmt.where(CapTopListDB.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(CapTopListDB.trade_date <= end_date)
        stmt = stmt.order_by(CapTopListDB.trade_date.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]


CapTopListRepoImpl.__implements_protocol__ = CapTopListRepository