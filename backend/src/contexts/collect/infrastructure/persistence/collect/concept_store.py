"""概念采集读写 — 委托 ConceptRepoImpl（已有写方法）+ 自实现 reason / snapshot

配套设计文档：docs/backend-docs/dev/step5/03collect优化/02-端口与基础设施实现.md §3.2
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select

from contexts.collect.application.port.collect_port import ConceptStorePort
from contexts.data.application.port.concept import (
    ConceptIndexTHBO,
    ConceptListBO,
    ConceptOfStockBO,
    ConceptSnapshotBO,
)
from contexts.market.domain.service.market_session import market_now
from shared.infrastructure.persistence.connection import AsyncSessionLocal
from contexts.concept.infrastructure.persistence.models.concept import (
    ConceptMemberDB,
    ConceptsDB,
    ConceptSnapshotDB,
)
from contexts.concept.infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl


def _to_naive(dt: datetime) -> datetime:
    """去掉 tzinfo，匹配 TIMESTAMP WITHOUT TIME ZONE 列"""
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


class SqlConceptStore(ConceptStorePort):
    """概念采集读写（实现侧）"""

    # ── 清单（委托 ConceptRepoImpl）──
    async def list_active_concepts(self) -> list[tuple[int, str, str]]:
        async with AsyncSessionLocal() as session:
            return await ConceptRepoImpl(session).list_active_concepts()

    async def count_active(self) -> int:
        async with AsyncSessionLocal() as session:
            return await ConceptRepoImpl(session).count_active()

    async def upsert_concepts(self, bos: list[ConceptListBO]) -> dict[str, int]:
        async with AsyncSessionLocal() as session:
            return await ConceptRepoImpl(session).upsert_concepts(bos)

    async def deactivate_missing(self, keep_index_codes: list[str]) -> int:
        async with AsyncSessionLocal() as session:
            return await ConceptRepoImpl(session).deactivate_missing(keep_index_codes)

    # ── 成分股（委托 ConceptRepoImpl）──
    async def count_members(self, concept_id: int) -> int:
        async with AsyncSessionLocal() as session:
            return await ConceptRepoImpl(session).count_members(concept_id)

    async def replace_members(
        self, concept_id: int, symbols: list[str],
    ) -> tuple[int, int]:
        async with AsyncSessionLocal() as session:
            return await ConceptRepoImpl(session).replace_members(concept_id, symbols)

    # ── 指数日 K（委托 ConceptRepoImpl）──
    async def get_max_trade_dates(self) -> dict[str, date]:
        async with AsyncSessionLocal() as session:
            return await ConceptRepoImpl(session).get_max_trade_dates()

    async def upsert_index_th(self, bos: list[ConceptIndexTHBO]) -> int:
        async with AsyncSessionLocal() as session:
            return await ConceptRepoImpl(session).upsert_index_th(bos)

    # ── 入选理由（搬自 concept_reason.py 直写 SQL）──
    async def member_symbols(self, only_missing_reason: bool) -> list[str]:
        async with AsyncSessionLocal() as session:
            if only_missing_reason:
                rows = await session.execute(
                    select(ConceptMemberDB.symbol)
                    .where((ConceptMemberDB.reason.is_(None)) | (ConceptMemberDB.reason == ""))
                    .distinct()
                )
            else:
                rows = await session.execute(
                    select(ConceptMemberDB.symbol).distinct()
                )
            return sorted({r[0] for r in rows.all()})

    async def update_reasons(self, symbol: str, items: list[ConceptOfStockBO]) -> int:
        """按 (symbol, index_code) 命中已有关系，reason 变化才更新。返回更新条数。"""
        if not items:
            return 0
        async with AsyncSessionLocal() as session:
            member_rows = await session.execute(
                select(ConceptMemberDB).where(ConceptMemberDB.symbol == symbol)
            )
            members = list(member_rows.scalars().all())
            index_to_member = {m.concept_id: m for m in members}
            index_codes = [b.index_code for b in items if b.index_code]
            if not index_codes:
                return 0
            concept_rows = await session.execute(
                select(ConceptsDB).where(ConceptsDB.index_code.in_(index_codes))
            )
            id_by_index = {c.index_code: c.id for c in concept_rows.scalars().all()}
            updated = 0
            for b in items:
                cid = id_by_index.get(b.index_code)
                if cid is None or cid not in index_to_member:
                    continue
                m = index_to_member[cid]
                if b.reason and m.reason != b.reason:
                    m.reason = b.reason
                    updated += 1
            await session.commit()
            return updated

    # ── 快照（搬自 concept_snapshot.py 直写 SQL）──
    async def active_index_codes(self) -> list[str]:
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(ConceptsDB.index_code).where(ConceptsDB.is_active == True)  # noqa: E712
            )
            return sorted({r[0] for r in rows.all()})

    async def add_snapshot(
        self, index_code: str, snap: ConceptSnapshotBO, trade_time: datetime,
    ) -> None:
        async with AsyncSessionLocal() as session:
            row = (await session.execute(
                select(ConceptsDB.name).where(ConceptsDB.index_code == index_code)
            )).first()
            concept_name = row[0] if row else index_code
            now = datetime.now(timezone.utc)
            session.add(ConceptSnapshotDB(
                index_code=index_code,
                concept_name=concept_name,
                # trade_time 列为 TIMESTAMP WITHOUT TIME ZONE，存市场本地时间（去 tz）
                trade_time=_to_naive(market_now()),
                open_price=snap.open,
                high=snap.high,
                low=snap.low,
                price=snap.price,
                prev_close=snap.prev_close,
                pct_change=snap.change_pct,
                source="ths",
                captured_at=now,
            ))
            await session.commit()


__all__ = ["SqlConceptStore"]
