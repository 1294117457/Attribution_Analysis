"""股东户数仓储实现（cap_holder_nums）

UK: (symbol, end_date)。SymboledEntity（无 trade_date），按 end_date 列做日期范围查询。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.cap_holder_num.entity import CapHolderNum
from domain.entitys.cap_holder_num.repository import CapHolderNumRepository
from infrastructure.persistence.models.cap_holder_num import CapHolderNumDB
from infrastructure.persistence.repositories._symboled_dated_repo import (
    save_batch_symboled_dated,
)


_VALUE_COLUMNS = [
    "ann_date", "holder_num", "holder_nums", "data_source",
]
# UK 是 (symbol, end_date)，不是通用的 (symbol, trade_date)
_KEY_COLUMNS = ["symbol", "end_date"]
_UK = "uq_cap_holder_nums_uk"


class CapHolderNumRepoImpl:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_entity(row: CapHolderNumDB) -> CapHolderNum:
        return CapHolderNum(
            id=row.id, symbol=row.symbol, data_source=row.data_source,
            end_date=row.end_date, ann_date=row.ann_date,
            holder_num=row.holder_num, holder_nums=row.holder_nums,
        )

    async def save(self, entity: CapHolderNum) -> CapHolderNum:
        await self.save_batch([entity])
        return entity

    async def save_batch(self, entities: list[CapHolderNum]) -> int:
        return await save_batch_symboled_dated(
            self._session, CapHolderNumDB, entities, _VALUE_COLUMNS, _UK,
            key_columns=_KEY_COLUMNS,
        )

    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapHolderNum]:
        # SymboledEntity 字段名是 end_date 不是 trade_date
        stmt = select(CapHolderNumDB).where(CapHolderNumDB.symbol == symbol)
        if start_date:
            stmt = stmt.where(CapHolderNumDB.end_date >= start_date)
        if end_date:
            stmt = stmt.where(CapHolderNumDB.end_date <= end_date)
        stmt = stmt.order_by(CapHolderNumDB.end_date.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]


CapHolderNumRepoImpl.__implements_protocol__ = CapHolderNumRepository