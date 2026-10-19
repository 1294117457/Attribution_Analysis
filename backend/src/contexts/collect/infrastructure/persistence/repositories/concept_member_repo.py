"""ConceptMemberRepository：概念成分股仓储

模式：delete-by-concept_id-then-insert（按 concept_id 整批重写）

service 端拿到 BO 后，应先通过 ConceptRepository.get_id_by_name() 取 concept_id，
再调 save_by_concept(concept_id, bos) 写入。
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.concept.application.bo.concept import ConceptMemberBO
from contexts.concept.infrastructure.persistence.models.concept import ConceptMemberDB

logger = logging.getLogger(__name__)


class ConceptMemberRepository:
    """概念成分股仓储（实现 domain Protocol）"""

    async def save_by_concept(
        self, concept_id: int, bos: list[ConceptMemberBO], session: AsyncSession,
    ) -> int:
        if not bos:
            return 0
        now = datetime.now()
        rows = [
            {
                "symbol": b.symbol,
                "concept_id": concept_id,
                "short_name": b.short_name,
                "joined_at": now,
                "synced_at": now,
                "source": "ths",
            }
            for b in bos
        ]
        await session.execute(
            delete(ConceptMemberDB).where(ConceptMemberDB.concept_id == concept_id)
        )
        stmt = pg_insert(ConceptMemberDB).values(rows)
        r = await session.execute(stmt)
        return r.rowcount or len(rows)


__all__ = ["ConceptMemberRepository"]
