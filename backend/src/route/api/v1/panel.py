"""StockPanel 面板列表路由

GET /api/v1/stock-panel/  分页 + 多维筛选 + 4 表快照 + 池信息

替代原 GET /api/v1/stocks/ 的富字段查询职责（list_with_kline_stats_paginated）。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.panel import StockPanelListVO, StockPanelQueryRequest
from application.panel_service import StockPanelAppService
from infrastructure.database.connection import get_db
from route.schemas import response as R

router = APIRouter(prefix="/stock-panel", tags=["面板"])


def get_panel_service(
    db: AsyncSession = Depends(get_db),
) -> StockPanelAppService:
    return StockPanelAppService(session=db)


@router.get(
    "/",
    summary="股票面板列表（分页 + 多维筛选 + 4 表快照 + 池信息）",
)
async def query_panels(
    q: Optional[str] = Query(None, description="代码 / 名称 / 拼音 模糊搜索"),
    industry: Optional[str] = Query(None, description="行业"),
    market: Optional[str] = Query(None, description="市场类型"),
    exchange: Optional[str] = Query(None, description="交易所 SSE/SZSE/BSE"),
    is_hs: Optional[str] = Query(None, description="沪深港通 N/H/S"),
    list_status: Optional[str] = Query("L", description="上市状态 L/D/P/全部"),
    exclude_st: Optional[bool] = Query(None, description="排除 ST / 仅 ST"),
    min_total_mv: Optional[float] = Query(None, ge=0, description="最低总市值(万元)"),
    with_pools: bool = Query(
        False, description="是否附带所属操作池（避免 N+1 反向查询）",
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=500, description="每页条数"),
    service: StockPanelAppService = Depends(get_panel_service),
):
    """分页 + 多维筛选 + K线统计 + 最新估值的股票列表（StockPanel.vue 主列表用）

    若 with_pools=true，响应 items[].pools 字段会附带每只股票所属的操作池，
    无需前端逐条调用 /pools/by-symbol/{symbol}，避免 N+1 问题。

    字段命名与前端 PaginatedResponse<StockInfo> 1:1 对齐：
    items / total / page / page_size / pages
    """
    request = StockPanelQueryRequest(
        q=q,
        industry=industry,
        market=market,
        exchange=exchange,
        is_hs=is_hs,
        list_status=list_status,
        exclude_st=exclude_st,
        min_total_mv=min_total_mv,
        with_pools=with_pools,
        page=page,
        page_size=page_size,
    )
    response = await service.query_panels(request)
    return R.ok(response.model_dump())