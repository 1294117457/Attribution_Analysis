"""K线 API 路由"""

from datetime import date
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.kline_service import KlineAppService
from application.dto.kline import (
    KlineCollectRequest,
    KlineDeleteRequest,
    KlineQueryRequest,
)
from domain.kline.schemas import KlineBO
from infrastructure.collectors.interfaces import FetcherProtocol
from infrastructure.config import get_settings
from infrastructure.database.connection import get_db
from route.schemas import response as R

router = APIRouter(prefix="/klines", tags=["K线"])


# ── 依赖注入工厂 ──────────────────────────────────────────

def get_kline_service(
    db: AsyncSession = Depends(get_db),
) -> KlineAppService:
    return KlineAppService(session=db)


@lru_cache
def get_kline_fetcher() -> FetcherProtocol:
    """K 线采集器依赖（单例）。

    根据 `COLLECTOR_SOURCE` 环境变量选择数据源适配器：
    - tushare  → TushareFetcher
    - akshare  → AkShareFetcher（默认）
    """
    source = (get_settings().COLLECTOR_SOURCE or "akshare").lower()
    if source == "tushare":
        from infrastructure.collectors.tushare import TushareFetcher
        return TushareFetcher(KlineBO)
    # 默认 / 显式 akshare
    from infrastructure.collectors.akshare import AkShareFetcher
    return AkShareFetcher(KlineBO)


# ── 查询路由 ──────────────────────────────────────────────

@router.get("/{symbol}", summary="查询K线")
async def get_klines(
    symbol: str,
    start_date: Optional[date] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(365, ge=1, le=3650, description="最大返回条数"),
    order_desc: bool = Query(True, description="是否按日期降序"),
    service: KlineAppService = Depends(get_kline_service),
):
    """查询股票的K线数据"""
    request = KlineQueryRequest(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        order_desc=order_desc,
    )
    response = await service.get_klines(request)
    return R.ok(response.model_dump())


@router.get("/{symbol}/stats", summary="K线统计")
async def get_kline_stats(
    symbol: str,
    service: KlineAppService = Depends(get_kline_service),
):
    """获取K线统计信息（条数、日期范围、最新收盘价等）"""
    stats = await service.get_stats(symbol)
    return R.ok(stats.model_dump())


@router.get("/{symbol}/{trade_date}", summary="查询单条K线")
async def get_kline_by_date(
    symbol: str,
    trade_date: date,
    service: KlineAppService = Depends(get_kline_service),
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
    service: KlineAppService = Depends(get_kline_service),
    fetcher: FetcherProtocol = Depends(get_kline_fetcher),
):
    """采集并存储K线数据"""
    response = await service.collect(request, fetcher)
    return R.created(response.model_dump())


@router.post(
    "/collect/batch",
    summary="批量采集K线",
    status_code=status.HTTP_201_CREATED,
)
async def collect_batch(
    symbols: list[str] = Query(..., description="股票代码列表"),
    days: int = Query(30, ge=1, le=3650, description="回溯天数"),
    service: KlineAppService = Depends(get_kline_service),
    fetcher: FetcherProtocol = Depends(get_kline_fetcher),
):
    """批量采集多只股票的K线数据"""
    results = await service.collect_batch(symbols, days, fetcher)
    return R.created({
        symbol: resp.model_dump() for symbol, resp in results.items()
    })


# ── 删除路由 ──────────────────────────────────────────────

@router.delete("/{symbol}", summary="删除全部K线")
async def delete_all_klines(
    symbol: str,
    service: KlineAppService = Depends(get_kline_service),
):
    """删除指定股票的所有K线数据"""
    request = KlineDeleteRequest(symbol=symbol)
    response = await service.delete(request)
    return R.ok(response.model_dump())


@router.delete("/{symbol}/{trade_date}", summary="删除单条K线")
async def delete_kline(
    symbol: str,
    trade_date: date,
    service: KlineAppService = Depends(get_kline_service),
):
    """删除指定日期的K线数据"""
    request = KlineDeleteRequest(symbol=symbol, trade_date=trade_date)
    response = await service.delete(request)
    return R.ok(response.model_dump())
