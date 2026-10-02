"""股票 API 路由

⚠️ 历史说明：
    旧版 GET / （分页 + 4 表快照 + 池信息）已迁移至
    application/panel_service.py::StockPanelAppService +
    route/api/v1/panel.py::GET /api/v1/stock-panel/。

    本文件保留 GET / 作为**向后兼容薄包装**，内部委托给
    StockPanelAppService.query_panels，便于旧调用方（如 Dashboard）
    无需修改即可继续工作。

新代码请使用 GET /api/v1/stock-panel/。
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from route.dto.response.panel import StockPanelQueryRequest
from route.dto.request.stock import StockUpdateRequest
from application.service.collect_app_service import CollectAppService
from application.service.stock_app_service import StockAppService
from infrastructure.config.di import (
    get_panel_app_service,
    get_stock_app_service,
)
from application.service.panel_app_service import StockPanelAppService
from route.api import _response as R

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["股票"])


# ── 依赖注入工厂（来自 infrastructure.config.di） ──────────────────────────
get_stock_service = get_stock_app_service
get_panel_service = get_panel_app_service


# ── 查询路由 ──────────────────────────────────────────────

@router.get(
    "/",
    summary="股票列表（向后兼容，已迁移至 /stock-panel/）",
    deprecated=True,
)
async def query_stocks(
    q: Optional[str] = Query(None, description="代码 / 名称模糊搜索"),
    industry: Optional[str] = Query(None, description="行业"),
    market: Optional[str] = Query(None, description="市场类型"),
    exchange: Optional[str] = Query(None, description="交易所 SSE/SZSE/BSE"),
    is_hs: Optional[str] = Query(None, description="沪深港通 N/H/S"),
    list_status: Optional[str] = Query("L", description="上市状态 L/D/P/全部"),
    exclude_st: Optional[bool] = Query(None, description="排除ST股票"),
    min_total_mv: Optional[float] = Query(None, ge=0, description="最低总市值(万元)"),
    with_pools: bool = Query(False, description="是否附带所属操作池（避免 N+1 反向查询）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=500, description="每页条数"),
    panel_service: StockPanelAppService = Depends(get_panel_service),
):
    """⚠️ 已废弃：迁移至 GET /api/v1/stock-panel/

    本路由保留为**向后兼容薄包装**，内部委托 StockPanelAppService.query_panels。
    新代码请直接使用 /api/v1/stock-panel/，字段与响应完全一致。
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
    response = await panel_service.query_panels(request)
    return R.ok(response.model_dump())


@router.get("/meta", summary="股票枚举值")
async def get_stock_meta(
    service: StockAppService = Depends(get_stock_service),
):
    """获取行业 / 市场 / 交易所枚举值（用于前端筛选下拉）"""
    meta = await service.get_meta()
    return R.ok(meta.model_dump())


@router.get("/{symbol}", summary="股票详情")
async def get_stock(
    symbol: str,
    service: StockAppService = Depends(get_stock_service),
):
    """获取股票详细信息"""
    stock = await service.get_stock(symbol)
    return R.ok(stock.model_dump())


# ── 写入路由 ──────────────────────────────────────────────

@router.post(
    "/",
    summary="新增/更新股票",
    status_code=status.HTTP_201_CREATED,
)
async def upsert_stock(
    symbol: str = Query(..., description="股票代码"),
    name: str = Query(..., description="股票名称"),
    industry: Optional[str] = Query(None, description="所属行业"),
    market: Optional[str] = Query(None, description="所属市场"),
    service: StockAppService = Depends(get_stock_service),
):
    """新增或更新股票信息"""
    stock = await service.upsert_stock(symbol, name, industry, market)
    return R.created(stock.model_dump())


@router.post(
    "/sync",
    summary="同步股票基本信息",
    status_code=status.HTTP_201_CREATED,
)
async def sync_stocks(
    list_status: str = Query("L", description="上市状态 L/D/P"),
):
    """全量同步 A股股票基本信息（采集接口 stock_basic.collect_one）

    同步完成后，前端可调用 /stocks/meta 刷新枚举值。
    """
    result = await CollectAppService().run_one("stock_basic", "all", {"list_status": list_status})
    return R.created(result.data)


@router.patch("/{symbol}", summary="部分更新股票")
async def update_stock(
    symbol: str,
    request: StockUpdateRequest,
    service: StockAppService = Depends(get_stock_service),
):
    """部分更新股票信息"""
    stock = await service.update_stock(symbol, request)
    return R.ok(stock.model_dump())


# ── 删除路由 ──────────────────────────────────────────────

@router.delete("/{symbol}", summary="删除股票")
async def delete_stock(
    symbol: str,
    service: StockAppService = Depends(get_stock_service),
):
    """删除股票"""
    response = await service.delete_stock(symbol)
    return R.ok(response.model_dump())


# ── 日频估值同步 ──────────────────────────────────────────

@router.post("/sync-daily-basic", summary="同步日频估值指标")
async def sync_daily_basic(
    trade_date: Optional[str] = Query(
        None,
        description="YYYYMMDD 格式，不传默认取最近交易日",
    ),
    days: int = Query(1, ge=1, le=30, description="往回拉取天数（默认1天）"),
):
    """同步全市场日频估值（采集接口 daily_basic.collect_one，逐日）

    用于填充 fin_daily_basics 表，使股票列表能展示最新价、总市值、PE 等。
    """
    svc = CollectAppService()
    dates = await svc.handler("daily_basic").list_units({"trade_date": trade_date, "days": days})

    total_synced = 0
    synced_dates: list[str] = []
    for td in dates:
        result = await svc.run_one("daily_basic", td)
        if result.skipped:
            continue
        total_synced += result.saved_count
        synced_dates.append(td)

    return R.ok({
        "synced_count": total_synced,
        "dates": synced_dates,
        "message": f"成功同步 {total_synced} 条日频估值数据",
    })
