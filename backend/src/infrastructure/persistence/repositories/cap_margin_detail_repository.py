"""两融明细仓储实现（cap_margin_details）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.cap_margin_detail.entity import CapMarginDetail
from domain.entitys.cap_margin_detail.repository import CapMarginDetailRepository
from infrastructure.persistence.models.cap_margin_detail import CapMarginDetailDB
from infrastructure.persistence.repositories._symboled_dated_repo import (
    find_by_symbol_and_date_range,
    save_batch_symboled_dated,
)


_VALUE_COLUMNS = [
    "rzye", "rqye", "rzmre", "rqyl", "rzche", "rqchl", "rqmcl", "rzrqye",
    "data_source",
]
_UK = "uq_cap_margin_details_uk"


class CapMarginDetailRepoImpl:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_entity(row: CapMarginDetailDB) -> CapMarginDetail:
        return CapMarginDetail(
            id=row.id, symbol=row.symbol, trade_date=row.trade_date,
            data_source=row.data_source,
            rzye=row.rzye, rqye=row.rqye, rzmre=row.rzmre, rqyl=row.rqyl,
            rzche=row.rzche, rqchl=row.rqchl, rqmcl=row.rqmcl, rzrqye=row.rzrqye,
        )

    async def save(self, entity: CapMarginDetail) -> CapMarginDetail:
        await self.save_batch([entity])
        return entity

    async def save_batch(self, entities: list[CapMarginDetail]) -> int:
        return await save_batch_symboled_dated(
            self._session, CapMarginDetailDB, entities, _VALUE_COLUMNS, _UK,
        )

    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapMarginDetail]:
        rows = await find_by_symbol_and_date_range(
            self._session, CapMarginDetailDB, symbol, start_date, end_date,
        )
        return [self._to_entity(r) for r in rows]


CapMarginDetailRepoImpl.__implements_protocol__ = CapMarginDetailRepository