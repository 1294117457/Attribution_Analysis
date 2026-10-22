"""tech routes — 技术面 5 个 service 对应 5 个 route

Phase3：内联 CollectBody → DTO CollectRequest / CollectResponse
Phase3 v3（2026-10-19）：所有 service 统一走 TaskRunner 派发
  - collect() 返回 {"log_id", "status"}（INCREMENTAL/FULL_REFRESH）
  - REALTIME service（minute_kline）保留 CollectResult 兼容
Phase5 v5（2026-10-21）：service 入参校验失败 → InvalidParams → HTTP 400
Phase5 v6（2026-10-21）：daily_kline 拆成独立模块 route/tech/daily.py
  - 强类型请求 DTO（DailyCollectRequest：start_date / end_date 必填）
  - 响应不再返回 log_id（v5 协议：前端按 service_name 查日志列表）

URL 路径保持 stable：
    /daily_kline  /minute_kline
    （daily_kline 见 daily.py，其余见本文件）
（注：service_name 与 fatcher_type 保持稳定；类名 DailyService/MinuteService
       + 依赖注入工厂 get_daily_service/get_minute_service 已重命名为简短语义版）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from shared.interface import _response as R
from contexts.collect.application.service.base import InvalidParams
from contexts.collect.interface.dto.request.collect import CollectRequest
from contexts.collect.interface.dto.response.collect import ApiResponse, CollectResponse
from contexts.collect.infrastructure.di.collect_service import (
    get_minute_service,
    get_adj_factor_service,
    get_suspend_service,
    get_name_change_service,
)
from contexts.collect.interface.route.tech.daily import router as daily_router

router = APIRouter(prefix="/collect/tech", tags=["采集-技术面"])

# 日 K 线单独成模块（强类型请求 DTO + v5 自管协议响应）
router.include_router(daily_router)


async def _run(svc, body: CollectRequest) -> CollectResponse:
    """统一执行：触发后台采集任务

    Phase 2 统一返回 dict（INCREMENTAL/FULL_REFRESH）：
        {log_id, status}

    REALTIME service（minute_kline）暂保留 CollectResult 兼容。

    ★ service.collect() 的入参校验抛 InvalidParams（如 daily_kline 的
      时间范围必传），这里统一转 HTTP 400 —— 请求不合法当场返回，
      不派发后台任务、不写 collect_logs。
    """
    try:
        result = await svc.collect(body.params)
    except InvalidParams as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

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
    "/minute_kline", summary="分钟 K 线（实时查询入口）",
    response_model=ApiResponse[CollectResponse],
)
async def minute_trigger(body: CollectRequest, svc=Depends(get_minute_service)):
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
