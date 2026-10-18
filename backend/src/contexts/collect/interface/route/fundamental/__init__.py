"""fundamental routes — 基本面 12 个 service 对应 12 个 route（含 4 个概念 + 1 个股票基本信息）

URL 风格：POST /collect/fundamental/{service_name}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from shared.interface import _response as R
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


@router.post("/daily_basic", summary="每日估值采集")
async def daily_basic_trigger(body: CollectBody, svc=Depends(get_daily_basic_service)):
    return await _run(svc, body)


@router.post("/fin_income", summary="利润表采集（按 symbol 批量）")
async def fin_income_trigger(body: CollectBody, svc=Depends(get_fin_income_service)):
    return await _run(svc, body)


@router.post("/top10_holders", summary="前 10 大股东采集（按 symbol 批量）")
async def top10_holders_trigger(body: CollectBody, svc=Depends(get_top10_holders_service)):
    return await _run(svc, body)


@router.post("/top10_floatholders", summary="前 10 大流通股东采集（按 symbol 批量）")
async def top10_floatholders_trigger(body: CollectBody, svc=Depends(get_top10_float_holders_service)):
    return await _run(svc, body)


@router.post("/dividend", summary="分红送股采集（按 symbol 批量）")
async def dividend_trigger(body: CollectBody, svc=Depends(get_dividend_service)):
    return await _run(svc, body)


@router.post("/stock_basic", summary="股票基本信息采集")
async def stock_basic_trigger(body: CollectBody, svc=Depends(get_stock_basic_service)):
    return await _run(svc, body)


@router.post("/stock_concepts", summary="股票所属概念采集（按 symbol 批量）")
async def stock_concepts_trigger(body: CollectBody, svc=Depends(get_stock_concepts_service)):
    return await _run(svc, body)


@router.post("/concept_list", summary="概念清单采集")
async def concept_list_trigger(body: CollectBody, svc=Depends(get_concept_list_service)):
    return await _run(svc, body)


@router.post("/concept_members", summary="概念成分股采集（按 index_code 批量）")
async def concept_members_trigger(body: CollectBody, svc=Depends(get_concept_members_service)):
    return await _run(svc, body)


@router.post("/concept_index_daily", summary="概念指数日 K 采集（按 index_code 批量）")
async def concept_index_daily_trigger(body: CollectBody, svc=Depends(get_concept_index_daily_service)):
    return await _run(svc, body)


@router.post("/concept_minute", summary="概念实时分时采集")
async def concept_minute_trigger(body: CollectBody, svc=Depends(get_concept_minute_service)):
    return await _run(svc, body)


@router.post("/concept_snapshot", summary="概念行情快照采集")
async def concept_snapshot_trigger(body: CollectBody, svc=Depends(get_concept_snapshot_service)):
    return await _run(svc, body)


__all__ = ["router"]
