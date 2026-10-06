"""停复牌仓储实现（base_suspends）

无 UK，按 id 自增。重复采集做"先删后写"按 (symbol, trade_date)。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.base_suspend.entity import BaseSuspend
from domain.entitys.base_suspend.repository import BaseSuspendRepository
from infrastructure.persistence.models.base_suspend import BaseSuspendDB


class BaseSuspendRepoImpl:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_entity(row: BaseSuspendDB) -> BaseSuspend:
        return BaseSuspend(
            id=row.id, symbol=row.symbol, trade_date=row.trade_date,
            data_source=row.data_source,
            suspend_timing=row.suspend_timing, suspend_type=row.suspend_type,
        )

    async def save(self, entity: BaseSuspend) -> BaseSuspend:
        await self.save_batch([entity])
        return entity

    async def save_batch(self, entities: list[BaseSuspend]) -> int:
        if not entities:
            return 0
        symbols = {e.symbol for e in entities}
        # 先按 symbol 删除，再全量插入（停复牌日期级数据，量极小）
        for s in symbols:
            await self._session.execute(
                delete(BaseSuspendDB).where(BaseSuspendDB.symbol == s)
            )
        for e in entities:
            self._session.add(BaseSuspendDB(
                symbol=e.symbol, trade_date=e.trade_date,
                data_source=e.data_source,
                suspend_timing=e.suspend_timing, suspend_type=e.suspend_type,
            ))
        await self._session.commit()
        return len(entities)

    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[BaseSuspend]:
        stmt = select(BaseSuspendDB).where(BaseSuspendDB.symbol == symbol)
        if start_date:
            stmt = stmt.where(BaseSuspendDB.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(BaseSuspendDB.trade_date <= end_date)
        stmt = stmt.order_by(BaseSuspendDB.trade_date.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]


BaseSuspendRepoImpl.__implements_protocol__ = BaseSuspendRepository