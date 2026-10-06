"""复权因子仓储实现（base_adj_factors）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.base_adj_factor.entity import BaseAdjFactor
from domain.entitys.base_adj_factor.repository import BaseAdjFactorRepository
from infrastructure.persistence.models.base_adj_factor import BaseAdjFactorDB
from infrastructure.persistence.repositories._symboled_dated_repo import (
    find_by_symbol_and_date_range,
    save_batch_symboled_dated,
)


_VALUE_COLUMNS = ["adj_factor", "data_source"]
_UK = "uq_base_adj_factors_uk"


class BaseAdjFactorRepoImpl:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_entity(row: BaseAdjFactorDB) -> BaseAdjFactor:
        return BaseAdjFactor(
            id=row.id, symbol=row.symbol, trade_date=row.trade_date,
            data_source=row.data_source,
            adj_factor=row.adj_factor,
        )

    async def save(self, entity: BaseAdjFactor) -> BaseAdjFactor:
        await self.save_batch([entity])
        return entity

    async def save_batch(self, entities: list[BaseAdjFactor]) -> int:
        return await save_batch_symboled_dated(
            self._session, BaseAdjFactorDB, entities, _VALUE_COLUMNS, _UK,
        )

    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[BaseAdjFactor]:
        rows = await find_by_symbol_and_date_range(
            self._session, BaseAdjFactorDB, symbol, start_date, end_date,
        )
        return [self._to_entity(r) for r in rows]


BaseAdjFactorRepoImpl.__implements_protocol__ = BaseAdjFactorRepository