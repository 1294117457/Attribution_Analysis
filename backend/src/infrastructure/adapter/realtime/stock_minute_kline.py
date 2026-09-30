"""实时接口：股票分 K（pytdx 通达信，不入库）

「当天」= 最近一个交易日；通达信按「最近 N 根」返回，盘前 / 收盘后 / 周末自然是上一个交易日。
"""

from __future__ import annotations

from typing import Any, Optional

from application.port.collector_port import MinuteKlineFetcher
from infrastructure.adapter import get_registry
from infrastructure.adapter.realtime.base import BaseRealtimeQuery

BARS_PER_DAY = {"1min": 240, "5min": 48, "15min": 16, "30min": 8, "60min": 4}
MAX_DAYS = 5
MAX_LEGACY_COUNT = 1200


class StockMinuteKlineQuery(BaseRealtimeQuery):
    name = "stock_minute_kline"
    facet = "tech"
    sub_facet = "kline"
    label = "股票分 K"
    description = "通达信 1/5/15/30/60 分钟 K 线；1 分钟仅当天，其他周期最多 5 日"
    sort_order = 50
    source = "tdx"
    source_label = "通达信"
    ttl_trading = 15
    consumers = ("股票列表展开行 · 分 K",)
    sample_params = {"symbol": "600519", "interval": "5min", "days": 1}

    def normalize(self, params: dict) -> dict:
        symbol = str(params.get("symbol") or "").strip()
        if len(symbol) != 6 or not symbol.isdigit():
            raise ValueError("symbol 需为 6 位股票代码")
        if symbol.startswith(("8", "4", "92")):
            raise ValueError(f"{symbol} 为北交所代码，分K暂不支持")
        interval = str(params.get("interval") or "5min")
        if interval not in BARS_PER_DAY:
            raise ValueError(f"interval 可选: {list(BARS_PER_DAY)}")

        count = params.get("count")
        if count not in (None, ""):
            count = int(count)
            if not 1 <= count <= MAX_LEGACY_COUNT:
                raise ValueError(f"count 范围 1–{MAX_LEGACY_COUNT}")
            return {"symbol": symbol, "interval": interval, "count": count}

        days = int(params.get("days") or 1)
        max_days = 1 if interval == "1min" else MAX_DAYS
        if not 1 <= days <= max_days:
            raise ValueError(f"{interval} 的 days 范围 1–{max_days}")
        return {"symbol": symbol, "interval": interval, "days": days}

    def cache_key(self, params: dict) -> str:
        tail = f"c{params['count']}" if "count" in params else params["days"]
        return f"{params['symbol']}:{params['interval']}:{tail}"

    async def fetch(self, params: dict) -> Optional[dict[str, Any]]:
        interval = params["interval"]
        count = params.get("count") or BARS_PER_DAY[interval] * params["days"]
        fetcher: MinuteKlineFetcher = get_registry().get(MinuteKlineFetcher)
        bos = await fetcher.fetch_minute_klines(symbol=params["symbol"], interval=interval, count=count)
        items = [
            {
                "datetime": bo.dt.strftime("%Y-%m-%d %H:%M"),
                "interval": bo.interval,
                "open": bo.open,
                "high": bo.high,
                "low": bo.low,
                "close": bo.close,
                "volume": bo.volume,
                "amount": bo.amount,
            }
            for bo in bos
        ]
        return {"symbol": params["symbol"], "interval": interval, "total": len(items), "items": items}
