"""操作池应用服务（业务模块：stock-pool/）

合并原 2 个 service：
- StockPoolAppService    → 池 CRUD + 成员管理
- PoolOperationAppService → 池操作（采集 K 线等后台派发任务 + 进度查询）

统一为 StockPoolService，依赖全部通过构造注入（DDD.md §4）。
"""
from __future__ import annotations

import logging

from application.port.operation_dispatcher_port import OperationDispatcherPort
from domain.base import DomainError
from domain.entitys.stock_info.repository import StockInfoRepository
from domain.entitys.stock_pool.entity import (
    CannotDeleteDefaultPoolError,
    MemberNotFoundError,
    PoolNotFoundError,
    PoolOperationConflictError,
    PoolOperationNotFoundError,
    StockPool,
)
from domain.entitys.stock_pool.repository import (
    PoolOperationRepository,
    StockPoolRepository,
)
from route.dto.request.pool_operation import (
    PoolKlineCollectRequest,
    PoolOperationCreateResponse,
    PoolOperationListRequest,
    PoolOperationListResponse,
    PoolOperationProgressVO,
    PoolOperationVO,
)
from route.dto.response.pool import (
    PoolAddMembersRequest,
    PoolAddMembersResponse,
    PoolCreateRequest,
    PoolDetailVO,
    PoolListResponse,
    PoolMemberListResponse,
    PoolMemberVO,
    PoolPoolsBySymbolResponse,
    PoolRemoveMembersRequest,
    PoolUpdateMemberMemoRequest,
    PoolUpdateRequest,
    PoolVO,
)

logger = logging.getLogger(__name__)


class StockPoolService:
    """操作池应用服务（依赖注入：只接 Repository / port）

    包含：
    - 池 CRUD：create / list / get / update / delete / archive
    - 成员管理：add / remove / clear / list / memo
    - 反向查询：find_pools_by_symbol
    - 默认池：ensure_default_pool
    - 池操作：K 线采集派发 + 进度查询 + 取消
    """

    def __init__(
        self,
        pool_repo: StockPoolRepository,
        stock_repo: StockInfoRepository,
        op_repo: PoolOperationRepository,
        dispatcher: OperationDispatcherPort,
    ) -> None:
        self._repo = pool_repo
        self._stock_repo = stock_repo
        self._op_repo = op_repo
        self._dispatcher = dispatcher

    # ══════════════════════════════════════════════════════════════════════
    # 池 CRUD
    # ══════════════════════════════════════════════════════════════════════

    async def create_pool(self, request: PoolCreateRequest) -> PoolVO:
        pool = StockPool.create(
            name=request.name, pool_type=request.pool_type,
            description=request.description, color=request.color, icon=request.icon,
        )
        created = await self._repo.create(pool)
        return PoolVO.model_validate(created.to_dict())

    async def list_pools(
        self, include_archived: bool = False, limit: int = 100, offset: int = 0,
    ) -> PoolListResponse:
        pools = await self._repo.find_all(
            include_archived=include_archived, limit=limit, offset=offset,
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
                    symbol=m.symbol, memo=m.memo, sort_order=m.sort_order,
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

    async def update_pool(self, pool_id: int, request: PoolUpdateRequest) -> PoolVO:
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

    # ══════════════════════════════════════════════════════════════════════
    # 成员管理
    # ══════════════════════════════════════════════════════════════════════

    async def add_members(
        self, pool_id: int, request: PoolAddMembersRequest,
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
        added, skipped = await self._repo.add_members_batch(pool_id, valid_symbols)
        skipped.extend(invalid_symbols)
        return PoolAddMembersResponse(
            pool_id=pool_id, added=added, skipped=skipped,
            total_added=len(added), total_skipped=len(skipped),
        )

    async def remove_members(
        self, pool_id: int, request: PoolRemoveMembersRequest,
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
        self, pool_id: int, request: PoolUpdateMemberMemoRequest,
    ) -> PoolMemberVO:
        pool = await self._repo.find_by_id(pool_id)
        if not pool:
            raise PoolNotFoundError(pool_id)
        if not pool.has_member(request.symbol):
            raise MemberNotFoundError(request.symbol, pool_id)
        await self._repo.update_member_memo(pool_id, request.symbol, request.memo)
        stock = await self._stock_repo.find_by_symbol(request.symbol)
        return PoolMemberVO(
            symbol=request.symbol, memo=request.memo,
            name=stock.name if stock else None, is_valid=stock is not None,
        )

    async def list_members(
        self, pool_id: int, limit: int = 100, offset: int = 0,
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
                    symbol=m.symbol, memo=m.memo, sort_order=m.sort_order,
                    added_at=m.added_at,
                    name=stock.name if stock else None,
                    industry=stock.industry.name if stock and stock.industry else None,
                    market=stock.market.name if stock and stock.market else None,
                    exchange=stock.exchange if stock else None,
                    is_valid=stock is not None,
                )
            )
        total = await self._repo.count_members(pool_id)
        return PoolMemberListResponse(pool_id=pool_id, total=total, items=member_vos)

    # ══════════════════════════════════════════════════════════════════════
    # 反向查询
    # ══════════════════════════════════════════════════════════════════════

    async def find_pools_by_symbol(self, symbol: str) -> PoolPoolsBySymbolResponse:
        pools = await self._repo.find_pools_by_symbol(symbol)
        pool_vos = [PoolVO.model_validate(p.to_dict()) for p in pools]
        return PoolPoolsBySymbolResponse(
            symbol=symbol, pools=pool_vos, total=len(pool_vos),
        )

    async def ensure_default_pool(self) -> PoolVO:
        existing = await self._repo.find_by_default()
        if existing:
            return PoolVO.model_validate(existing.to_dict())
        pool = StockPool.create(
            name="我的自选", pool_type="watchlist", is_default=True,
            icon="⭐", color="#FFB800",
        )
        created = await self._repo.create(pool)
        return PoolVO.model_validate(created.to_dict())

    # ══════════════════════════════════════════════════════════════════════
    # 池操作（K 线采集派发等）
    # ══════════════════════════════════════════════════════════════════════

    async def create_kline_collect_operation(
        self, request: PoolKlineCollectRequest,
    ) -> PoolOperationCreateResponse:
        pool = await self._pool_repo.find_by_id(request.pool_id)
        if not pool:
            raise PoolNotFoundError(request.pool_id)
        existing = await self._op_repo.list_by_pool(request.pool_id, limit=1)
        for op in existing:
            if op["status"] in ("pending", "running"):
                raise PoolOperationConflictError(request.pool_id)
        members = await self._pool_repo.list_members(request.pool_id, limit=10000)
        symbols = [m.symbol for m in members]
        if not symbols:
            return PoolOperationCreateResponse(
                operation_id=0, pool_id=request.pool_id,
                operation_type=request.operation_type, status="skipped",
                total=0, message="池内没有成员",
            )
        params = {"days": request.days}
        op_id = await self._op_repo.create(
            pool_id=request.pool_id,
            operation_type=request.operation_type,
            params=params,
        )
        await self._op_repo.update_progress(op_id, done=0, total=len(symbols))
        await self._dispatcher.dispatch_kline_collect(
            op_id=op_id, pool_id=request.pool_id,
            symbols=symbols, days=request.days,
        )
        return PoolOperationCreateResponse(
            operation_id=op_id, pool_id=request.pool_id,
            operation_type=request.operation_type, status="pending",
            total=len(symbols), message=f"操作已派发，共 {len(symbols)} 只股票",
        )

    async def list_operations(
        self, request: PoolOperationListRequest,
    ) -> PoolOperationListResponse:
        pool = await self._pool_repo.find_by_id(request.pool_id)
        if not pool:
            raise PoolNotFoundError(request.pool_id)
        ops = await self._op_repo.list_by_pool(
            request.pool_id, limit=request.limit, offset=request.offset,
        )
        items = []
        for op in ops:
            progress = PoolOperationProgressVO(
                done=op["progress"].get("done", 0),
                total=op["progress"].get("total", 0),
                failed=op["progress"].get("failed", 0),
            )
            items.append(
                PoolOperationVO(
                    id=op["id"], pool_id=op["pool_id"],
                    operation_type=op["operation_type"], status=op["status"],
                    params=op["params"], result_summary=op["result_summary"],
                    progress=progress, error_message=op["error_message"],
                    started_at=op["started_at"], finished_at=op["finished_at"],
                    created_at=op["created_at"],
                )
            )
        return PoolOperationListResponse(
            pool_id=request.pool_id, total=len(items), items=items,
        )

    async def get_operation(self, op_id: int) -> PoolOperationVO:
        op = await self._op_repo.find_by_id(op_id)
        if not op:
            raise PoolOperationNotFoundError(op_id)
        return self._build_op_vo(op)

    async def get_operation_progress(self, op_id: int) -> PoolOperationProgressVO:
        op = await self._op_repo.find_by_id(op_id)
        if not op:
            raise PoolOperationNotFoundError(op_id)
        return PoolOperationProgressVO(
            done=op["progress"].get("done", 0),
            total=op["progress"].get("total", 0),
            failed=op["progress"].get("failed", 0),
        )

    async def cancel_operation(self, op_id: int) -> PoolOperationVO:
        op = await self._op_repo.find_by_id(op_id)
        if not op:
            raise PoolOperationNotFoundError(op_id)
        if op["status"] not in ("pending", "running"):
            raise DomainError("该操作无法取消", "CANNOT_CANCEL")
        await self._dispatcher.cancel_operation(op_id)
        await self._op_repo.update_status(
            op_id, status="cancelled", finished_at=op.get("started_at"),
        )
        return await self.get_operation(op_id)

    @staticmethod
    def _build_op_vo(op: dict) -> PoolOperationVO:
        progress = PoolOperationProgressVO(
            done=op["progress"].get("done", 0),
            total=op["progress"].get("total", 0),
            failed=op["progress"].get("failed", 0),
        )
        return PoolOperationVO(
            id=op["id"], pool_id=op["pool_id"],
            operation_type=op["operation_type"], status=op["status"],
            params=op["params"], result_summary=op["result_summary"],
            progress=progress, error_message=op["error_message"],
            started_at=op["started_at"], finished_at=op["finished_at"],
            created_at=op["created_at"],
        )
