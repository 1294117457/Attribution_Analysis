"""capital routes — 资金面 9 个 service 对应 9 个 route

Phase3：内联 CollectBody → DTO CollectRequest / CollectResponse
Phase3 v3（2026-10-19）：所有 INCREMENTAL service 走 TaskRunner 派发
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from shared.interface import _response as R
from contexts.collect.interface.dto.request.collect import CollectRequest
from contexts.collect.interface.dto.response.collect import ApiResponse, CollectResponse
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
    """统一执行：触发后台采集任务

    Phase 3 v3：所有 capital service 均为 INCREMENTAL，collect() 返回 {log_id, status}。
    """
    result = await svc.collect(body.params)
    if isinstance(result, dict):
        return CollectResponse(
            log_id=result.get("log_id"),
            status=result.get("status"),
            message=f"采集任务已派发，前端请用 log_id 轮询 /collect/logs/{result.get('log_id')}",
        )
    # 兼容：旧 service 返回 CollectResult（保留 fallback）
    return CollectResponse(
        total=result.total, success=result.success, fail=result.fail,
        skip=result.skip, saved=result.saved, message=result.message,
    )


@router.post("/moneyflow", response_model=ApiResponse[CollectResponse], summary="个股资金流向")
async def moneyflow_trigger(body: CollectRequest, svc=Depends(get_moneyflow_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/moneyflow_hsgt", response_model=ApiResponse[CollectResponse], summary="沪深港通资金流向")
async def moneyflow_hsgt_trigger(body: CollectRequest, svc=Depends(get_moneyflow_hsgt_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/top_list", response_model=ApiResponse[CollectResponse], summary="龙虎榜每日明细")
async def top_list_trigger(body: CollectRequest, svc=Depends(get_top_list_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/top_inst", response_model=ApiResponse[CollectResponse], summary="龙虎榜机构明细")
async def top_inst_trigger(body: CollectRequest, svc=Depends(get_top_inst_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/block_trade", response_model=ApiResponse[CollectResponse], summary="大宗交易")
async def block_trade_trigger(body: CollectRequest, svc=Depends(get_block_trade_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/margin", response_model=ApiResponse[CollectResponse], summary="融资融券明细")
async def margin_trigger(body: CollectRequest, svc=Depends(get_margin_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/hsgt_top10", response_model=ApiResponse[CollectResponse], summary="沪深港通前 10 持仓")
async def hsgt_top10_trigger(body: CollectRequest, svc=Depends(get_hsgt_top10_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/limit_list_d", response_model=ApiResponse[CollectResponse], summary="每日涨跌停板")
async def limit_list_trigger(body: CollectRequest, svc=Depends(get_limit_list_service)):
    return R.ok((await _run(svc, body)).model_dump())


@router.post("/holder_number", response_model=ApiResponse[CollectResponse], summary="股东户数")
async def holder_number_trigger(body: CollectRequest, svc=Depends(get_holder_number_service)):
    return R.ok((await _run(svc, body)).model_dump())


__all__ = ["router"]