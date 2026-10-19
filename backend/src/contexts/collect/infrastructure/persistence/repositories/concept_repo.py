"""ConceptRepository：概念清单仓储

模式：upsert（UK = index_code）

依赖注入：save/list_all_codes/get_id_by_name 都需要 session 入参（由 service 工厂注入）。
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.concept.application.bo.concept import ConceptListBO
from contexts.concept.infrastructure.persistence.models.concept import ConceptsDB

logger = logging.getLogger(__name__)


class ConceptRepository:
    """概念清单仓储（实现 domain Protocol）"""

    async def save(self, bos: list[ConceptListBO], session: AsyncSession) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        stmt = pg_insert(ConceptsDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in ConceptsDB.__table__.columns
            if c.name not in (
                "id", "first_seen_at",
                "index_code",
            )
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["index_code"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        return r.rowcount or len(rows)

    async def list_all_codes(self, session: AsyncSession) -> list[str]:
        """返回全部 index_code（service 全量模式用）"""
        rows = (await session.execute(
            select(ConceptsDB.index_code)
            .where(ConceptsDB.is_active.is_(True))
            .order_by(ConceptsDB.index_code)
        )).all()
        return [r[0] for r in rows if r[0]]

    async def get_id_by_name(self, name: str, session: AsyncSession) -> Optional[int]:
        """通过 name 查 id（stock_concepts repo 用）"""
        row = (await session.execute(
            select(ConceptsDB.id).where(ConceptsDB.name == name)
        )).first()
        return row[0] if row else None

    @staticmethod
    def _to_row(b: ConceptListBO) -> dict:
        return {
            "index_code": b.index_code,
            "concept_code": b.concept_code,
            "name": b.name,
            "source": "ths",
        }


__all__ = ["ConceptRepository"]
