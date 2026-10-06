"""大宗交易仓储实现（cap_block_trades）

无 UK，按 (trade_date, symbol, buyer, seller) 自然主键。
直接 id 自增，重复采集时做"先删后写"以保证最新。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.cap_block_trade.entity import CapBlockTrade
from domain.entitys.cap_block_trade.repository import CapBlockTradeRepository
from infrastructure.persistence.models.cap_block_trade import CapBlockTradeDB


class CapBlockTradeRepoImpl:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_entity(row: CapBlockTradeDB) -> CapBlockTrade:
        return CapBlockTrade(
            id=row.id, trade_date=row.trade_date, symbol=row.symbol,
            data_source=row.data_source,
            name=row.name, price=row.price, vol=row.vol, amount=row.amount,
            buyer=row.buyer, seller=row.seller,
        )

    async def save(self, entity: CapBlockTrade) -> CapBlockTrade:
        row = CapBlockTradeDB(
            trade_date=entity.trade_date, symbol=entity.symbol,
            data_source=entity.data_source,
            name=entity.name, price=entity.price, vol=entity.vol,
            amount=entity.amount, buyer=entity.buyer, seller=entity.seller,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.commit()
        entity.id = row.id
        return entity

    async def save_batch(self, entities: list[CapBlockTrade]) -> int:
        """大宗交易按 trade_date 整批替换：先删后写。"""
        if not entities:
            return 0
        dates = {e.trade_date for e in entities}
        for d in dates:
            await self._session.execute(
                delete(CapBlockTradeDB).where(CapBlockTradeDB.trade_date == d)
            )
        for e in entities:
            self._session.add(CapBlockTradeDB(
                trade_date=e.trade_date, symbol=e.symbol,
                data_source=e.data_source,
                name=e.name, price=e.price, vol=e.vol, amount=e.amount,
                buyer=e.buyer, seller=e.seller,
            ))
        await self._session.commit()
        return len(entities)

    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapBlockTrade]:
        stmt = select(CapBlockTradeDB).where(CapBlockTradeDB.symbol == symbol)
        if start_date:
            stmt = stmt.where(CapBlockTradeDB.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(CapBlockTradeDB.trade_date <= end_date)
        stmt = stmt.order_by(CapBlockTradeDB.trade_date.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]


CapBlockTradeRepoImpl.__implements_protocol__ = CapBlockTradeRepository