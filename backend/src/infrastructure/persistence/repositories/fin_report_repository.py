"""财报仓储实现（fin_reports）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import distinct, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.fin_report.entity import FinReport
from domain.entitys.fin_report.repository import FinReportRepository
from infrastructure.persistence.models.fin_report import FinReportDB

# 利润表任务只写这些列；资产负债 / 现金流列留给各自的任务，upsert 时不覆盖
_INCOME_COLUMNS = [
    "ann_date", "comp_type",
    "basic_eps", "diluted_eps", "total_revenue", "revenue",
    "operate_profit", "total_profit", "n_income", "n_income_attr_p",
]
_ALL_COLUMNS = [c.name for c in FinReportDB.__table__.columns if c.name not in ("id", "created_at", "updated_at")]


class FinReportRepoImpl:
    """财报仓储实现"""

    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_entity(row: FinReportDB) -> FinReport:
        return FinReport(id=row.id, **{c: getattr(row, c) for c in _ALL_COLUMNS})

    @staticmethod
    def _to_row(entity: FinReport) -> dict:
        return {
            "symbol": entity.symbol,
            "end_date": entity.end_date,
            "report_type": entity.report_type,
            "data_source": entity.data_source,
            **{c: getattr(entity, c) for c in _INCOME_COLUMNS},
        }

    async def save(self, entity: FinReport) -> FinReport:
        await self.save_batch([entity])
        return entity

    async def save_batch(self, entities: list[FinReport]) -> int:
        """按 (symbol, end_date, report_type) upsert，仅更新利润表列"""
        if not entities:
            return 0
        excluded = pg_insert(FinReportDB).excluded
        upsert_set = {c: getattr(excluded, c) for c in _INCOME_COLUMNS}
        upsert_set["updated_at"] = func.now()
        stmt = (
            pg_insert(FinReportDB)
            .values([self._to_row(e) for e in entities])
            .on_conflict_do_update(constraint="uq_fin_reports_uk", set_=upsert_set)
        )
        await self._session.execute(stmt)
        await self._session.commit()
        return len(entities)

    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[FinReport]:
        stmt = select(FinReportDB).where(FinReportDB.symbol == symbol)
        if start_date:
            stmt = stmt.where(FinReportDB.end_date >= start_date)
        if end_date:
            stmt = stmt.where(FinReportDB.end_date <= end_date)
        stmt = stmt.order_by(FinReportDB.end_date.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]

    async def list_symbols_with_reports(self) -> set[str]:
        """已有财报的股票（only_missing 断点续采用）"""
        rows = await self._session.execute(select(distinct(FinReportDB.symbol)))
        return {r[0] for r in rows.all()}


FinReportRepoImpl.__implements_protocol__ = FinReportRepository
