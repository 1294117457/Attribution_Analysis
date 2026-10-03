"""池操作应用服务

DDD 改造（2026-10-03）：构造改为依赖注入，只接收 Repository / port，
不再持有 AsyncSession，也不再直接 import `infrastructure.*`（DDD.md §4）。
"""
from __future__ import annotations

import logging

from route.dto.request.pool_operation import (
    PoolKlineCollectRequest,
    PoolOperationCreateResponse,
    PoolOperationListRequest,
    PoolOperationListResponse,
    PoolOperationProgressVO,
    PoolOperationVO,
)
from application.port.operation_dispatcher_port import OperationDispatcherPort
from domain.base import DomainError
from domain.entitys.stock_pool.entity import (
    PoolNotFoundError,
    PoolOperationConflictError,
    PoolOperationNotFoundError,
)
from domain.entitys.stock_pool.repository import PoolOperationRepository, StockPoolRepository

logger = logging.getLogger(__name__)


class PoolOperationAppService:
    """池操作应用服务（依赖注入）"""

    def __init__(
        self,
        pool_repo: StockPoolRepository,
        op_repo: PoolOperationRepository,
        dispatcher: OperationDispatcherPort,
    ) -> None:
        self._pool_repo = pool_repo
        self._op_repo = op_repo
        self._dispatcher = dispatcher

    async def create_kline_collect_operation(
        self, request: PoolKlineCollectRequest
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
                operation_id=0,
                pool_id=request.pool_id,
                operation_type=request.operation_type,
                status="skipped",
                total=0,
                message="池内没有成员",
            )

        params = {
            "days": request.days,
        }
        op_id = await self._op_repo.create(
            pool_id=request.pool_id,
            operation_type=request.operation_type,
            params=params,
        )

        await self._op_repo.update_progress(
            op_id, done=0, total=len(symbols)
        )

        await self._dispatcher.dispatch_kline_collect(
            op_id=op_id,
            pool_id=request.pool_id,
            symbols=symbols,
            days=request.days,
        )

        return PoolOperationCreateResponse(
            operation_id=op_id,
            pool_id=request.pool_id,
            operation_type=request.operation_type,
            status="pending",
            total=len(symbols),
            message=f"操作已派发，共 {len(symbols)} 只股票",
        )

    async def list_operations(
        self, request: PoolOperationListRequest
    ) -> PoolOperationListResponse:
        pool = await self._pool_repo.find_by_id(request.pool_id)
        if not pool:
            raise PoolNotFoundError(request.pool_id)

        ops = await self._op_repo.list_by_pool(
            request.pool_id, limit=request.limit, offset=request.offset
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
                    id=op["id"],
                    pool_id=op["pool_id"],
                    operation_type=op["operation_type"],
                    status=op["status"],
                    params=op["params"],
                    result_summary=op["result_summary"],
                    progress=progress,
                    error_message=op["error_message"],
                    started_at=op["started_at"],
                    finished_at=op["finished_at"],
                    created_at=op["created_at"],
                )
            )

        return PoolOperationListResponse(
            pool_id=request.pool_id,
            total=len(items),
            items=items,
        )

    async def get_operation(self, op_id: int) -> PoolOperationVO:
        op = await self._op_repo.find_by_id(op_id)
        if not op:
            raise PoolOperationNotFoundError(op_id)

        progress = PoolOperationProgressVO(
            done=op["progress"].get("done", 0),
            total=op["progress"].get("total", 0),
            failed=op["progress"].get("failed", 0),
        )
        return PoolOperationVO(
            id=op["id"],
            pool_id=op["pool_id"],
            operation_type=op["operation_type"],
            status=op["status"],
            params=op["params"],
            result_summary=op["result_summary"],
            progress=progress,
            error_message=op["error_message"],
            started_at=op["started_at"],
            finished_at=op["finished_at"],
            created_at=op["created_at"],
        )

    async def get_operation_progress(
        self, op_id: int
    ) -> PoolOperationProgressVO:
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
            op_id,
            status="cancelled",
            finished_at=op.get("started_at"),
        )
        return await self.get_operation(op_id)