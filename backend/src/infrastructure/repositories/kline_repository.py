"""K线仓储实现（含 17 个技术指标字段）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.kline.entity import Kline
from domain.kline.repository import KlineRepository
from domain.kline.value_objects import StockCode
from infrastructure.database.models.tech_kline import TechKlineDailyDB


# 一行 = 一只股票一天的所有 K 线 + 指标字段（方案 A 展宽结构）
_INDICATOR_COLUMNS = [
    "ma5", "ma10", "ma20", "ma60",
    "ema12", "ema26",
    "macd_dif", "macd_dea", "macd_bar",
    "rsi6", "rsi12", "rsi24",
    "kdj_k", "kdj_d", "kdj_j",
    "boll_up", "boll_mid", "boll_dn",
]


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
            ma5=row.ma5,
            ma10=row.ma10,
            ma20=row.ma20,
            ma60=row.ma60,
            ema12=row.ema12,
            ema26=row.ema26,
            macd_dif=row.macd_dif,
            macd_dea=row.macd_dea,
            macd_bar=row.macd_bar,
            rsi6=row.rsi6,
            rsi12=row.rsi12,
            rsi24=row.rsi24,
            kdj_k=row.kdj_k,
            kdj_d=row.kdj_d,
            kdj_j=row.kdj_j,
            boll_up=row.boll_up,
            boll_mid=row.boll_mid,
            boll_dn=row.boll_dn,
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
            "ma5":  kline.ma5,
            "ma10": kline.ma10,
            "ma20": kline.ma20,
            "ma60": kline.ma60,
            "ema12": kline.ema12,
            "ema26": kline.ema26,
            "macd_dif": kline.macd_dif,
            "macd_dea": kline.macd_dea,
            "macd_bar": kline.macd_bar,
            "rsi6":  kline.rsi6,
            "rsi12": kline.rsi12,
            "rsi24": kline.rsi24,
            "kdj_k": kline.kdj_k,
            "kdj_d": kline.kdj_d,
            "kdj_j": kline.kdj_j,
            "boll_up":  kline.boll_up,
            "boll_mid": kline.boll_mid,
            "boll_dn":  kline.boll_dn,
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
        """批量保存 K 线 + 指标，使用 ON CONFLICT DO UPDATE。"""
        if not klines:
            return 0
        rows = [self._to_row(k) for k in klines]

        # DO UPDATE 全部字段（含指标），保证重复采集时指标被覆盖
        excluded = pg_insert(TechKlineDailyDB).excluded
        upsert_set = {col: getattr(excluded, col) for col in _INDICATOR_COLUMNS}
        upsert_set.update({
            "name": excluded.name,
            "open": excluded.open,
            "high": excluded.high,
            "low":  excluded.low,
            "close": excluded.close,
            "volume": excluded.volume,
            "amount": excluded.amount,
            "change_pct": excluded.change_pct,
        })

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
