"""capital routes — 资金面 9 个 service 对应 9 个 route

Phase3：内联 CollectBody → DTO CollectRequest / CollectResponse
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from shared.interface import _response as R
from contexts.collect.interface.dto.request.collect import CollectRequest
from contexts.collect.interface.dto.response.collect import CollectResponse
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


async def _run(svc, body: CollectRequest) -> CollectResponse:
    result = await svc.collect(body.params)
    return CollectResponse(
        total=result.total, success=result.success, fail=result.fail,
        skip=result.skip, saved=result.saved, message=result.message,
    )


@router.post("/moneyflow", response_model=CollectResponse, summary="个股资金流向")
async def moneyflow_trigger(body: CollectRequest, svc=Depends(get_moneyflow_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/moneyflow_hsgt", response_model=CollectResponse, summary="沪深港通资金流向")
async def moneyflow_hsgt_trigger(body: CollectRequest, svc=Depends(get_moneyflow_hsgt_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/top_list", response_model=CollectResponse, summary="龙虎榜每日明细")
async def top_list_trigger(body: CollectRequest, svc=Depends(get_top_list_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/top_inst", response_model=CollectResponse, summary="龙虎榜机构明细")
async def top_inst_trigger(body: CollectRequest, svc=Depends(get_top_inst_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/block_trade", response_model=CollectResponse, summary="大宗交易")
async def block_trade_trigger(body: CollectRequest, svc=Depends(get_block_trade_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/margin", response_model=CollectResponse, summary="融资融券明细")
async def margin_trigger(body: CollectRequest, svc=Depends(get_margin_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/hsgt_top10", response_model=CollectResponse, summary="沪深港通前 10 持仓")
async def hsgt_top10_trigger(body: CollectRequest, svc=Depends(get_hsgt_top10_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/limit_list_d", response_model=CollectResponse, summary="每日涨跌停板")
async def limit_list_trigger(body: CollectRequest, svc=Depends(get_limit_list_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/holder_number", response_model=CollectResponse, summary="股东户数")
async def holder_number_trigger(body: CollectRequest, svc=Depends(get_holder_number_service)):
    return R.ok((await _run(svc, body)).model_dump())


__all__ = ["router"]
