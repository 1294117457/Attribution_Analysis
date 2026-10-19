"""ConceptSnapshotRepository：概念行情快照仓储

模式：每行有时间戳 captured_at，每次写入新一行（不更新，append 历史）。
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.concept.application.bo.concept import ConceptSnapshotBO
from contexts.concept.infrastructure.persistence.models.concept import ConceptSnapshotDB

logger = logging.getLogger(__name__)


class ConceptSnapshotRepository:
    """概念行情快照仓储（实现 domain Protocol）

    行情时序数据：每次采集写入新一行（保留历史），
    应用层取最新 1 行：ORDER BY captured_at DESC LIMIT 1。
    """

    async def save(self, bos: list[ConceptSnapshotBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        now = datetime.now()
        rows = [self._to_row(b, now) for b in bos]
        stmt = pg_insert(ConceptSnapshotDB).values(rows)
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: ConceptSnapshotBO, now: datetime) -> dict:
        return {
            "index_code": b.index_code,
            "concept_name": b.concept_name or b.index_code,
            "trade_date": b.trade_date,
            "trade_time": None,
            "open_price": b.open_price,
            "high": b.high,
            "low": b.low,
            "price": b.price,
            "prev_close": b.prev_close,
            "p_change": b.p_change,
            "pct_change": b.pct_change,
            "source": "ths",
            "captured_at": now,
        }


__all__ = ["ConceptSnapshotRepository"]
