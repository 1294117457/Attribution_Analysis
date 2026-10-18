"""K线仓储实现（仅 OHLCV）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.market.domain.entities.kline.entity import Kline
from contexts.market.domain.entities.kline.repository import KlineRepository
from contexts.market.domain.entities.kline.vo import StockCode
from contexts.market.infrastructure.persistence.models.tech_kline import TechKlineDailyDB



class KlineRepoImpl:
    """K线仓储实现

    实现 domain/kline/repository.py 中的 KlineRepository 接口。
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── ORM ↔ Entity 转换 ───────────────────────────────────

    def _to_entity(self, row: TechKlineDailyDB) -> Kline:
        """ORM 行 → 领域实体"""
        return Kline.create(
            id=row.id,
            symbol=row.symbol,
            name=row.name or "",
            trade_date=row.date,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
            amount=row.amount,
            change_pct=row.change_pct,
        )

    @staticmethod
    def _to_row(kline: Kline) -> dict:
        """领域实体 → ORM 行字典"""
        return {
            "symbol": kline.symbol.code,
            "name": kline.name,
            "date": kline.trade_date.date,
            "open": kline.open,
            "high": kline.high,
            "low": kline.low,
            "close": kline.close,
            "volume": kline.volume,
            "amount": kline.amount,
            "change_pct": kline.change_pct,
        }

    # ── KlineRepository 接口实现 ─────────────────────────────

    async def save(self, kline: Kline) -> Kline:
        row = TechKlineDailyDB(**self._to_row(kline))
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        kline.id = row.id
        return kline

    async def save_batch(self, klines: list[Kline]) -> int:
        """批量保存 K 线，使用 ON CONFLICT DO UPDATE。"""
        if not klines:
            return 0
        rows = [self._to_row(k) for k in klines]

        excluded = pg_insert(TechKlineDailyDB).excluded
        upsert_set = {
            "name": excluded.name,
            "open": excluded.open,
            "high": excluded.high,
            "low":  excluded.low,
            "close": excluded.close,
            "volume": excluded.volume,
            "amount": excluded.amount,
            "change_pct": excluded.change_pct,
        }

        stmt = (
            pg_insert(TechKlineDailyDB)
            .values(rows)
            .on_conflict_do_update(
                constraint="uq_tech_kline_symbol_date",
                set_=upsert_set,
            )
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount

    async def find_by_id(self, id: int) -> Optional[Kline]:
        stmt = select(TechKlineDailyDB).where(TechKlineDailyDB.id == id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def find_by_symbol_date(
        self, symbol: StockCode, trade_date: date
    ) -> Optional[Kline]:
        stmt = select(TechKlineDailyDB).where(
            TechKlineDailyDB.symbol == symbol.code,
            TechKlineDailyDB.date == trade_date,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def find_by_symbol(
        self,
        symbol: StockCode,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365,
        order_desc: bool = True,
    ) -> list[Kline]:
        stmt = select(TechKlineDailyDB).where(TechKlineDailyDB.symbol == symbol.code)

        if start_date:
            stmt = stmt.where(TechKlineDailyDB.date >= start_date)
        if end_date:
            stmt = stmt.where(TechKlineDailyDB.date <= end_date)

        order_col = TechKlineDailyDB.date.desc() if order_desc else TechKlineDailyDB.date.asc()
        stmt = stmt.order_by(order_col).limit(limit)

        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    async def count_by_symbol(self, symbol: StockCode) -> int:
        stmt = select(func.count()).where(TechKlineDailyDB.symbol == symbol.code)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete_by_symbol(self, symbol: StockCode) -> int:
        stmt = delete(TechKlineDailyDB).where(TechKlineDailyDB.symbol == symbol.code)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount

    async def delete_one(self, symbol: StockCode, trade_date: date) -> int:
        stmt = delete(TechKlineDailyDB).where(
            TechKlineDailyDB.symbol == symbol.code,
            TechKlineDailyDB.date == trade_date,
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount


# 标注实现关系（便于 IDE 提示）
KlineRepoImpl.__implements_protocol__ = KlineRepository
