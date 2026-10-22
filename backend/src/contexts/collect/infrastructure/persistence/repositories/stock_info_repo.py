"""StockInfoRepository（step7 简化版）—— 替换原 market 上下文的 SqlStockInfoRepository

供 StockBasicService 使用。
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.market.infrastructure.persistence.models.stock_basic import StockBasicDB

logger = logging.getLogger(__name__)


class StockInfoRepository:
    """股票基本信息仓储（直接 upsert / replace_all）

    所有方法接受 session: AsyncSession 入参（由 service 工厂注入或 Depends 入口），
    不再自己 async with db_session_factory()。
    """

    async def save_batch(self, rows: list[dict], session: AsyncSession) -> int:
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
            c.name for c in StockBasicDB.__table__.columns
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
        stmt = pg_insert(StockBasicDB).values(clean)
        # symbol 冲突时全列更新（None 仍会覆盖旧值，符合 upsert 语义）
        update_cols = {c.name: stmt.excluded[c.name] for c in StockBasicDB.__table__.columns
                       if c.name not in ("id", "symbol", "created_at", "updated_at")}
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol"],
            set_=update_cols,
        )
        result = await session.execute(stmt)
        return result.rowcount or len(clean)

    async def replace_all(
        self,
        rows: list[dict],
        list_status: str,
        session: AsyncSession,
    ) -> int:
        """FULL_REFRESH：同 list_status 子集整体覆盖（事务内 DELETE + INSERT）

        语义：清空 list_status=? 的所有行，INSERT 新行。
        典型用途：stock_basic 每次"全市场最新"覆盖。

        注意：
          - 只覆盖传入的 list_status 子集，不动其他子集
            （如传 L 时 D / P 不动）
          - 入参 rows 缺字段按 None 补齐（与 save_batch 一致）
          - symbol 必填，无效行跳过
          - 事务由调用方管理（service 层 session 已在事务中）

        Returns:
            实际写入行数
        """
        # 1. DELETE 旧子集
        await session.execute(
            delete(StockBasicDB).where(StockBasicDB.list_status == list_status)
        )

        if not rows:
            logger.info(
                "[replace_all] list_status=%s, 0 rows → DELETE 0 行（无 INSERT）",
                list_status,
            )
            return 0

        # 2. 补齐列（缺则 None）
        all_cols = [
            c.name for c in StockBasicDB.__table__.columns
            if c.name not in ("id", "created_at", "updated_at")
        ]
        clean: list[dict] = []
        for r in rows:
            if "symbol" not in r or r["symbol"] is None:
                continue
            row = {col: r.get(col) for col in all_cols}
            row["symbol"] = str(row["symbol"]).zfill(6)
            # list_status 强制对齐（防止 BO 里写错）
            row["list_status"] = list_status
            clean.append(row)

        if not clean:
            return 0

        # 3. INSERT 新子集（bulk_insert_mappings 走 executemany，高效）
        await session.execute(StockBasicDB.__table__.insert(), clean)

        logger.info(
            "[replace_all] list_status=%s, 写入 %d 行",
            list_status, len(clean),
        )
        return len(clean)

    async def find(self, symbol: str, session: AsyncSession) -> dict | None:
        row = await session.get(StockBasicDB, symbol)
        if row is None:
            return None
        return self._to_dict(row)

    async def list_symbols(
        self, session: AsyncSession, list_status: str = "L",
    ) -> list[str]:
        rows = (await session.execute(
            select(StockBasicDB.symbol)
            .where(StockBasicDB.list_status == list_status)
            .order_by(StockBasicDB.symbol)
        )).all()
        return [r[0] for r in rows]

    async def list_dates(
        self, symbols: Iterable[str], session: AsyncSession,
    ) -> dict[str, date | None]:
        symbols = list(symbols)
        if not symbols:
            return {}
        rows = (await session.execute(
            select(StockBasicDB.symbol, StockBasicDB.list_date)
            .where(StockBasicDB.symbol.in_(symbols))
        )).all()
        return {r[0]: r[1] for r in rows}

    @staticmethod
    def _to_dict(r) -> dict:
        return {
            "symbol": r.symbol,
            "ts_code": r.ts_code,
            "name": r.name,
            "fullname": getattr(r, "fullname", None),
            "enname": getattr(r, "enname", None),
            "cnspell": getattr(r, "cnspell", None),
            "area": r.area,
            "industry": r.industry,
            "market": r.market,
            "exchange": r.exchange,
            "list_date": r.list_date.isoformat() if r.list_date else None,
            "delist_date": r.delist_date.isoformat() if r.delist_date else None,
            "list_status": r.list_status,
            "is_hs": r.is_hs,
            "act_name": r.act_name,
            "act_ent_type": r.act_ent_type,
            "curr_type": getattr(r, "curr_type", None),
        }


__all__ = ["StockInfoRepository"]
