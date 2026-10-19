"""tech routes — 技术面 5 个 service 对应 5 个 route

URL 风格：POST /collect/tech/{service_name}

Phase3：内联 CollectBody → DTO CollectRequest / CollectResponse
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from shared.interface import _response as R
from contexts.collect.interface.dto.request.collect import CollectRequest
from contexts.collect.interface.dto.response.collect import CollectResponse
from contexts.collect.infrastructure.di.collect_service import (
    get_daily_kline_service,
    get_minute_kline_service,
    get_adj_factor_service,
    get_suspend_service,
    get_name_change_service,
)

router = APIRouter(prefix="/collect/tech", tags=["采集-技术面"])


async def _run(svc, body: CollectRequest) -> CollectResponse:
    """统一执行：mode 不进 params（业务字段纯净）

    当前实现：所有 service.collect() 都是"异步派发"模式——
        1. log_service.create_pending()  建日志
        2. task_runner.dispatch()       派发后台任务
        3. 立刻返回 { log_id, status: "pending" }

    前端拿到 log_id 后用 GET /collect/logs/{service_name}/{log_id} 轮询进度。
    service 内部从 META.kind 派生采集模式（incremental / full_refresh）。
    """
    result = await svc.collect(body.params)
    return CollectResponse(
        log_id=result.get("log_id"),
        status=result.get("status"),
        message=f"采集任务已派发，前端请用 log_id 轮询 /collect/logs/{body.service_name if hasattr(body, 'service_name') else ''}/{result.get('log_id')}",
    )


@router.post(
    "/daily_kline", summary="日 K 线采集（按 symbol 批量）",
    response_model=CollectResponse,
)
async def daily_kline_trigger(body: CollectRequest, svc=Depends(get_daily_kline_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post(
    "/minute_kline", summary="分钟 K 线（实时查询入口）",
    response_model=CollectResponse,
)
async def minute_kline_trigger(body: CollectRequest, svc=Depends(get_minute_kline_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post(
    "/adj_factor", summary="复权因子采集（按 symbol 批量）",
    response_model=CollectResponse,
)
async def adj_factor_trigger(body: CollectRequest, svc=Depends(get_adj_factor_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post(
    "/suspend", summary="停复牌采集",
    response_model=CollectResponse,
)
async def suspend_trigger(body: CollectRequest, svc=Depends(get_suspend_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post(
    "/name_change", summary="股票曾用名采集",
    response_model=CollectResponse,
)
async def name_change_trigger(body: CollectRequest, svc=Depends(get_name_change_service)):
    return R.ok((await _run(svc, body)).model_dump())


__all__ = ["router"]
