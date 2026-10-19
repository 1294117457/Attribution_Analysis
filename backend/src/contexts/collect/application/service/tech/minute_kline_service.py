"""MinuteKlineService：分钟 K 线 service（Pytdx 实时查询，不入库）

主入口是 get()；collect() 仅返回提示。
"""
from __future__ import annotations

import logging
from typing import Optional

from contexts.collect.application.service.base import CollectResult, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.tech.MinuteKlinePytdxFetcher import (
    MinuteKlinePytdxFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class MinuteKlineService:
    """分钟 K 线 service（Pytdx 实时查询，无 collect/写库）"""

    META = ServiceMeta(
        name='minute_kline',
        facet='tech',
        label='分钟 K 线',
        description='通达信 1/5/15/30/60 分钟 K 线（实时）',
        kind=ServiceKind.REALTIME,
    )
    name = "minute_kline"
    facet = "tech"
    sub_facet = "kline_minute"
    label = "分钟 K 线"
    description = "通达信 1/5/15/30/60 分钟 K 线（实时）"
    DEFAULT_PARAMS = {"symbol": None, "interval": "5min", "days": 1}
    UI_SCHEMA = [
        {"key": "symbol",   "ui": "symbol_str",     "label": "股票代码", "required": True, "placeholder": "000001"},
        {"key": "interval", "ui": "interval_kline", "label": "分钟周期", "required": True},
        {"key": "days",     "ui": "days_int",       "label": "回溯天数", "required": True},
    ]
    RATE_LIMIT = ("pytdx", 60, 60)
    CONCURRENCY = 1

    # 兼容前端/旧调用方传 '5'（裸数字）的情况
    _INTERVAL_ALIAS = {"1": "1min", "5": "5min", "15": "15min", "30": "30min", "60": "60min"}

    def __init__(self, fetcher: MinuteKlinePytdxFetcher | None = None) -> None:
        self._fetcher = fetcher or MinuteKlinePytdxFetcher()

    async def collect(self, params: dict) -> CollectResult:
        """collect 模式：实际上无数据写库，返回空"""
        return CollectResult(message="MinuteKline 是实时查询 service，请使用 get()")

    @staticmethod
    def _normalize_interval(interval: str) -> str:
        return MinuteKlineService._INTERVAL_ALIAS.get(str(interval).strip(), str(interval))

    async def get(
        self,
        symbol: str,
        interval: str = "5min",
        days: int = 1,
    ) -> list[dict]:
        """实时查询分 K 线"""
        # 兼容前端/旧调用方传 '5'（裸数字）的情况
        normalized = self._normalize_interval(interval)
        # 校验：是合法 MinuteInterval（防止拼错）
        from contexts.market.application.bo.kline import MinuteInterval
        MinuteInterval(normalized)  # 失败会抛 ValueError
        p = {
            "symbol": str(symbol).zfill(6),
            "interval": normalized,
            "days": days,
        }
        await check(self.RATE_LIMIT)
        bos = await self._fetcher.fetch(**p)
        return [
            {
                "symbol": bo.symbol,
                "dt": bo.dt.isoformat() if bo.dt else None,
                "interval": bo.interval,
                "open": bo.open, "high": bo.high, "low": bo.low, "close": bo.close,
                "volume": bo.volume, "amount": bo.amount,
            }
            for bo in bos
        ]


__all__ = ["MinuteKlineService"]
