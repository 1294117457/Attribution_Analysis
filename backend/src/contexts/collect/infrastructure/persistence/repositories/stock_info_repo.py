"""StockInfoRepository（step7 简化版）—— 替换原 market 上下文的 SqlStockInfoRepository

供 StockBasicService 使用。
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.market.infrastructure.persistence.models.stock_info import StockInfoDB

logger = logging.getLogger(__name__)


class StockInfoRepository:
    """股票基本信息仓储（直接 upsert）"""

    async def save_batch(self, rows: list[dict]) -> int:
        """批量 upsert；返回受影响行数

        rows 每条 dict 必须含 symbol，其它字段可选

        容错：tushare 返回的字段可能逐行不一致（act_ent_type / act_name
        在某些行没有），SQLAlchemy 编译批量 INSERT 时按列取并集，
        会渲染所有列的占位符。我们把每行都补齐全表列（缺则 None），
        让 PostgreSQL 接收 NULL（这些列都是 nullable=True）。
        """
        if not rows:
            return 0
        # 表的所有可写列（id 由序列生成，created_at/updated_at 由 server_default）
        all_cols = [
            c.name for c in StockInfoDB.__table__.columns
            if c.name not in ("id", "created_at", "updated_at")
        ]
        clean = []
        for r in rows:
            if "symbol" not in r or r["symbol"] is None:
                continue
            row = {col: r.get(col) for col in all_cols}
            # symbol 必填
            row["symbol"] = str(row["symbol"]).zfill(6)
            clean.append(row)
        if not clean:
            return 0
        async with db_session_factory() as session:
            stmt = pg_insert(StockInfoDB).values(clean)
            # symbol 冲突时全列更新（None 仍会覆盖旧值，符合 upsert 语义）
            update_cols = {c.name: stmt.excluded[c.name] for c in StockInfoDB.__table__.columns
                           if c.name not in ("id", "symbol", "created_at", "updated_at")}
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol"],
                set_=update_cols,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount or len(clean)

    async def find(self, symbol: str) -> dict | None:
        async with db_session_factory() as session:
            row = await session.get(StockInfoDB, symbol)
            if row is None:
                return None
            return self._to_dict(row)

    async def list_symbols(self, list_status: str = "L") -> list[str]:
        async with db_session_factory() as session:
            rows = (await session.execute(
                select(StockInfoDB.symbol)
                .where(StockInfoDB.list_status == list_status)
                .order_by(StockInfoDB.symbol)
            )).all()
            return [r[0] for r in rows]

    async def list_dates(
        self, symbols: Iterable[str],
    ) -> dict[str, date | None]:
        symbols = list(symbols)
        if not symbols:
            return {}
        async with db_session_factory() as session:
            rows = (await session.execute(
                select(StockInfoDB.symbol, StockInfoDB.list_date)
                .where(StockInfoDB.symbol.in_(symbols))
            )).all()
            return {r[0]: r[1] for r in rows}

    @staticmethod
    def _to_dict(r) -> dict:
        return {
            "symbol": r.symbol,
            "ts_code": r.ts_code,
            "name": r.name,
            "area": r.area,
            "industry": r.industry,
            "market": r.market,
            "exchange": r.exchange,
            "list_date": r.list_date.isoformat() if r.list_date else None,
            "delist_date": r.delist_date.isoformat() if r.delist_date else None,
            "list_status": r.list_status,
            "is_hs": r.is_hs,
            "total_shares": r.total_shares,
            "act_name": r.act_name,
            "act_ent_type": r.act_ent_type,
        }


__all__ = ["StockInfoRepository"]
