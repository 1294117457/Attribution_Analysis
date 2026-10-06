"""股票曾用名仓储实现（base_name_changes）

UK: (symbol, start_date)。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.base_name_change.entity import BaseNameChange
from domain.entitys.base_name_change.repository import BaseNameChangeRepository
from infrastructure.persistence.models.base_name_change import BaseNameChangeDB
from infrastructure.persistence.repositories._symboled_dated_repo import chunks


_VALUE_COLUMNS = ["end_date", "ann_date", "change_reason", "data_source"]


class BaseNameChangeRepoImpl:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_entity(row: BaseNameChangeDB) -> BaseNameChange:
        return BaseNameChange(
            id=row.id, symbol=row.symbol, data_source=row.data_source,
            name=row.name, start_date=row.start_date,
            end_date=row.end_date, ann_date=row.ann_date,
            change_reason=row.change_reason,
        )

    async def save(self, entity: BaseNameChange) -> BaseNameChange:
        await self.save_batch([entity])
        return entity

    async def save_batch(self, entities: list[BaseNameChange]) -> int:
        if not entities:
            return 0
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        total = 0
        for batch in chunks(entities, 500):
            rows = [
                {
                    "symbol": e.symbol, "name": e.name,
                    "start_date": e.start_date, "data_source": e.data_source,
                    "end_date": e.end_date, "ann_date": e.ann_date,
                    "change_reason": e.change_reason,
                }
                for e in batch
            ]
            stmt = pg_insert(BaseNameChangeDB).values(rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_base_name_change_uk",
                set_={c: stmt.excluded[c] for c in _VALUE_COLUMNS},
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
    ) -> list[BaseNameChange]:
        stmt = select(BaseNameChangeDB).where(BaseNameChangeDB.symbol == symbol)
        if start_date:
            stmt = stmt.where(BaseNameChangeDB.start_date >= start_date)
        if end_date:
            stmt = stmt.where(BaseNameChangeDB.start_date <= end_date)
        stmt = stmt.order_by(BaseNameChangeDB.start_date.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]


BaseNameChangeRepoImpl.__implements_protocol__ = BaseNameChangeRepository