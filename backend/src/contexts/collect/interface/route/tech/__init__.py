"""tech routes — 技术面 5 个 service 对应 5 个 route

Phase3：内联 CollectBody → DTO CollectRequest / CollectResponse
Phase3 v3（2026-10-19）：所有 service 统一走 TaskRunner 派发
  - collect() 返回 {"log_id", "status"}（INCREMENTAL/FULL_REFRESH）
  - REALTIME service（minute_kline）保留 CollectResult 兼容
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from shared.interface import _response as R
from contexts.collect.interface.dto.request.collect import CollectRequest
from contexts.collect.interface.dto.response.collect import ApiResponse, CollectResponse
from contexts.collect.infrastructure.di.collect_service import (
    get_daily_kline_service,
    get_minute_kline_service,
    get_adj_factor_service,
    get_suspend_service,
    get_name_change_service,
)

router = APIRouter(prefix="/collect/tech", tags=["采集-技术面"])


async def _run(svc, body: CollectRequest) -> CollectResponse:
    """统一执行：触发后台采集任务

    Phase 2 统一返回 dict（INCREMENTAL/FULL_REFRESH）：
        {log_id, status}

    REALTIME service（minute_kline）暂保留 CollectResult 兼容。
    """
    result = await svc.collect(body.params)
    if isinstance(result, dict):
        return CollectResponse(
            log_id=result.get("log_id"),
            status=result.get("status"),
            message=f"采集任务已派发，前端请用 log_id 轮询 /collect/logs/{result.get('log_id')}",
        )
    # 兼容：REALTIME service 返回 CollectResult
    return CollectResponse(
        total=result.total, success=result.success, fail=result.fail,
        skip=result.skip, saved=result.saved, message=result.message,
    )


@router.post(
    "/daily_kline", summary="日 K 线采集（按 symbol 批量）",
    response_model=ApiResponse[CollectResponse],
)
async def daily_kline_trigger(body: CollectRequest, svc=Depends(get_daily_kline_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post(
    "/minute_kline", summary="分钟 K 线（实时查询入口）",
    response_model=ApiResponse[CollectResponse],
)
async def minute_kline_trigger(body: CollectRequest, svc=Depends(get_minute_kline_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post(
    "/adj_factor", summary="复权因子采集（按 symbol 批量）",
    response_model=ApiResponse[CollectResponse],
)
async def adj_factor_trigger(body: CollectRequest, svc=Depends(get_adj_factor_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post(
    "/suspend", summary="停复牌采集",
    response_model=ApiResponse[CollectResponse],
)
async def suspend_trigger(body: CollectRequest, svc=Depends(get_suspend_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post(
    "/name_change", summary="股票曾用名采集",
    response_model=ApiResponse[CollectResponse],
)
async def name_change_trigger(body: CollectRequest, svc=Depends(get_name_change_service)):
    return R.ok((await _run(svc, body)).model_dump())


__all__ = ["router"]
