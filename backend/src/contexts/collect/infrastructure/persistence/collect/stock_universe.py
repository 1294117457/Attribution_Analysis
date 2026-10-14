"""股票范围与日 K 覆盖（采集专用只读查询）

自开 session、自 commit；不复用 StockInfoRepository（它是 session 绑定的）。

配套设计文档：docs/backend-docs/dev/step5/03collect优化/02-端口与基础设施实现.md §3.2
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import func, select

from contexts.collect.application.port.collect_port import StockUniversePort
from contexts.shared.infrastructure.persistence.connection import AsyncSessionLocal
from contexts.market.infrastructure.persistence.models.stock_info import StockInfoDB
from contexts.market.infrastructure.persistence.models.tech_kline import TechKlineDailyDB


class SqlStockUniverse(StockUniversePort):
    """股票范围与日 K 覆盖"""

    async def list_symbols(
        self, list_status: str = "L", exchanges: list[str] | None = None,
    ) -> list[str]:
        async with AsyncSessionLocal() as session:
            stmt = select(StockInfoDB.symbol).where(StockInfoDB.list_status == list_status)
            if exchanges:
                stmt = stmt.where(StockInfoDB.exchange.in_(exchanges))
            stmt = stmt.order_by(StockInfoDB.symbol)
            return [r[0] for r in (await session.execute(stmt)).all()]

    async def list_dates(self, symbols: list[str]) -> dict[str, Optional[date]]:
        if not symbols:
            return {}
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(StockInfoDB.symbol, StockInfoDB.list_date)
                .where(StockInfoDB.symbol.in_(symbols))
            )
            return {r[0]: r[1] for r in rows.all()}

    async def kline_coverage(self, symbols: list[str]) -> dict[str, tuple[date, date]]:
        if not symbols:
            return {}
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(
                    TechKlineDailyDB.symbol,
                    func.min(TechKlineDailyDB.date),
                    func.max(TechKlineDailyDB.date),
                )
                .where(TechKlineDailyDB.symbol.in_(symbols))
                .group_by(TechKlineDailyDB.symbol)
            )
            return {r[0]: (r[1], r[2]) for r in rows.all()}


__all__ = ["SqlStockUniverse"]
