"""FinReportRepository：财务报表仓储

模式：upsert（UK = symbol + end_date + report_type）
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.bo import FinReportBO
from contexts.market.infrastructure.persistence.models.fin_report import (
    FinReportDB,
)

logger = logging.getLogger(__name__)


class FinReportRepository:
    """财务报表仓储（实现 domain Protocol）"""

    async def save(self, bos: list[FinReportBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(FinReportDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in FinReportDB.__table__.columns
            if c.name not in (
                "id", "created_at", "updated_at",
                "symbol", "end_date", "report_type",
            )
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "end_date", "report_type"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: FinReportBO) -> dict:
        return {
            "symbol": b.symbol,
            "end_date": b.end_date,
            "ann_date": b.ann_date,
            "report_type": b.report_type,
            "comp_type": b.comp_type,
            "end_type": b.end_type,
            "basic_eps": b.basic_eps,
            "diluted_eps": b.diluted_eps,
            "total_revenue": b.total_revenue,
            "revenue": b.revenue,
            "operate_profit": b.operate_profit,
            "total_profit": b.total_profit,
            "n_income": b.n_income,
            "n_income_attr_p": b.n_income_attr_p,
        }


__all__ = ["FinReportRepository"]
