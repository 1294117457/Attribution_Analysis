"""分钟 K 线 API 路由（纯透传，不落库）

前端请求 → pytdx 实时拉取 → 直接返回 JSON
"""

from functools import lru_cache

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from infrastructure.collectors.pytdx.fetcher import PytdxFetcher
from route.schemas import response as R

router = APIRouter(prefix="/minute-klines", tags=["分钟K线"])


@lru_cache
def get_pytdx_fetcher() -> PytdxFetcher:
    return PytdxFetcher()


class MinuteKlineItem(BaseModel):
    datetime: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float


@router.get("/{symbol}", summary="实时获取分钟K线")
async def get_minute_klines(
    symbol: str,
    interval: str = Query("5min", description="周期: 1min/5min/15min/30min/60min"),
    count: int = Query(200, ge=1, le=1200, description="获取K线数量"),
    fetcher: PytdxFetcher = Depends(get_pytdx_fetcher),
):
    """实时从通达信拉取分钟 K 线，不存储"""
    try:
        bos = await fetcher.fetch_minute_klines(
            symbol=symbol,
            interval=interval,
            count=count,
        )
    except Exception as e:
        return R.err(f"获取分K失败: {e}", 502)

    items = [
        MinuteKlineItem(
            datetime=bo.dt.strftime("%Y-%m-%d %H:%M"),
            interval=bo.interval,
            open=bo.open,
            high=bo.high,
            low=bo.low,
            close=bo.close,
            volume=bo.volume,
            amount=bo.amount,
        ).model_dump()
        for bo in bos
    ]

    return R.ok({"total": len(items), "items": items})
