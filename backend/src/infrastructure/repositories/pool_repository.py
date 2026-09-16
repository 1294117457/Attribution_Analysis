"""操作池仓储实现"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, delete, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.stock_pool.entity import StockPool, DuplicateMemberError
from domain.stock_pool.repository import StockPoolRepository
from domain.stock_pool.value_objects import PoolMember, PoolType
from domain.stock_pool.schemas import StockPoolVO
from infrastructure.database.models.pool import (
    StockPoolDB,
    StockPoolMemberDB,
)

logger = logging.getLogger(__name__)


class StockPoolRepoImpl(StockPoolRepository):
    """操作池仓储实现"""

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── ORM ↔ Entity 转换 ──────────────────────────────────────────────────

    def _to_entity(self, db: StockPoolDB) -> StockPool:
        members = [
            PoolMember(
                symbol=m.symbol,
                memo=m.memo or "",
                sort_order=m.sort_order,
                added_at=m.added_at,
            )
            for m in db.members
        ]
        return StockPool.reconstitute(
            id=db.id,
            name=db.name,
            pool_type=db.pool_type,
            description=db.description,
            color=db.color,
            icon=db.icon,
            sort_order=db.sort_order,
            is_default=db.is_default,
            is_archived=db.is_archived,
            members=members,
            created_at=db.created_at,
            updated_at=db.updated_at,
        )

    def _to_entity_light(self, db: StockPoolDB, member_count: Optional[int] = None) -> StockPool:
        """不含成员的轻量实体

        member_count: 来自单独查询的真实成员数（仅用于列表场景，避免 N+1）。
        """
        pool = StockPool.reconstitute(
            id=db.id,
            name=db.name,
            pool_type=db.pool_type,
            description=db.description,
            color=db.color,
            icon=db.icon,
            sort_order=db.sort_order,
            is_default=db.is_default,
            is_archived=db.is_archived,
            members=[],
            created_at=db.created_at,
            updated_at=db.updated_at,
        )
        if member_count is not None:
            pool._member_count_override = member_count
        return pool

    # ── 池 CRUD ─────────────────────────────────────────────────────────────

    async def create(self, pool: StockPool) -> StockPool:
        db = StockPoolDB(
            name=pool.name,
            pool_type=pool.pool_type.code,
            description=pool.description,
            color=pool.color,
            icon=pool.icon,
            sort_order=pool.sort_order,
            is_default=pool.is_default,
            is_archived=pool.is_archived,
        )
        self._session.add(db)
        await self._session.flush()
        await self._session.refresh(db)

        if pool.members:
            member_dbs = [
                StockPoolMemberDB(
                    pool_id=db.id,
                    symbol=m.symbol,
                    memo=m.memo,
                    sort_order=m.sort_order,
                    added_at=m.added_at or datetime.now(),
                )
                for m in pool.members
            ]
            self._session.add_all(member_dbs)
            await self._session.flush()

        return self._to_entity(db)

    async def find_by_id(self, pool_id: int) -> Optional[StockPool]:
        stmt = (
            select(StockPoolDB)
            .where(StockPoolDB.id == pool_id)
            .options(selectinload(StockPoolDB.members))
        )
        result = await self._session.execute(stmt)
        db = result.scalar_one_or_none()
        return self._to_entity(db) if db else None

    async def find_by_id_with_members(self, pool_id: int) -> Optional[StockPool]:
        return await self.find_by_id(pool_id)

    async def find_all(
        self,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StockPool]:
        stmt = (
            select(StockPoolDB)
            .order_by(
                StockPoolDB.is_default.desc(),
                StockPoolDB.sort_order.asc(),
                StockPoolDB.updated_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        if not include_archived:
            stmt = stmt.where(StockPoolDB.is_archived == False)

        result = await self._session.execute(stmt)
        dbs = result.scalars().all()
        if not dbs:
            return []
        # 批量统计每个池的成员数（避免 N+1）
        pool_ids = [db.id for db in dbs]
        count_stmt = (
            select(
                StockPoolMemberDB.pool_id,
                func.count(StockPoolMemberDB.symbol),
            )
            .where(StockPoolMemberDB.pool_id.in_(pool_ids))
            .group_by(StockPoolMemberDB.pool_id)
        )
        count_result = await self._session.execute(count_stmt)
        counts = {pid: cnt for pid, cnt in count_result.all()}
        return [
            self._to_entity_light(db, member_count=counts.get(db.id, 0))
            for db in dbs
        ]

    async def find_by_default(self) -> Optional[StockPool]:
        stmt = (
            select(StockPoolDB)
            .where(StockPoolDB.is_default == True)
            .options(selectinload(StockPoolDB.members))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        db = result.scalar_one_or_none()
        return self._to_entity(db) if db else None

    async def update(self, pool: StockPool) -> StockPool:
        stmt = (
            update(StockPoolDB)
            .where(StockPoolDB.id == pool.id)
            .values(
                name=pool.name,
                pool_type=pool.pool_type.code,
                description=pool.description,
                color=pool.color,
                icon=pool.icon,
                sort_order=pool.sort_order,
                is_archived=pool.is_archived,
                updated_at=datetime.now(),
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return await self.find_by_id(pool.id)

    async def delete(self, pool_id: int) -> bool:
        stmt = delete(StockPoolDB).where(StockPoolDB.id == pool_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    # ── 成员管理 ─────────────────────────────────────────────────────────────

    async def add_member(
        self, pool_id: int, symbol: str, memo: str = ""
    ) -> PoolMember:
        existing = await self._session.execute(
            select(StockPoolMemberDB).where(
                and_(
                    StockPoolMemberDB.pool_id == pool_id,
                    StockPoolMemberDB.symbol == symbol,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateMemberError(symbol, pool_id)

        count_result = await self._session.execute(
            select(func.count(StockPoolMemberDB.pool_id)).where(
                StockPoolMemberDB.pool_id == pool_id
            )
        )
        count = count_result.scalar() or 0

        member_db = StockPoolMemberDB(
            pool_id=pool_id,
            symbol=symbol,
            memo=memo,
            sort_order=count,
            added_at=datetime.now(),
        )
        self._session.add(member_db)
        await self._session.flush()

        return PoolMember(
            symbol=symbol,
            memo=memo,
            sort_order=count,
            added_at=datetime.now(),
        )

    async def add_members_batch(
        self, pool_id: int, symbols: list[str]
    ) -> tuple[list[str], list[str]]:
        added, skipped = [], []
        for symbol in symbols:
            try:
                await self.add_member(pool_id, symbol)
                added.append(symbol)
            except DuplicateMemberError:
                skipped.append(symbol)
            except Exception as e:
                logger.warning("添加成员失败 %s: %s", symbol, e)
                skipped.append(symbol)
        return added, skipped

    async def remove_member(self, pool_id: int, symbol: str) -> bool:
        stmt = delete(StockPoolMemberDB).where(
            and_(
                StockPoolMemberDB.pool_id == pool_id,
                StockPoolMemberDB.symbol == symbol,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def remove_members_batch(
        self, pool_id: int, symbols: list[str]
    ) -> int:
        stmt = delete(StockPoolMemberDB).where(
            and_(
                StockPoolMemberDB.pool_id == pool_id,
                StockPoolMemberDB.symbol.in_(symbols),
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def clear_members(self, pool_id: int) -> int:
        stmt = delete(StockPoolMemberDB).where(
            StockPoolMemberDB.pool_id == pool_id
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def update_member_memo(
        self, pool_id: int, symbol: str, memo: str
    ) -> bool:
        stmt = (
            update(StockPoolMemberDB)
            .where(
                and_(
                    StockPoolMemberDB.pool_id == pool_id,
                    StockPoolMemberDB.symbol == symbol,
                )
            )
            .values(memo=memo)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def list_members(
        self,
        pool_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PoolMember]:
        stmt = (
            select(StockPoolMemberDB)
            .where(StockPoolMemberDB.pool_id == pool_id)
            .order_by(
                StockPoolMemberDB.sort_order.asc(),
                StockPoolMemberDB.added_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        dbs = result.scalars().all()
        return [
            PoolMember(
                symbol=m.symbol,
                memo=m.memo or "",
                sort_order=m.sort_order,
                added_at=m.added_at,
            )
            for m in dbs
        ]

    async def count_members(self, pool_id: int) -> int:
        stmt = (
            select(func.count(StockPoolMemberDB.pool_id))
            .where(StockPoolMemberDB.pool_id == pool_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    # ── 反向查询 ─────────────────────────────────────────────────────────────

    async def find_pools_by_symbol(self, symbol: str) -> list[StockPool]:
        stmt = (
            select(StockPoolDB)
            .join(StockPoolMemberDB)
            .where(
                and_(
                    StockPoolMemberDB.symbol == symbol,
                    StockPoolDB.is_archived == False,
                )
            )
            .order_by(StockPoolDB.is_default.desc(), StockPoolDB.updated_at.desc())
        )
        result = await self._session.execute(stmt)
        dbs = result.scalars().all()
        return [self._to_entity_light(db) for db in dbs]
