"""操作池应用服务"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.pool import (
    PoolCreateRequest,
    PoolUpdateRequest,
    PoolAddMembersRequest,
    PoolRemoveMembersRequest,
    PoolUpdateMemberMemoRequest,
    PoolVO,
    PoolDetailVO,
    PoolMemberVO,
    PoolListResponse,
    PoolMemberListResponse,
    PoolAddMembersResponse,
    PoolPoolsBySymbolResponse,
)
from application.exceptions import (
    PoolNotFoundError,
    CannotDeleteDefaultPoolError,
    DuplicatePoolMemberError,
    PoolMemberNotFoundError,
)
from domain.stock_pool.entity import StockPool, DuplicateMemberError as DomainDuplicateMemberError
from domain.stock_pool.repository import StockPoolRepository
from infrastructure.repositories.pool_repository import StockPoolRepoImpl
from infrastructure.repositories.stock_repository import StockRepoImpl

logger = logging.getLogger(__name__)


class StockPoolAppService:
    """操作池应用服务"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo: StockPoolRepository = StockPoolRepoImpl(session)
        self._stock_repo = StockRepoImpl(session)

    # ── 池 CRUD ─────────────────────────────────────────────────────────────

    async def create_pool(self, request: PoolCreateRequest) -> PoolVO:
        pool = StockPool.create(
            name=request.name,
            pool_type=request.pool_type,
            description=request.description,
            color=request.color,
            icon=request.icon,
        )
        created = await self._repo.create(pool)
        return PoolVO.model_validate(created.to_dict())

    async def list_pools(
        self,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> PoolListResponse:
        pools = await self._repo.find_all(
            include_archived=include_archived,
            limit=limit,
            offset=offset,
        )
        items = [PoolVO.model_validate(p.to_dict()) for p in pools]
        return PoolListResponse(total=len(items), items=items)

    async def get_pool(self, pool_id: int) -> PoolDetailVO:
        pool = await self._repo.find_by_id(pool_id)
        if not pool:
            raise PoolNotFoundError(pool_id)

        members = await self._repo.list_members(pool_id, limit=10000)
        member_vos = []
        for m in members:
            stock = await self._stock_repo.find_by_symbol(m.symbol)
            member_vos.append(
                PoolMemberVO(
                    symbol=m.symbol,
                    memo=m.memo,
                    sort_order=m.sort_order,
                    added_at=m.added_at,
                    name=stock.name if stock else None,
                    industry=stock.industry.name if stock and stock.industry else None,
                    market=stock.market.name if stock and stock.market else None,
                    exchange=stock.exchange if stock else None,
                    is_valid=stock is not None,
                )
            )

        vo = PoolDetailVO.model_validate(pool.to_dict())
        vo.members = member_vos
        return vo

    async def update_pool(
        self, pool_id: int, request: PoolUpdateRequest
    ) -> PoolVO:
        pool = await self._repo.find_by_id(pool_id)
        if not pool:
            raise PoolNotFoundError(pool_id)

        if request.name is not None:
            pool.rename(request.name)
        if request.description is not None:
            pool.update_description(request.description)
        if request.color is not None:
            pool.update_color(request.color)
        if request.icon is not None:
            pool.update_icon(request.icon)
        if request.sort_order is not None:
            pool.sort_order = request.sort_order

        updated = await self._repo.update(pool)
        return PoolVO.model_validate(updated.to_dict())

    async def delete_pool(self, pool_id: int) -> None:
        pool = await self._repo.find_by_id(pool_id)
        if not pool:
            raise PoolNotFoundError(pool_id)
        if pool.is_default:
            raise CannotDeleteDefaultPoolError()

        await self._repo.delete(pool_id)

    async def archive_pool(self, pool_id: int) -> PoolVO:
        pool = await self._repo.find_by_id(pool_id)
        if not pool:
            raise PoolNotFoundError(pool_id)
        pool.archive()
        updated = await self._repo.update(pool)
        return PoolVO.model_validate(updated.to_dict())

    # ── 成员管理 ─────────────────────────────────────────────────────────────

    async def add_members(
        self, pool_id: int, request: PoolAddMembersRequest
    ) -> PoolAddMembersResponse:
        pool = await self._repo.find_by_id(pool_id)
        if not pool:
            raise PoolNotFoundError(pool_id)

        if request.validate_exists:
            valid_symbols, invalid_symbols = [], []
            for symbol in request.symbols:
                stock = await self._stock_repo.find_by_symbol(symbol)
                if stock:
                    valid_symbols.append(symbol)
                else:
                    invalid_symbols.append(symbol)
        else:
            valid_symbols = list(request.symbols)
            invalid_symbols = []

        added, skipped = await self._repo.add_members_batch(
            pool_id, valid_symbols
        )
        skipped.extend(invalid_symbols)

        return PoolAddMembersResponse(
            pool_id=pool_id,
            added=added,
            skipped=skipped,
            total_added=len(added),
            total_skipped=len(skipped),
        )

    async def remove_members(
        self, pool_id: int, request: PoolRemoveMembersRequest
    ) -> int:
        pool = await self._repo.find_by_id(pool_id)
        if not pool:
            raise PoolNotFoundError(pool_id)

        return await self._repo.remove_members_batch(pool_id, request.symbols)

    async def clear_members(self, pool_id: int) -> int:
        pool = await self._repo.find_by_id(pool_id)
        if not pool:
            raise PoolNotFoundError(pool_id)

        return await self._repo.clear_members(pool_id)

    async def update_member_memo(
        self, pool_id: int, request: PoolUpdateMemberMemoRequest
    ) -> PoolMemberVO:
        pool = await self._repo.find_by_id(pool_id)
        if not pool:
            raise PoolNotFoundError(pool_id)

        if not pool.has_member(request.symbol):
            raise PoolMemberNotFoundError(request.symbol)

        await self._repo.update_member_memo(
            pool_id, request.symbol, request.memo
        )

        stock = await self._stock_repo.find_by_symbol(request.symbol)
        return PoolMemberVO(
            symbol=request.symbol,
            memo=request.memo,
            name=stock.name if stock else None,
            is_valid=stock is not None,
        )

    async def list_members(
        self,
        pool_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> PoolMemberListResponse:
        pool = await self._repo.find_by_id(pool_id)
        if not pool:
            raise PoolNotFoundError(pool_id)

        members = await self._repo.list_members(pool_id, limit, offset)
        member_vos = []
        for m in members:
            stock = await self._stock_repo.find_by_symbol(m.symbol)
            member_vos.append(
                PoolMemberVO(
                    symbol=m.symbol,
                    memo=m.memo,
                    sort_order=m.sort_order,
                    added_at=m.added_at,
                    name=stock.name if stock else None,
                    industry=stock.industry.name if stock and stock.industry else None,
                    market=stock.market.name if stock and stock.market else None,
                    exchange=stock.exchange if stock else None,
                    is_valid=stock is not None,
                )
            )

        total = await self._repo.count_members(pool_id)
        return PoolMemberListResponse(
            pool_id=pool_id,
            total=total,
            items=member_vos,
        )

    # ── 反向查询 ─────────────────────────────────────────────────────────────

    async def find_pools_by_symbol(self, symbol: str) -> PoolPoolsBySymbolResponse:
        pools = await self._repo.find_pools_by_symbol(symbol)
        pool_vos = [PoolVO.model_validate(p.to_dict()) for p in pools]
        return PoolPoolsBySymbolResponse(
            symbol=symbol,
            pools=pool_vos,
            total=len(pool_vos),
        )

    # ── 辅助方法 ─────────────────────────────────────────────────────────────

    async def ensure_default_pool(self) -> PoolVO:
        existing = await self._repo.find_by_default()
        if existing:
            return PoolVO.model_validate(existing.to_dict())

        pool = StockPool.create(
            name="我的自选",
            pool_type="watchlist",
            is_default=True,
            icon="⭐",
            color="#FFB800",
        )
        created = await self._repo.create(pool)
        return PoolVO.model_validate(created.to_dict())
