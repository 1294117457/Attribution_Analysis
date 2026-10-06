"""前十大股东仓储实现（fin_top10_holders）

UK: (symbol, end_date, ann_date, holder_name)。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.fin_top10_holders.entity import FinTop10Holders
from domain.entitys.fin_top10_holders.repository import FinTop10HoldersRepository
from infrastructure.persistence.models.fin_top10_holders import FinTop10HolderDB
from infrastructure.persistence.repositories._symboled_dated_repo import chunks


_VALUE_COLUMNS = [
    "hold_amount", "hold_ratio", "hold_float_ratio", "hold_change",
    "holder_type", "data_source",
]


class FinTop10HoldersRepoImpl:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_entity(row: FinTop10HolderDB) -> FinTop10Holders:
        return FinTop10Holders(
            id=row.id, symbol=row.symbol, data_source=row.data_source,
            holder_name=row.holder_name, end_date=row.end_date,
            ann_date=row.ann_date,
            hold_amount=row.hold_amount, hold_ratio=row.hold_ratio,
            hold_float_ratio=row.hold_float_ratio,
            hold_change=row.hold_change, holder_type=row.holder_type,
        )

    async def save(self, entity: FinTop10Holders) -> FinTop10Holders:
        await self.save_batch([entity])
        return entity

    async def save_batch(self, entities: list[FinTop10Holders]) -> int:
        if not entities:
            return 0
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        total = 0
        for batch in chunks(entities, 500):
            rows = [
                {
                    "symbol": e.symbol, "end_date": e.end_date,
                    "ann_date": e.ann_date, "holder_name": e.holder_name,
                    "data_source": e.data_source,
                    "hold_amount": e.hold_amount,
                    "hold_ratio": e.hold_ratio,
                    "hold_float_ratio": e.hold_float_ratio,
                    "hold_change": e.hold_change,
                    "holder_type": e.holder_type,
                }
                for e in batch
            ]
            stmt = pg_insert(FinTop10HolderDB).values(rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_fin_top10_holders_uk",
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
    ) -> list[FinTop10Holders]:
        stmt = select(FinTop10HolderDB).where(FinTop10HolderDB.symbol == symbol)
        if start_date:
            stmt = stmt.where(FinTop10HolderDB.end_date >= start_date)
        if end_date:
            stmt = stmt.where(FinTop10HolderDB.end_date <= end_date)
        stmt = stmt.order_by(
            FinTop10HolderDB.end_date.desc(), FinTop10HolderDB.holder_name,
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]


FinTop10HoldersRepoImpl.__implements_protocol__ = FinTop10HoldersRepository