"""K线 API 路由（业务模块：stock-info/）"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from contexts.market.application.service.stock_info_service import StockInfoService
from contexts.market.infrastructure.di import get_stock_info_service
from shared.interface import _response as R
from contexts.market.interface.dto.request.kline import (
    KlineCollectRequest,
    KlineDeleteRequest,
    KlineQueryRequest,
)
from contexts.market.interface.dto.response.kline import KlineCollectResponse

router = APIRouter(prefix="/klines", tags=["K线"])


# ── 查询路由 ──────────────────────────────────────────────

@router.get("/{symbol}", summary="查询K线")
async def get_klines(
    symbol: str,
    start_date: Optional[date] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(365, ge=1, le=3650, description="最大返回条数"),
    order_desc: bool = Query(True, description="是否按日期降序"),
    service: StockInfoService = Depends(get_stock_info_service),
):
    """查询股票的K线数据"""
    request = KlineQueryRequest(
        symbol=symbol, start_date=start_date, end_date=end_date,
        limit=limit, order_desc=order_desc,
    )
    response = await service.get_klines(request)
    return R.ok(response.model_dump())


@router.get("/{symbol}/stats", summary="K线统计")
async def get_kline_stats(
    symbol: str,
    service: StockInfoService = Depends(get_stock_info_service),
):
    """获取K线统计信息（条数、日期范围、最新收盘价等）"""
    stats = await service.get_stats(symbol)
    return R.ok(stats.model_dump())


@router.get("/{symbol}/{trade_date}", summary="查询单条K线")
async def get_kline_by_date(
    symbol: str,
    trade_date: date,
    service: StockInfoService = Depends(get_stock_info_service),
):
    """根据日期查询单条K线"""
    kline = await service.get_kline_by_date(symbol, trade_date)
    return R.ok(kline.model_dump())


# ── 采集路由 ──────────────────────────────────────────────

@router.post(
    "/collect",
    summary="采集K线",
    status_code=status.HTTP_201_CREATED,
)
async def collect_kline(
    request: KlineCollectRequest,
    service: StockInfoService = Depends(get_stock_info_service),
):
    """采集并存储K线数据（直接调 stock_info_service.collect）"""
    result = await service.collect(request)
    return R.created(result.model_dump())


@router.post(
    "/collect/batch",
    summary="批量采集K线",
    status_code=status.HTTP_201_CREATED,
)
async def collect_batch(
    symbols: list[str] = Query(..., description="股票代码列表"),
    days: int = Query(30, ge=1, le=3650, description="回溯天数"),
    service: StockInfoService = Depends(get_stock_info_service),
):
    """批量采集多只股票的K线数据"""
    results: dict[str, dict] = {}
    for symbol in symbols:
        try:
            req = KlineCollectRequest(
                symbol=symbol, days=days,
                start_date=None, end_date=None,
            )
            results[symbol] = (await service.collect(req)).model_dump()
        except Exception as e:
            results[symbol] = KlineCollectResponse(
                symbol=symbol, name="", saved_count=-1, total_count=0, message=str(e),
            ).model_dump()
    return R.created(results)


# ── 删除路由 ──────────────────────────────────────────────

@router.delete("/{symbol}", summary="删除全部K线")
async def delete_all_klines(
    symbol: str,
    service: StockInfoService = Depends(get_stock_info_service),
):
    """删除指定股票的所有K线数据"""
    request = KlineDeleteRequest(symbol=symbol)
    response = await service.delete(request)
    return R.ok(response.model_dump())


@router.delete("/{symbol}/{trade_date}", summary="删除单条K线")
async def delete_kline(
    symbol: str,
    trade_date: date,
    service: StockInfoService = Depends(get_stock_info_service),
):
    """删除指定日期的K线数据"""
    request = KlineDeleteRequest(symbol=symbol, trade_date=trade_date)
    response = await service.delete(request)
    return R.ok(response.model_dump())
