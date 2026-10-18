"""tech routes — 技术面 5 个 service 对应 5 个 route

URL 风格：POST /collect/tech/{service_name}
  - /collect/tech/daily_kline
  - /collect/tech/minute_kline
  - /collect/tech/adj_factor
  - /collect/tech/suspend
  - /collect/tech/name_change
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from shared.interface import _response as R
from contexts.collect.infrastructure.di.collect_service import (
    get_daily_kline_service,
    get_minute_kline_service,
    get_adj_factor_service,
    get_suspend_service,
    get_name_change_service,
)

router = APIRouter(prefix="/collect/tech", tags=["采集-技术面"])


class CollectBody(BaseModel):
    """采集请求体

    新格式：{"mode": "full" | "condition", "params": {...}}
    旧格式：{"params": {...}}    兼容：mode 默认为 condition
    """
    mode: str = "condition"
    params: dict = Field(default_factory=dict)


async def _run(svc, body: CollectBody):
    """统一执行：把 mode 合并进 params（让 RunLog.params 能被前端解析为采集模式）"""
    merged = {**body.params, "mode": body.mode}
    return R.ok((await svc.collect(merged)).to_dict())


@router.post("/daily_kline", summary="日 K 线采集（按 symbol 批量）")
async def daily_kline_trigger(body: CollectBody, svc=Depends(get_daily_kline_service)):
    return await _run(svc, body)


@router.post("/minute_kline", summary="分钟 K 线（实时查询入口）")
async def minute_kline_trigger(body: CollectBody, svc=Depends(get_minute_kline_service)):
    return await _run(svc, body)


@router.post("/adj_factor", summary="复权因子采集（按 symbol 批量）")
async def adj_factor_trigger(body: CollectBody, svc=Depends(get_adj_factor_service)):
    return await _run(svc, body)


@router.post("/suspend", summary="停复牌采集")
async def suspend_trigger(body: CollectBody, svc=Depends(get_suspend_service)):
    return await _run(svc, body)


@router.post("/name_change", summary="股票曾用名采集")
async def name_change_trigger(body: CollectBody, svc=Depends(get_name_change_service)):
    return await _run(svc, body)


__all__ = ["router"]
