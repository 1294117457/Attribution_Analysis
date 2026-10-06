"""龙虎榜机构席位仓储实现（cap_top_insts）

UK 不固定：每条记录是 (trade_date, symbol, exalter, side) 唯一。
直接按主键 id 增删（无 UK 约束覆盖），但为简洁仍走 pg_insert + on_conflict_do_nothing。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.cap_top_inst.entity import CapTopInst
from domain.entitys.cap_top_inst.repository import CapTopInstRepository
from infrastructure.persistence.models.cap_top_inst import CapTopInstDB


class CapTopInstRepoImpl:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_entity(row: CapTopInstDB) -> CapTopInst:
        return CapTopInst(
            id=row.id, trade_date=row.trade_date, symbol=row.symbol,
            data_source=row.data_source,
            exalter=row.exalter, side=row.side,
            buy=row.buy, buy_rate=row.buy_rate,
            sell=row.sell, sell_rate=row.sell_rate,
            net_buy=row.net_buy, reason=row.reason,
        )

    async def save(self, entity: CapTopInst) -> CapTopInst:
        row = CapTopInstDB(
            trade_date=entity.trade_date, symbol=entity.symbol,
            data_source=entity.data_source,
            exalter=entity.exalter, side=entity.side,
            buy=entity.buy, buy_rate=entity.buy_rate,
            sell=entity.sell, sell_rate=entity.sell_rate,
            net_buy=entity.net_buy, reason=entity.reason,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.commit()
        entity.id = row.id
        return entity

    async def save_batch(self, entities: list[CapTopInst]) -> int:
        if not entities:
            return 0
        rows = [
            {
                "trade_date": e.trade_date, "symbol": e.symbol,
                "data_source": e.data_source,
                "exalter": e.exalter, "side": e.side,
                "buy": e.buy, "buy_rate": e.buy_rate,
                "sell": e.sell, "sell_rate": e.sell_rate,
                "net_buy": e.net_buy, "reason": e.reason,
            }
            for e in entities
        ]
        stmt = pg_insert(CapTopInstDB).values(rows)
        stmt = stmt.on_conflict_do_nothing()
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount or len(rows)

    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapTopInst]:
        stmt = select(CapTopInstDB).where(CapTopInstDB.symbol == symbol)
        if start_date:
            stmt = stmt.where(CapTopInstDB.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(CapTopInstDB.trade_date <= end_date)
        stmt = stmt.order_by(CapTopInstDB.trade_date.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]

    async def find_by_date_symbol(
        self,
        trade_date: date,
        symbol: str,
    ) -> list[CapTopInst]:
        """按 trade_date + symbol 查询（接口合约）"""
        stmt = (
            select(CapTopInstDB)
            .where(
                CapTopInstDB.symbol == symbol,
                CapTopInstDB.trade_date == trade_date,
            )
            .order_by(CapTopInstDB.side, CapTopInstDB.net_buy.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]


CapTopInstRepoImpl.__implements_protocol__ = CapTopInstRepository