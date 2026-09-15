"""操作池 API 路由"""

from fastapi import APIRouter, Depends, Path, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.pool import (
    PoolCreateRequest,
    PoolUpdateRequest,
    PoolAddMembersRequest,
    PoolRemoveMembersRequest,
    PoolUpdateMemberMemoRequest,
)
from application.dto.pool_operation import (
    PoolKlineCollectRequest,
    PoolOperationListRequest,
)
from application.pool_service import StockPoolAppService
from application.pool_operation_service import PoolOperationAppService
from infrastructure.database.connection import get_db
from route.schemas.response import (
    ok, created, bad_request, not_found, err,
)

router = APIRouter(prefix="/api/v1", tags=["操作池"])


def get_pool_service(db: AsyncSession = Depends(get_db)) -> StockPoolAppService:
    return StockPoolAppService(session=db)


def get_pool_op_service(
    db: AsyncSession = Depends(get_db),
) -> PoolOperationAppService:
    return PoolOperationAppService(session=db)


# ═══════════════════════════════════════════════════════════════════════════════
# 池管理
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/pools",
    summary="创建池",
    status_code=status.HTTP_201_CREATED,
)
async def create_pool(
    request: PoolCreateRequest,
    service: StockPoolAppService = Depends(get_pool_service),
):
    pool = await service.create_pool(request)
    return created(pool.model_dump(), "创建成功")


@router.get("/pools", summary="池列表")
async def list_pools(
    include_archived: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: StockPoolAppService = Depends(get_pool_service),
):
    result = await service.list_pools(
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    return ok(result.model_dump())


@router.get("/pools/{pool_id}", summary="池详情")
async def get_pool(
    pool_id: int = Path(..., description="池 ID"),
    service: StockPoolAppService = Depends(get_pool_service),
):
    pool = await service.get_pool(pool_id)
    return ok(pool.model_dump())


@router.patch("/pools/{pool_id}", summary="更新池")
async def update_pool(
    pool_id: int = Path(...),
    request: PoolUpdateRequest = Body(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    pool = await service.update_pool(pool_id, request)
    return ok(pool.model_dump(), "更新成功")


@router.delete("/pools/{pool_id}", summary="删除池")
async def delete_pool(
    pool_id: int = Path(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    await service.delete_pool(pool_id)
    return ok(message="删除成功")


# ═══════════════════════════════════════════════════════════════════════════════
# 成员管理
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/pools/{pool_id}/members", summary="批量添加成员")
async def add_members(
    pool_id: int = Path(...),
    request: PoolAddMembersRequest = Body(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    result = await service.add_members(pool_id, request)
    return ok(result.model_dump(), "添加完成")


@router.delete("/pools/{pool_id}/members", summary="批量删除成员")
async def remove_members(
    pool_id: int = Path(...),
    request: PoolRemoveMembersRequest = Body(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    count = await service.remove_members(pool_id, request)
    return ok({"removed_count": count}, f"成功移除 {count} 个成员")


@router.get("/pools/{pool_id}/members", summary="成员列表")
async def list_members(
    pool_id: int = Path(...),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: StockPoolAppService = Depends(get_pool_service),
):
    result = await service.list_members(pool_id, limit, offset)
    return ok(result.model_dump())


@router.patch("/pools/{pool_id}/members/{symbol}", summary="更新成员备注")
async def update_member_memo(
    pool_id: int = Path(...),
    symbol: str = Path(..., description="股票代码"),
    request: PoolUpdateMemberMemoRequest = Body(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    member = await service.update_member_memo(pool_id, request)
    return ok(member.model_dump(), "更新成功")


@router.delete("/pools/{pool_id}/members/{symbol}", summary="删除单个成员")
async def remove_member(
    pool_id: int = Path(...),
    symbol: str = Path(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    await service.remove_members(
        pool_id, PoolRemoveMembersRequest(symbols=[symbol])
    )
    return ok(message="成员已移除")


# ═══════════════════════════════════════════════════════════════════════════════
# 反向查询
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/pools/by-symbol/{symbol}", summary="股票在哪些池")
async def find_pools_by_symbol(
    symbol: str = Path(..., description="股票代码"),
    service: StockPoolAppService = Depends(get_pool_service),
):
    result = await service.find_pools_by_symbol(symbol)
    return ok(result.model_dump())


# ═══════════════════════════════════════════════════════════════════════════════
# 池级操作
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/pools/{pool_id}/operations",
    summary="发起池操作",
    status_code=status.HTTP_201_CREATED,
)
async def create_pool_operation(
    pool_id: int = Path(...),
    request: PoolKlineCollectRequest = Body(...),
    service: PoolOperationAppService = Depends(get_pool_op_service),
):
    result = await service.create_kline_collect_operation(request)
    return created(result.model_dump(), result.message)


@router.get("/pools/{pool_id}/operations", summary="操作历史")
async def list_pool_operations(
    pool_id: int = Path(...),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: PoolOperationAppService = Depends(get_pool_op_service),
):
    result = await service.list_operations(
        PoolOperationListRequest(pool_id=pool_id, limit=limit, offset=offset)
    )
    return ok(result.model_dump())


# ═══════════════════════════════════════════════════════════════════════════════
# 操作记录
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/operations/{op_id}", summary="操作详情")
async def get_operation(
    op_id: int = Path(...),
    service: PoolOperationAppService = Depends(get_pool_op_service),
):
    op = await service.get_operation(op_id)
    return ok(op.model_dump())


@router.get("/operations/{op_id}/progress", summary="操作进度（轻量）")
async def get_operation_progress(
    op_id: int = Path(...),
    service: PoolOperationAppService = Depends(get_pool_op_service),
):
    progress = await service.get_operation_progress(op_id)
    return ok(progress.model_dump())


@router.post("/operations/{op_id}/cancel", summary="取消操作")
async def cancel_operation(
    op_id: int = Path(...),
    service: PoolOperationAppService = Depends(get_pool_op_service),
):
    op = await service.cancel_operation(op_id)
    return ok(op.model_dump(), "操作已取消")
