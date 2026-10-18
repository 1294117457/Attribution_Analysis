"""股票 CRUD 路由（业务模块：stock-info/）

仅保留股票基本信息 CRUD。面板/分页查询已迁移至 /stock-panel/（panel.py）。
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from contexts.market.application.service.stock_info_service import StockInfoService
from contexts.market.infrastructure.di import get_stock_info_service
from shared.interface import _response as R
from contexts.market.interface.dto.request.stock import StockUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["股票"])

# ── 依赖注入工厂 ──


@router.get("/meta", summary="股票枚举值")
async def get_stock_meta(
    service: StockInfoService = Depends(get_stock_info_service),
):
    """获取行业 / 市场 / 交易所枚举值（用于前端筛选下拉）"""
    meta = await service.get_meta()
    return R.ok(meta.model_dump())


@router.get("/{symbol}", summary="股票详情")
async def get_stock(
    symbol: str,
    service: StockInfoService = Depends(get_stock_info_service),
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
    service: StockInfoService = Depends(get_stock_info_service),
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
    service: StockInfoService = Depends(get_stock_info_service),
):
    """全量同步 A股股票基本信息（直接调 stock_info_service.sync_stocks）"""
    result = await service.sync_stocks(list_status=list_status)
    return R.created(result.model_dump())


@router.patch("/{symbol}", summary="部分更新股票")
async def update_stock(
    symbol: str,
    request: StockUpdateRequest,
    service: StockInfoService = Depends(get_stock_info_service),
):
    """部分更新股票信息"""
    stock = await service.update_stock(symbol, request)
    return R.ok(stock.model_dump())


@router.delete("/{symbol}", summary="删除股票")
async def delete_stock(
    symbol: str,
    service: StockInfoService = Depends(get_stock_info_service),
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
    service: StockInfoService = Depends(get_stock_info_service),
):
    """同步全市场日频估值（直接调 stock_info_service 内 daily_basic）"""
    # 简化：单日
    if not trade_date:
        return R.ok({"synced_count": 0, "dates": [], "message": "请提供 trade_date（YYYYMMDD）"})
    from contexts.collect.application.service.fundamental.daily_basic_service import (
        DailyBasicService,
    )
    from datetime import date
    daily_basic = DailyBasicService()
    td = date(int(trade_date[:4]), int(trade_date[4:6]), int(trade_date[6:8]))
    result = await daily_basic.collect({"trade_date": td})
    return R.ok({
        "synced_count": result.saved,
        "dates": [trade_date],
        "message": result.message or f"成功同步 {result.saved} 条日频估值",
    })
