"""Concept 仓储实现

配套设计文档：
  docs/dev/06gainian/02-infrastructure-design.md §3
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.concept.entity import Concept, ConceptMember, ConceptSource
from domain.concept.repository import ConceptRepository
from domain.concept.value_objects import ConceptBriefVO, ConceptGroupedVO
from infrastructure.database.models.concept import ConceptsDB, ConceptMemberDB

logger = logging.getLogger(__name__)


def _src(val) -> str:
    """统一提取 source 字段的字符串值"""
    return val.value if hasattr(val, "value") else str(val)


def _ctype(val) -> str:
    """统一提取 concept_type 字段的字符串值"""
    return val.value if hasattr(val, "value") else str(val)


class ConceptRepoImpl:
    """概念仓储实现"""

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── ORM ↔ Entity 转换 ─────────────────────────────────

    def _to_entity(self, row: ConceptsDB) -> Concept:
        return Concept(
            id=row.id,
            name=row.name,
            source=ConceptSource(row.source),
            concept_type=row.concept_type,
            description=row.description,
            stock_count=row.stock_count,
            is_active=row.is_active,
            first_seen_at=row.first_seen_at,
            last_synced_at=row.last_synced_at,
        )

    def _to_brief_vo(
        self, concept_id: int, name: str, source: str
    ) -> ConceptBriefVO:
        return ConceptBriefVO(
            concept_id=concept_id,
            name=name,
            source=source,
        )

    # ── 写入 ─────────────────────────────────────────────

    async def upsert_concept(self, concept: Concept) -> Concept:
        row_dict = {
            "name": concept.name,
            "source": _src(concept.source),
            "concept_type": _ctype(concept.concept_type),
            "description": concept.description,
            "stock_count": concept.stock_count,
            "is_active": concept.is_active,
            "last_synced_at": concept.last_synced_at,
        }
        stmt = (
            pg_insert(ConceptsDB)
            .values(**row_dict)
            .on_conflict_do_update(
                index_elements=["name", "source"],
                set_={
                    **row_dict,
                    "is_active": True,  # 重新上线时激活
                },
            )
            .returning(ConceptsDB.id)
        )
        result = await self._session.execute(stmt)
        concept.id = result.scalar_one()
        await self._session.commit()
        return concept

    async def upsert_members(
        self,
        concept_id: int,
        members: list[ConceptMember],
    ) -> int:
        """全量覆盖语义：DELETE + INSERT"""
        # 1. DELETE 旧成员
        await self._session.execute(
            delete(ConceptMemberDB).where(
                ConceptMemberDB.concept_id == concept_id
            )
        )
        # 2. INSERT 新成员
        if not members:
            await self._session.commit()
            return 0

        rows = [
            {
                "symbol": m.symbol,
                "concept_id": concept_id,
                "joined_at": m.joined_at,
                "source": _src(m.source),
            }
            for m in members
        ]
        self._session.add_all([ConceptMemberDB(**r) for r in rows])
        await self._session.commit()
        return len(rows)

    # ── 单条读取 ────────────────────────────────────────

    async def get_concept_by_id(self, concept_id: int) -> Optional[Concept]:
        stmt = select(ConceptsDB).where(ConceptsDB.id == concept_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def get_concept_by_name(
        self, name: str, source: str = "em"
    ) -> Optional[Concept]:
        stmt = select(ConceptsDB).where(
            and_(
                ConceptsDB.name == name,
                ConceptsDB.source == source,
            )
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(row) if row else None

    # ── 反向查询 ────────────────────────────────────────

    async def list_concepts_by_symbol(
        self, symbol: str
    ) -> list[ConceptBriefVO]:
        stmt = (
            select(
                ConceptsDB.id,
                ConceptsDB.name,
                ConceptsDB.source,
            )
            .join(ConceptMemberDB, ConceptMemberDB.concept_id == ConceptsDB.id)
            .where(
                and_(
                    ConceptMemberDB.symbol == symbol,
                    ConceptsDB.is_active == True,
                )
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [self._to_brief_vo(r.id, r.name, r.source) for r in rows]

    async def list_concepts_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[ConceptBriefVO]]:
        if not symbols:
            return {}

        stmt = (
            select(
                ConceptMemberDB.symbol,
                ConceptsDB.id,
                ConceptsDB.name,
                ConceptsDB.source,
            )
            .join(ConceptsDB, ConceptMemberDB.concept_id == ConceptsDB.id)
            .where(
                and_(
                    ConceptMemberDB.symbol.in_(symbols),
                    ConceptsDB.is_active == True,
                )
            )
        )
        rows = (await self._session.execute(stmt)).all()

        out: dict[str, list[ConceptBriefVO]] = {s: [] for s in symbols}
        for r in rows:
            out[r.symbol].append(self._to_brief_vo(r.id, r.name, r.source))
        return out

    async def list_concepts_by_symbol_grouped(
        self, symbol: str
    ) -> list[ConceptGroupedVO]:
        """单股票所属概念（含 concept_type / description，用于详情抽屉「概念」Tab）"""
        stmt = (
            select(
                ConceptsDB.id,
                ConceptsDB.name,
                ConceptsDB.source,
                ConceptsDB.concept_type,
                ConceptsDB.description,
            )
            .join(ConceptMemberDB, ConceptMemberDB.concept_id == ConceptsDB.id)
            .where(
                and_(
                    ConceptMemberDB.symbol == symbol,
                    ConceptsDB.is_active == True,
                )
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            ConceptGroupedVO(
                concept_id=r.id,
                name=r.name,
                source=r.source,
                concept_type=r.concept_type,
                description=r.description,
            )
            for r in rows
        ]

    # ── 列表 / 统计 ───────────────────────────────────

    async def list_concepts(
        self,
        q: Optional[str] = None,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Concept], int]:
        stmt = select(ConceptsDB)
        count_stmt = select(func.count()).select_from(ConceptsDB)

        conditions = []
        if q:
            stmt = stmt.where(ConceptsDB.name.ilike(f"%{q}%"))
            count_stmt = count_stmt.where(ConceptsDB.name.ilike(f"%{q}%"))
        if source:
            stmt = stmt.where(ConceptsDB.source == source)
            count_stmt = count_stmt.where(ConceptsDB.source == source)
        if is_active is not None:
            stmt = stmt.where(ConceptsDB.is_active == is_active)
            count_stmt = count_stmt.where(ConceptsDB.is_active == is_active)

        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = (
            stmt.order_by(ConceptsDB.name)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows], int(total)

    async def count_concepts(
        self,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        stmt = select(func.count()).select_from(ConceptsDB)
        if source:
            stmt = stmt.where(ConceptsDB.source == source)
        if is_active is not None:
            stmt = stmt.where(ConceptsDB.is_active == is_active)
        return int((await self._session.execute(stmt)).scalar_one())

    async def get_last_synced_at(self, source: str = "em") -> Optional[datetime]:
        stmt = (
            select(func.max(ConceptsDB.last_synced_at))
            .where(ConceptsDB.source == source)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()


# ── Protocol 实现标注 ─────────────────────────────────
ConceptRepoImpl.__implements_protocol__ = ConceptRepository
