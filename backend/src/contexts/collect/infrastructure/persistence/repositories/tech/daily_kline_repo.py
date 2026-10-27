"""DailyKlineRepository：日 K 线持久化（表 tech_daily @ raw_data_db）

session 由 service 层持有并以参数传入：本 repo 不开 session、不 commit、
不 rollback，事务边界与重试粒度由 service 决定。
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.market.application.bo.kline import KlineBO
from contexts.market.infrastructure.persistence.models.tech_kline import (
    TechKlineDailyDB,
)

logger = logging.getLogger(__name__)

# asyncpg 单条语句最多 32767 个绑定参数（PostgreSQL 协议上限 65535）。
# tech_daily 每行 10 列 → 1000 行 = 10000 个参数，留足余量。
# 全市场单日约 5500+ 行，一次性展开成一条 INSERT 会直接超限报错。
BATCH_SIZE = 1000

# ON CONFLICT DO UPDATE 只更新业务列，不动主键 / UK / 时间戳
_UPSERT_EXCLUDE_COLUMNS = ("id", "symbol", "date", "created_at", "updated_at")


class DailyKlineRepository:
    """日 K 线仓储（tech_daily upsert + 查询）"""

    async def save_klines(
        self, klines: list[KlineBO], session: AsyncSession,
    ) -> int:
        """批量 upsert（UK = symbol + date），返回受影响行数

        分批执行：每批 BATCH_SIZE 行，避免绑定参数超过 asyncpg 上限。
        """
        if not klines:
            return 0
        rows = [self._to_row(k) for k in klines]

        update_columns = [
            c.name for c in TechKlineDailyDB.__table__.columns
            if c.name not in _UPSERT_EXCLUDE_COLUMNS
        ]

        total = 0
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i: i + BATCH_SIZE]
            stmt = pg_insert(TechKlineDailyDB).values(batch)
            # stmt.excluded 必须绑定在当前批次的 stmt 上，不能跨批复用
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "date"],
                set_={c: stmt.excluded[c] for c in update_columns},
            )
            result = await session.execute(stmt)
            total += result.rowcount or len(batch)
        return total

    async def find_by_symbol(
        self,
        symbol: str,
        session: AsyncSession,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 30,
        order_desc: bool = True,
    ) -> list[dict]:
        """按 symbol + 日期区间查日 K（symbol 传空串 = 不按代码过滤）"""
        stmt = select(TechKlineDailyDB)
        if symbol:
            stmt = stmt.where(TechKlineDailyDB.symbol == str(symbol).zfill(6))
        if start_date:
            stmt = stmt.where(TechKlineDailyDB.date >= start_date)
        if end_date:
            stmt = stmt.where(TechKlineDailyDB.date <= end_date)
        stmt = stmt.order_by(
            TechKlineDailyDB.date.desc() if order_desc else TechKlineDailyDB.date
        )
        if limit:
            stmt = stmt.limit(limit)
        rows = (await session.execute(stmt)).scalars().all()
        return [self._to_dict(r) for r in rows]

    @staticmethod
    def _to_row(k: KlineBO) -> dict:
        """KlineBO → tech_daily 行（ORM 列名是 date，BO 里是 trade_date）"""
        return {
            "symbol": k.symbol,
            "name": k.name or "",
            "date": k.trade_date,
            "open": float(k.open),
            "high": float(k.high),
            "low": float(k.low),
            "close": float(k.close),
            "volume": int(k.volume),
            "amount": float(k.amount or 0.0),
            "change_pct": (
                float(k.change_pct) if k.change_pct is not None else None
            ),
        }

    @staticmethod
    def _to_dict(r: TechKlineDailyDB) -> dict:
        """tech_daily 行 → dict（对外暴露 trade_date，与 BO 对齐）"""
        return {
            "symbol": r.symbol,
            "trade_date": r.date.isoformat() if r.date else None,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume,
            "amount": r.amount,
        }


__all__ = ["DailyKlineRepository"]