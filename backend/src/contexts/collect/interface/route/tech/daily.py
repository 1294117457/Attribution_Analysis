from __future__ import annotations

from fastapi import APIRouter, Depends

from shared.interface import _response as R
from contexts.collect.interface.dto.request.daily import DailyCollectRequest
from contexts.collect.interface.dto.response.collect import ApiResponse
from contexts.collect.infrastructure.di.collect_service import get_daily_service

# 前缀 / tags 由父级 tech/__init__.py 的 router 继承（include_router）
router = APIRouter()


@router.post(
    "/daily",
    summary="日 K 线采集（时间范围全市场，可选指定 ts_code 只采单只）",
    response_model=ApiResponse[None],
)
async def daily_trigger(body: DailyCollectRequest, svc=Depends(get_daily_service)):
    """派发日 K 线采集任务，立即返回（进度查 collect_logs）"""
    await svc.collect(body)
    return R.ok(message="采集任务派发成功")


__all__ = ["router"]