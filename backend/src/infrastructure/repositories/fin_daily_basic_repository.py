"""日频估值指标仓储实现"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.fin_daily_basic.entity import FinDailyBasic
from domain.fin_daily_basic.repository import FinDailyBasicRepository
from infrastructure.database.models.fin_daily_basic import FinDailyBasicDB


_VALUE_COLUMNS = [
    "close", "turnover_rate", "turnover_rate_f", "volume_ratio",
    "pe", "pe_ttm", "pb", "ps", "ps_ttm",
    "dv_ratio", "dv_ttm",
    "total_share", "float_share", "free_share",
    "total_mv", "circ_mv",
]


class FinDailyBasicRepoImpl:
    """日频估值指标仓储实现"""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_entity(self, row: FinDailyBasicDB) -> FinDailyBasic:
        return FinDailyBasic(
            symbol=row.symbol,
            trade_date=row.trade_date,
            close=row.close,
            turnover_rate=row.turnover_rate,
            turnover_rate_f=row.turnover_rate_f,
            volume_ratio=row.volume_ratio,
            pe=row.pe,
            pe_ttm=row.pe_ttm,
            pb=row.pb,
            ps=row.ps,
            ps_ttm=row.ps_ttm,
            dv_ratio=row.dv_ratio,
            dv_ttm=row.dv_ttm,
            total_share=row.total_share,
            float_share=row.float_share,
            free_share=row.free_share,
            total_mv=row.total_mv,
            circ_mv=row.circ_mv,
            data_source=row.data_source,
        )

    @staticmethod
    def _to_row(entity: FinDailyBasic) -> dict:
        return {
            "symbol": entity.symbol,
            "trade_date": entity.trade_date,
            "close": entity.close,
            "turnover_rate": entity.turnover_rate,
            "turnover_rate_f": entity.turnover_rate_f,
            "volume_ratio": entity.volume_ratio,
            "pe": entity.pe,
            "pe_ttm": entity.pe_ttm,
            "pb": entity.pb,
            "ps": entity.ps,
            "ps_ttm": entity.ps_ttm,
            "dv_ratio": entity.dv_ratio,
            "dv_ttm": entity.dv_ttm,
            "total_share": entity.total_share,
            "float_share": entity.float_share,
            "free_share": entity.free_share,
            "total_mv": entity.total_mv,
            "circ_mv": entity.circ_mv,
            "data_source": entity.data_source,
        }

    async def save(self, entity: FinDailyBasic) -> FinDailyBasic:
        row = FinDailyBasicDB(**self._to_row(entity))
        self._session.add(row)
        await self._session.flush()
        return entity

    async def save_batch(self, entities: list[FinDailyBasic]) -> int:
        """批量 upsert，ON CONFLICT (symbol, trade_date) DO UPDATE"""
        if not entities:
            return 0

        BATCH_SIZE = 500
        excluded = pg_insert(FinDailyBasicDB).excluded
        upsert_set = {col: getattr(excluded, col) for col in _VALUE_COLUMNS}

        total = 0
        for i in range(0, len(entities), BATCH_SIZE):
            batch = entities[i: i + BATCH_SIZE]
            rows = [self._to_row(e) for e in batch]
            stmt = (
                pg_insert(FinDailyBasicDB)
                .values(rows)
                .on_conflict_do_update(
                    constraint="uq_fin_daily_basics_uk",
                    set_=upsert_set,
                )
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
    ) -> list[FinDailyBasic]:
        stmt = select(FinDailyBasicDB).where(FinDailyBasicDB.symbol == symbol)
        if start_date:
            stmt = stmt.where(FinDailyBasicDB.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(FinDailyBasicDB.trade_date <= end_date)
        stmt = stmt.order_by(FinDailyBasicDB.trade_date.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def get_latest_date(self) -> Optional[date]:
        """获取表中最新的 trade_date"""
        stmt = select(func.max(FinDailyBasicDB.trade_date))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


FinDailyBasicRepoImpl.__implements_protocol__ = FinDailyBasicRepository
