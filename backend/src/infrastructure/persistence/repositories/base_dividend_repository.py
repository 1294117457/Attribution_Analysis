"""分红送股仓储实现（base_dividends）

UK: (symbol, end_date, div_proc)。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.base_dividend.entity import BaseDividend
from domain.entitys.base_dividend.repository import BaseDividendRepository
from infrastructure.persistence.models.base_dividend import BaseDividendDB
from infrastructure.persistence.repositories._symboled_dated_repo import (
    save_batch_symboled_dated,
)


_VALUE_COLUMNS = [
    "ann_date", "record_date", "ex_date", "pay_date",
    "stk_div", "stk_bo_rate", "stk_co_rate",
    "cash_div", "cash_div_tax", "data_source",
]


class BaseDividendRepoImpl:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_entity(row: BaseDividendDB) -> BaseDividend:
        return BaseDividend(
            id=row.id, symbol=row.symbol, data_source=row.data_source,
            end_date=row.end_date, ann_date=row.ann_date,
            record_date=row.record_date, ex_date=row.ex_date, pay_date=row.pay_date,
            div_proc=row.div_proc,
            stk_div=row.stk_div, stk_bo_rate=row.stk_bo_rate,
            stk_co_rate=row.stk_co_rate,
            cash_div=row.cash_div, cash_div_tax=row.cash_div_tax,
        )

    async def save(self, entity: BaseDividend) -> BaseDividend:
        await self.save_batch([entity])
        return entity

    async def save_batch(self, entities: list[BaseDividend]) -> int:
        # 走共用 helper：UK 是 (symbol, end_date, div_proc)，且需要对
        # 同一 UK 的多条记录去重（PG 的 ON CONFLICT 不允许批内重复冲突键）
        return await save_batch_symboled_dated(
            self._session, BaseDividendDB, entities, _VALUE_COLUMNS,
            "uq_base_dividends_uk",
            key_columns=["symbol", "end_date", "div_proc"],
        )

    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[BaseDividend]:
        stmt = select(BaseDividendDB).where(BaseDividendDB.symbol == symbol)
        if start_date:
            stmt = stmt.where(BaseDividendDB.end_date >= start_date)
        if end_date:
            stmt = stmt.where(BaseDividendDB.end_date <= end_date)
        stmt = stmt.order_by(BaseDividendDB.end_date.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]


BaseDividendRepoImpl.__implements_protocol__ = BaseDividendRepository