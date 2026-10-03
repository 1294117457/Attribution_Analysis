"""K线 API 路由（业务模块：stock-info/）"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from application.service import (
    CollectManageService,
    StockInfoService,
    StockInfoService as KLineServiceAlias,  # 向后兼容的别名
)
from infrastructure.config.di import (
    get_collect_manage_service,
    get_stock_info_service,
)
from route.api import _response as R
from route.dto.request.kline import (
    KlineCollectRequest,
    KlineDeleteRequest,
    KlineQueryRequest,
)
from route.dto.response.kline import KlineCollectResponse

router = APIRouter(prefix="/klines", tags=["K线"])


# ── 依赖注入工厂 ──────────────────────────────────────────
get_kline_service = get_stock_info_service


# ── 查询路由 ──────────────────────────────────────────────

@router.get("/{symbol}", summary="查询K线")
async def get_klines(
    symbol: str,
    start_date: Optional[date] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(365, ge=1, le=3650, description="最大返回条数"),
    order_desc: bool = Query(True, description="是否按日期降序"),
    service: StockInfoService = Depends(get_kline_service),
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
    service: StockInfoService = Depends(get_kline_service),
):
    """获取K线统计信息（条数、日期范围、最新收盘价等）"""
    stats = await service.get_stats(symbol)
    return R.ok(stats.model_dump())


@router.get("/{symbol}/{trade_date}", summary="查询单条K线")
async def get_kline_by_date(
    symbol: str,
    trade_date: date,
    service: StockInfoService = Depends(get_kline_service),
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
    collect: CollectManageService = Depends(get_collect_manage_service),
):
    """采集并存储K线数据（采集接口 daily_kline.collect_one）"""
    result = await collect.run_one(
        "daily_kline", request.symbol,
        _kline_params(request.days, request.start_date, request.end_date),
    )
    return R.created(result.data)


@router.post(
    "/collect/batch",
    summary="批量采集K线",
    status_code=status.HTTP_201_CREATED,
)
async def collect_batch(
    symbols: list[str] = Query(..., description="股票代码列表"),
    days: int = Query(30, ge=1, le=3650, description="回溯天数"),
    collect: CollectManageService = Depends(get_collect_manage_service),
):
    """批量采集多只股票的K线数据

    大批量请用 POST /collect/tasks {"task_type": "daily_kline", "params": {"symbols": [...]}}
    """
    results: dict[str, dict] = {}
    for symbol in symbols:
        try:
            results[symbol] = (await collect.run_one(
                "daily_kline", symbol, _kline_params(days),
            )).data
        except Exception as e:
            results[symbol] = KlineCollectResponse(
                symbol=symbol, name="", saved_count=-1, total_count=0, message=str(e),
            ).model_dump()
    return R.created(results)


def _kline_params(days: int, start_date: Optional[date] = None, end_date: Optional[date] = None) -> dict:
    params: dict = {"days": days}
    if start_date and end_date:
        params.update(start_date=start_date, end_date=end_date)
    return params


# ── 删除路由 ──────────────────────────────────────────────

@router.delete("/{symbol}", summary="删除全部K线")
async def delete_all_klines(
    symbol: str,
    service: StockInfoService = Depends(get_kline_service),
):
    """删除指定股票的所有K线数据"""
    request = KlineDeleteRequest(symbol=symbol)
    response = await service.delete(request)
    return R.ok(response.model_dump())


@router.delete("/{symbol}/{trade_date}", summary="删除单条K线")
async def delete_kline(
    symbol: str,
    trade_date: date,
    service: StockInfoService = Depends(get_kline_service),
):
    """删除指定日期的K线数据"""
    request = KlineDeleteRequest(symbol=symbol, trade_date=trade_date)
    response = await service.delete(request)
    return R.ok(response.model_dump())
