"""日 K 线采集路由（tech facet → daily_kline）

URL 保持 stable：POST /collect/tech/daily_kline

v5 自管协议（2026-10-21）：
    - service.collect() 只做「校验 + 派发后台任务」，立即返回 {"status": "pending"}
    - 日志全生命周期在 service.run_collect() 内部，log_id 不透出任何边界
      → 前端按 service_name 轮询 GET /collect/logs/daily_kline
    - 入参用强类型 DTO（DailyCollectRequest）：
      缺字段 / 日期格式错 / start > end → FastAPI 422
      时间跨度过大（service 侧业务规则）→ 400
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from shared.interface import _response as R
from contexts.collect.application.service.base import InvalidParams
from contexts.collect.interface.dto.request.daily import DailyCollectRequest
from contexts.collect.interface.dto.response.collect import ApiResponse, CollectResponse
from contexts.collect.infrastructure.di.collect_service import get_daily_service

# 前缀 / tags 由父级 tech/__init__.py 的 router 继承（include_router）
router = APIRouter()

#: service_name —— 前端轮询日志列表用的查询键（与 META.name 一致）
SERVICE_NAME = "daily_kline"


@router.post(
    "/daily_kline",
    summary="日 K 线采集（全市场，时间范围必传）",
    response_model=ApiResponse[CollectResponse],
)
async def daily_trigger(body: DailyCollectRequest, svc=Depends(get_daily_service)):
    """触发日 K 线采集

    ★ 只透传 start_date / end_date：symbol 固定由 service 从 stock_basic 读取，
      前端传的其它字段不会进入 collect_logs.params。
    """
    try:
        result = await svc.collect(body.to_service_params())
    except InvalidParams as e:
        # service 侧业务校验失败（如时间跨度过大）→ 400
        raise HTTPException(status_code=400, detail=str(e)) from e

    status = result.get("status", "pending") if isinstance(result, dict) else "pending"
    return R.ok(
        CollectResponse(
            log_id=None,  # v5：log_id 不透出，前端按 service_name 查日志
            status=status,
            message=(
                "采集任务已派发，请按 service_name=daily_kline "
                "轮询 GET /collect/logs/daily_kline 查看进度"
            ),
        ).model_dump()
    )


__all__ = ["router"]
