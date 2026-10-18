"""概念路由 — 概念大盘 + K线 /api/v1/concepts/*

包含：
- GET /concept-board            概念大盘（涨/跌 Top + 全量分页）
- GET /concept-board/members    概念成分股列表
- GET /{index_code}/kline       概念指数日 K + 实时快照
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from contexts.concept.application.service.concept_board_service import ConceptBoardService
from contexts.concept.interface.dto.request.concept_board import (
    ConceptBoardQueryRequest,
    ConceptMembersQueryRequest,
)
from contexts.concept.infrastructure.di import get_concept_board_service
from shared.interface import _response as R

router = APIRouter(prefix="/concepts", tags=["概念"])


@router.get(
    "/concept-board",
    response_model=None,
    summary="概念大盘（涨/跌 Top + 全量分页）",
)
async def get_concept_board(
    type_filter: str = Query("all", description="概念类型筛选（all/industry/theme/...）"),
    sort_by: str = Query("pct_change", description="排序键 pct_change/stock_count/name"),
    order: str = Query("desc", description="排序方向 asc/desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    app: ConceptBoardService = Depends(get_concept_board_service),
):
    """概念大盘：返回分页概念 + 实时涨幅。"""
    req = ConceptBoardQueryRequest(
        type_filter=type_filter, sort_by=sort_by, order=order,
        page=page, page_size=page_size,
    )
    result = await app.query_board(req)
    return R.ok(result)


@router.get(
    "/concept-board/members",
    response_model=None,
    summary="概念成分股列表（带最新价/涨跌幅/换手 + 池）",
)
async def get_concept_board_members(
    concept_id: int = Query(..., description="概念 id"),
    sort_by: str = Query("pct_change"),
    order: str = Query("desc"),
    with_pools: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    app: ConceptBoardService = Depends(get_concept_board_service),
):
    """概念成分股：join stock_infos + fin_daily_basics 最新一行。"""
    req = ConceptMembersQueryRequest(
        concept_id=concept_id, sort_by=sort_by, order=order,
        with_pools=with_pools, page=page, page_size=page_size,
    )
    result = await app.query_board_members(req)
    return R.ok(result)


@router.get(
    "/{index_code}/kline",
    response_model=None,
    summary="概念指数日 K + 实时快照",
)
async def get_concept_kline(
    index_code: str,
    days: int = Query(250, ge=10, le=1500, description="最多取多少根 K 线"),
    start_date: Optional[date] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期 YYYY-MM-DD"),
    app: ConceptBoardService = Depends(get_concept_board_service),
):
    """概念指数日 K（concept_index_ths）+ 实时快照

    实时不可用时降级为最近一日收盘。
    """
    result = await app.get_kline(
        index_code=index_code,
        start_date=start_date, end_date=end_date, days=days,
    )
    return R.ok(result)
