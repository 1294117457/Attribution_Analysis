"""分钟 K 线 API 路由（实时接口 stock_minute_kline，不落库）

前端请求 → RealtimeQueryFramework（Redis 15 秒缓存 / 单飞 / 同源限流 / 降级 / 统计）→ pytdx
"""

from typing import Optional

from fastapi import APIRouter, Query

from infrastructure.adapter.realtime import RealtimeQueryError, get_realtime_query_framework
from route.api import _response as R

router = APIRouter(prefix="/minute-klines", tags=["分钟K线"])


@router.get("/{symbol}", summary="实时获取分钟K线")
async def get_minute_klines(
    symbol: str,
    interval: str = Query("5min", description="周期: 1min/5min/15min/30min/60min"),
    days: int = Query(1, ge=1, le=5, description="天数：1min 仅 1，其他 1–5"),
    count: Optional[int] = Query(None, ge=1, le=1200, description="兼容旧参数：传了则按根数取"),
):
    params = {"symbol": symbol, "interval": interval, "days": days, "count": count}
    try:
        res = await get_realtime_query_framework().query("stock_minute_kline", params)
    except ValueError as e:
        return R.err(str(e), 400)
    except RealtimeQueryError as e:
        return R.err(str(e), 502)

    data = res.data or {"total": 0, "items": []}
    return R.ok({
        "total": data["total"],
        "items": data["items"],
        "cached": res.cached,
        "fetched_at": res.fetched_at,
    })
