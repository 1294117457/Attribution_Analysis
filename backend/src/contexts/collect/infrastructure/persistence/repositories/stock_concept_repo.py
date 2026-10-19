"""StockConceptRepository：股票所属概念仓储

模式：upsert（UK = symbol + concept_id）
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.infrastructure.persistence.models.fundamental_stock_concept import (
    FundamentalStockConceptDB,
)

logger = logging.getLogger(__name__)


class StockConceptRepository:
    """股票所属概念仓储（实现 domain Protocol）

    BO 是 adata 返回的 list[dict]，需要先找 concept_id（由 name 查 ConceptsDB）。
    """

    async def upsert_by_concept_map(
        self,
        rows: list[dict],
        concept_id_map: dict[str, int],
        session: AsyncSession,
    ) -> int:
        """rows 每条含 symbol/index_code/name/source/reason

        需通过 name → concept_id 查 concept 表的映射。
        """
        if not rows:
            return 0
        now = datetime.now()
        mapped: list[dict] = []
        for r in rows:
            cid = concept_id_map.get(r["name"])
            if cid is None:
                continue
            mapped.append({
                "symbol": str(r["symbol"]).zfill(6),
                "concept_id": cid,
                "name": r.get("name"),
                "source": r.get("source", "ths"),
                "reason": r.get("reason"),
                "synced_at": now,
            })
        if not mapped:
            return 0
        stmt = pg_insert(FundamentalStockConceptDB).values(mapped)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in FundamentalStockConceptDB.__table__.columns
            if c.name not in (
                "id", "created_at", "updated_at", "symbol", "concept_id",
            )
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "concept_id"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(mapped)


__all__ = ["StockConceptRepository"]
