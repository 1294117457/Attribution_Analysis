"""fundamental routes — 基本面 12 个 service 对应 12 个 route

Phase3：内联 CollectBody → DTO CollectRequest / CollectResponse
Phase3 v3（2026-10-19）：
  - INCREMENTAL/FULL_REFRESH service 走 TaskRunner 派发，返回 {log_id, status}
  - REALTIME service（concept_minute）保留 CollectResult 兼容
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from shared.interface import _response as R
from contexts.collect.interface.dto.request.collect import CollectRequest
from contexts.collect.interface.dto.response.collect import (
    ApiResponse,
    CollectResponse,
)
from contexts.collect.infrastructure.di.collect_service import (
    get_daily_basic_service,
    get_fin_income_service,
    get_top10_holders_service,
    get_top10_float_holders_service,
    get_dividend_service,
    get_stock_basic_service,
    get_stock_concepts_service,
    get_concept_list_service,
    get_concept_members_service,
    get_concept_index_daily_service,
    get_concept_minute_service,
    get_concept_snapshot_service,
)

router = APIRouter(prefix="/collect/fundamental", tags=["采集-基本面"])


async def _run(svc, body: CollectRequest) -> CollectResponse:
    """统一执行：触发后台采集任务

    Phase 3 v3：所有 INCREMENTAL/FULL_REFRESH service 返回 {log_id, status}；
    concept_minute（REALTIME）保留 CollectResult 兼容。
    """
    result = await svc.collect(body.params)
    if isinstance(result, dict):
        return CollectResponse(
            log_id=result.get("log_id"),
            status=result.get("status"),
            message=f"采集任务已派发，前端请用 log_id 轮询 /collect/logs/{result.get('log_id')}",
        )
    # 兼容：REALTIME service（concept_minute）返回 CollectResult
    return CollectResponse(
        total=result.total, success=result.success, fail=result.fail,
        skip=result.skip, saved=result.saved, message=result.message,
    )


@router.post("/daily_basic", response_model=ApiResponse[CollectResponse], summary="每日估值")
async def daily_basic_trigger(body: CollectRequest, svc=Depends(get_daily_basic_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/fin_income", response_model=ApiResponse[CollectResponse], summary="利润表")
async def fin_income_trigger(body: CollectRequest, svc=Depends(get_fin_income_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/top10_holders", response_model=ApiResponse[CollectResponse], summary="前 10 大股东")
async def top10_holders_trigger(body: CollectRequest, svc=Depends(get_top10_holders_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/top10_floatholders", response_model=ApiResponse[CollectResponse], summary="前 10 大流通股东")
async def top10_float_trigger(body: CollectRequest, svc=Depends(get_top10_float_holders_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/dividend", response_model=ApiResponse[CollectResponse], summary="分红送股")
async def dividend_trigger(body: CollectRequest, svc=Depends(get_dividend_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/stock_basic", response_model=ApiResponse[CollectResponse], summary="股票基本信息")
async def stock_basic_trigger(body: CollectRequest, svc=Depends(get_stock_basic_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/stock_concepts", response_model=ApiResponse[CollectResponse], summary="股票所属概念")
async def stock_concepts_trigger(body: CollectRequest, svc=Depends(get_stock_concepts_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/concept_list", response_model=ApiResponse[CollectResponse], summary="概念清单")
async def concept_list_trigger(body: CollectRequest, svc=Depends(get_concept_list_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/concept_members", response_model=ApiResponse[CollectResponse], summary="概念成分股")
async def concept_members_trigger(body: CollectRequest, svc=Depends(get_concept_members_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/concept_index_daily", response_model=ApiResponse[CollectResponse], summary="概念指数日 K")
async def concept_index_daily_trigger(body: CollectRequest, svc=Depends(get_concept_index_daily_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/concept_minute", response_model=ApiResponse[CollectResponse], summary="概念分时")
async def concept_minute_trigger(body: CollectRequest, svc=Depends(get_concept_minute_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/concept_snapshot", response_model=ApiResponse[CollectResponse], summary="概念行情快照")
async def concept_snapshot_trigger(body: CollectRequest, svc=Depends(get_concept_snapshot_service)):
    return R.ok((await _run(svc, body)).model_dump())


__all__ = ["router"]