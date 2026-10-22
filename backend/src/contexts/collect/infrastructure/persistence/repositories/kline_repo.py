"""KlineRepository：日 K 线持久化（step7 service 直接调用）

替代原 stock_info_service.collect() 内部走的 _kline_repo.save_batch。
DailyService 直接调本类的 save_klines() / find() / get_coverage()。
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Iterable

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.market.domain.entities.kline.entity import Kline
from contexts.market.infrastructure.persistence.models.tech_kline import TechKlineDailyDB

logger = logging.getLogger(__name__)


class KlineRepository:
    """日 K 线仓储（直接 ORM upsert，不再走 KlineEntity 中转）

    所有方法接受 session: AsyncSession 入参（由 service 工厂注入或 Depends 入口），
    不再自己 async with db_session_factory()。
    """

    async def save_klines(self, klines: list[Kline], session: AsyncSession) -> int:
        """批量 upsert；返回受影响行数"""
        if not klines:
            return 0
        rows = [self._to_row(k) for k in klines]
        stmt = pg_insert(TechKlineDailyDB).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "date"],
            set_={
                "name": stmt.excluded.name,
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "amount": stmt.excluded.amount,
                "change_pct": stmt.excluded.change_pct,
            },
        )
        result = await session.execute(stmt)
        return result.rowcount or len(rows)

    async def find(
        self, symbol: str, start: date | None, end: date | None,
        session: AsyncSession,
    ) -> list[Kline]:
        stmt = select(TechKlineDailyDB).where(TechKlineDailyDB.symbol == symbol)
        if start:
            stmt = stmt.where(TechKlineDailyDB.date >= start)
        if end:
            stmt = stmt.where(TechKlineDailyDB.date <= end)
        stmt = stmt.order_by(TechKlineDailyDB.date)
        rows = (await session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]

    async def find_by_symbol(
        self, symbol, session: AsyncSession, start_date=None, end_date=None,
        limit: int = 1000, order_desc: bool = False,
    ) -> list[Kline]:
        """兼容 stock_info_service 旧 API"""
        from sqlalchemy import desc
        stmt = select(TechKlineDailyDB).where(TechKlineDailyDB.symbol == str(symbol))
        if start_date:
            stmt = stmt.where(TechKlineDailyDB.date >= start_date)
        if end_date:
            stmt = stmt.where(TechKlineDailyDB.date <= end_date)
        stmt = stmt.order_by(desc(TechKlineDailyDB.date) if order_desc else TechKlineDailyDB.date)
        if limit:
            stmt = stmt.limit(limit)
        rows = (await session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]

    async def count_by_symbol(self, symbol, session: AsyncSession) -> int:
        r = await session.execute(
            select(func.count()).select_from(TechKlineDailyDB)
            .where(TechKlineDailyDB.symbol == str(symbol))
        )
        return r.scalar() or 0

    async def delete_one(
        self, symbol, trade_date, session: AsyncSession,
    ) -> int:
        r = await session.execute(
            delete(TechKlineDailyDB).where(
                TechKlineDailyDB.symbol == str(symbol),
                TechKlineDailyDB.date == trade_date,
            )
        )
        return r.rowcount or 0

    async def delete_by_symbol(self, symbol, session: AsyncSession) -> int:
        return await self.delete(str(symbol), session)

    async def get_coverage(
        self, symbols: Iterable[str], session: AsyncSession,
    ) -> dict[str, tuple[date, date]]:
        symbols = list(symbols)
        if not symbols:
            return {}
        rows = (await session.execute(
            select(
                TechKlineDailyDB.symbol,
                func.min(TechKlineDailyDB.date),
                func.max(TechKlineDailyDB.date),
            )
            .where(TechKlineDailyDB.symbol.in_(symbols))
            .group_by(TechKlineDailyDB.symbol)
        )).all()
        return {r[0]: (r[1], r[2]) for r in rows if r[1] and r[2]}

    async def list_symbol_dates(
        self, symbols: Iterable[str], session: AsyncSession,
    ) -> dict[str, date | None]:
        """每只股票的上市日（从 stock_info 拿）"""
        from contexts.market.infrastructure.persistence.models.stock_basic import StockBasicDB
        symbols = list(symbols)
        if not symbols:
            return {}
        rows = (await session.execute(
            select(StockBasicDB.symbol, StockBasicDB.list_date)
            .where(StockBasicDB.symbol.in_(symbols))
        )).all()
        return {r[0]: r[1] for r in rows}

    async def list_symbols(
        self, session: AsyncSession, list_status: str = "L",
    ) -> list[str]:
        from contexts.market.infrastructure.persistence.models.stock_basic import StockBasicDB
        rows = (await session.execute(
            select(StockBasicDB.symbol)
            .where(StockBasicDB.list_status == list_status)
            .order_by(StockBasicDB.symbol)
        )).all()
        return [r[0] for r in rows]

    async def delete(self, symbol: str, session: AsyncSession) -> int:
        result = await session.execute(
            delete(TechKlineDailyDB).where(TechKlineDailyDB.symbol == symbol)
        )
        return result.rowcount or 0

    # ── 私有 ──

    @staticmethod
    def _to_row(k: Kline) -> dict:
        return {
            "symbol": k.symbol.code if hasattr(k.symbol, "code") else str(k.symbol),
            "name": k.name or "",
            "date": k.trade_date.date if hasattr(k.trade_date, "date") else k.trade_date,
            "open": float(k.open),
            "high": float(k.high),
            "low": float(k.low),
            "close": float(k.close),
            "volume": int(k.volume),
            "amount": float(k.amount or 0.0),
            "change_pct": float(k.change_pct) if k.change_pct is not None else None,
        }

    @staticmethod
    def _to_entity(r) -> Kline:
        return Kline(
            id=r.id,
            symbol=r.symbol,
            trade_date=r.date,
            name=r.name or "",
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            volume=r.volume,
            amount=r.amount,
            change_pct=r.change_pct,
        )


__all__ = ["KlineRepository"]
