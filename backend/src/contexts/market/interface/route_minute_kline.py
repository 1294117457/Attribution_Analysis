"""分钟 K 线 API 路由（实时接口 stock_minute_kline，不落库）

前端请求 → StockInfoService.get_minute_klines → DataGateway（QUERY：15 秒缓存 / 单飞 / 同源限流 / 统计）→ pytdx
"""

from fastapi import APIRouter, Depends, Query
from pydantic import ValidationError

from contexts.data.application.port.base import InvalidParams, RateLimited, SourceUnavailable
from contexts.data.application.port.tech import MinuteInterval, MinuteKlineParams
from contexts.market.application.service.stock_info_service import StockInfoService
from contexts.shared.infrastructure.config.di import get_stock_info_service
from contexts.shared.interface import _response as R

router = APIRouter(prefix="/minute-klines", tags=["分钟K线"])


@router.get("/{symbol}", summary="实时获取分钟K线")
async def get_minute_klines(
    symbol: str,
    interval: MinuteInterval = Query(MinuteInterval.M5, description="周期"),
    days: int = Query(1, ge=1, le=5, description="天数：1min 仅 1，其他 1–5"),
    service: StockInfoService = Depends(get_stock_info_service),
):
    try:
        params = MinuteKlineParams(symbol=symbol, interval=interval, days=days)
        return R.ok(await service.get_minute_klines(params))
    except ValidationError as e:
        return R.err("; ".join(err["msg"].removeprefix("Value error, ") for err in e.errors()), 400)
    except InvalidParams as e:
        return R.err(str(e), 400)
    except (RateLimited, SourceUnavailable) as e:
        return R.err(str(e), 502)
