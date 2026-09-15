"""股票信息仓储实现"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.stock_info.entity import StockInfo
from domain.stock_info.repository import StockInfoRepository
from infrastructure.database.models.stock_info import StockInfoDB
from infrastructure.database.models.kline import DailyKlineDB


class StockRepoImpl:
    """股票信息仓储实现

    实现 domain/stock_info/repository.py 中的 StockInfoRepository 接口。
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_entity(self, row: StockInfoDB) -> StockInfo:
        """ORM → Entity"""
        return StockInfo.create(
            id=row.id,
            symbol=row.symbol,
            name=row.name or "",
            industry=row.industry,
            market=row.market,
            list_date=row.list_date,
            total_shares=row.total_shares,
        )

    @staticmethod
    def _to_row(stock: StockInfo) -> dict:
        """Entity → ORM"""
        return {
            "symbol": stock.symbol,
            "name": stock.name,
            "industry": stock.industry.name if stock.industry else None,
            "market": stock.market.code if stock.market else None,
            "list_date": stock.list_date,
            "total_shares": stock.total_shares,
        }

    async def save(self, stock: StockInfo) -> StockInfo:
        row = StockInfoDB(**self._to_row(stock))
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        stock.id = row.id
        return stock

    async def find_by_symbol(self, symbol: str) -> Optional[StockInfo]:
        stmt = select(StockInfoDB).where(StockInfoDB.symbol == symbol)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def find_all(
        self,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> list[StockInfo]:
        stmt = select(StockInfoDB)
        if industry:
            stmt = stmt.where(StockInfoDB.industry == industry)
        if market:
            stmt = stmt.where(StockInfoDB.market == market)
        stmt = stmt.order_by(StockInfoDB.symbol)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    async def upsert(self, stock: StockInfo) -> StockInfo:
        row_dict = self._to_row(stock)
        stmt = (
            pg_insert(StockInfoDB)
            .values(**row_dict)
            .on_conflict_do_update(
                index_elements=["symbol"],
                set_=row_dict,
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        return stock

    async def delete(self, symbol: str) -> bool:
        stmt = select(StockInfoDB).where(StockInfoDB.symbol == symbol)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row:
            await self._session.delete(row)
            await self._session.commit()
            return True
        return False

    async def list_with_kline_stats(
        self,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> list[dict]:
        stmt = (
            select(
                StockInfoDB.symbol,
                StockInfoDB.name,
                StockInfoDB.industry,
                StockInfoDB.market,
                func.count(DailyKlineDB.id).label("record_count"),
                func.min(DailyKlineDB.date).label("kline_start"),
                func.max(DailyKlineDB.date).label("kline_end"),
            )
            .outerjoin(DailyKlineDB, StockInfoDB.symbol == DailyKlineDB.symbol)
            .group_by(StockInfoDB.id)
            .order_by(StockInfoDB.symbol)
        )
        if industry:
            stmt = stmt.where(StockInfoDB.industry == industry)
        if market:
            stmt = stmt.where(StockInfoDB.market == market)

        result = await self._session.execute(stmt)
        rows = result.all()
        return [
            {
                "symbol": r.symbol,
                "name": r.name,
                "industry": r.industry,
                "market": r.market,
                "record_count": r.record_count,
                "kline_start": r.kline_start,
                "kline_end": r.kline_end,
            }
            for r in rows
        ]


StockRepoImpl.__implements_protocol__ = StockInfoRepository
