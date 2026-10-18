"""capital routes — 资金面 9 个 service 对应 9 个 route

URL 风格：POST /collect/capital/{service_name}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from shared.interface import _response as R
from contexts.collect.infrastructure.di.collect_service import (
    get_moneyflow_service,
    get_moneyflow_hsgt_service,
    get_top_list_service,
    get_top_inst_service,
    get_block_trade_service,
    get_margin_service,
    get_hsgt_top10_service,
    get_limit_list_service,
    get_holder_number_service,
)

router = APIRouter(prefix="/collect/capital", tags=["采集-资金面"])


class CollectBody(BaseModel):
    """采集请求体

    新格式：{"mode": "full" | "condition", "params": {...}}
    旧格式：{"params": {...}}    兼容：mode 默认为 condition
    """
    mode: str = "condition"  # 'full' = 全量 / 'condition' = 条件
    params: dict = Field(default_factory=dict)


async def _run(svc, body: CollectBody):
    """统一执行：把 mode 合并进 params（让 RunLog.params 后续能被前端解析）"""
    merged = {**body.params, "mode": body.mode}
    return R.ok((await svc.collect(merged)).to_dict())


@router.post("/moneyflow", summary="个股资金流向采集")
async def moneyflow_trigger(body: CollectBody, svc=Depends(get_moneyflow_service)):
    return await _run(svc, body)


@router.post("/moneyflow_hsgt", summary="沪深港通资金流向采集")
async def moneyflow_hsgt_trigger(body: CollectBody, svc=Depends(get_moneyflow_hsgt_service)):
    return await _run(svc, body)


@router.post("/top_list", summary="龙虎榜每日明细采集")
async def top_list_trigger(body: CollectBody, svc=Depends(get_top_list_service)):
    return await _run(svc, body)


@router.post("/top_inst", summary="龙虎榜机构明细采集")
async def top_inst_trigger(body: CollectBody, svc=Depends(get_top_inst_service)):
    return await _run(svc, body)


@router.post("/block_trade", summary="大宗交易采集")
async def block_trade_trigger(body: CollectBody, svc=Depends(get_block_trade_service)):
    return await _run(svc, body)


@router.post("/margin", summary="融资融券明细采集")
async def margin_trigger(body: CollectBody, svc=Depends(get_margin_service)):
    return await _run(svc, body)


@router.post("/hsgt_top10", summary="沪深港通前 10 持仓采集")
async def hsgt_top10_trigger(body: CollectBody, svc=Depends(get_hsgt_top10_service)):
    return await _run(svc, body)


@router.post("/limit_list_d", summary="涨跌停板采集")
async def limit_list_d_trigger(body: CollectBody, svc=Depends(get_limit_list_service)):
    return await _run(svc, body)


@router.post("/holder_number", summary="股东户数采集（按 symbol 批量）")
async def holder_number_trigger(body: CollectBody, svc=Depends(get_holder_number_service)):
    return await _run(svc, body)


__all__ = ["router"]
