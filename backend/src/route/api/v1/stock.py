"""股票 CRUD 路由（业务模块：stock-info/）

仅保留股票基本信息 CRUD。面板/分页查询已迁移至 /stock-panel/（panel.py）。
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from application.service import CollectManageService, StockInfoService
from infrastructure.config.di import (
    get_collect_manage_service,
    get_stock_info_service,
)
from route.api import _response as R
from route.dto.request.stock import StockUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["股票"])

# ── 依赖注入工厂 ──
get_stock_service = get_stock_info_service


@router.get("/meta", summary="股票枚举值")
async def get_stock_meta(
    service: StockInfoService = Depends(get_stock_service),
):
    """获取行业 / 市场 / 交易所枚举值（用于前端筛选下拉）"""
    meta = await service.get_meta()
    return R.ok(meta.model_dump())


@router.get("/{symbol}", summary="股票详情")
async def get_stock(
    symbol: str,
    service: StockInfoService = Depends(get_stock_service),
):
    """获取股票详细信息"""
    stock = await service.get_stock(symbol)
    return R.ok(stock.model_dump())


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
    service: StockInfoService = Depends(get_stock_service),
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
    collect: CollectManageService = Depends(get_collect_manage_service),
):
    """全量同步 A股股票基本信息（采集接口 stock_basic.collect_one）"""
    result = await collect.run_one("stock_basic", "all", {"list_status": list_status})
    return R.created(result.data)


@router.patch("/{symbol}", summary="部分更新股票")
async def update_stock(
    symbol: str,
    request: StockUpdateRequest,
    service: StockInfoService = Depends(get_stock_service),
):
    """部分更新股票信息"""
    stock = await service.update_stock(symbol, request)
    return R.ok(stock.model_dump())


@router.delete("/{symbol}", summary="删除股票")
async def delete_stock(
    symbol: str,
    service: StockInfoService = Depends(get_stock_service),
):
    """删除股票"""
    response = await service.delete_stock(symbol)
    return R.ok(response.model_dump())


@router.post("/sync-daily-basic", summary="同步日频估值指标")
async def sync_daily_basic(
    trade_date: Optional[str] = Query(
        None, description="YYYYMMDD 格式，不传默认取最近交易日",
    ),
    days: int = Query(1, ge=1, le=30, description="往回拉取天数（默认1天）"),
    collect: CollectManageService = Depends(get_collect_manage_service),
):
    """同步全市场日频估值（采集接口 daily_basic.collect_one，逐日）"""
    dates = await collect.handler("daily_basic").list_units(
        {"trade_date": trade_date, "days": days},
    )
    total_synced = 0
    synced_dates: list[str] = []
    for td in dates:
        result = await collect.run_one("daily_basic", td)
        if result.skipped:
            continue
        total_synced += result.saved_count
        synced_dates.append(td)
    return R.ok({
        "synced_count": total_synced,
        "dates": synced_dates,
        "message": f"成功同步 {total_synced} 条日频估值数据",
    })
