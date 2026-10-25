"""MinuteService：分钟 K 线 service（Pytdx 实时查询，不入库）

主入口是 get()；collect() 仅返回提示。

命名说明：tech/ 下 Minute 唯一指向分钟 K 线，剥 Kline 不歧义。
service_name 保持 "minute_kline"：URL / DB 前端查询键，不能改。
"""
from __future__ import annotations

import logging
from typing import Optional

from contexts.collect.application.service.base import CollectResult, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.tech.MinutePytdxFetcher import (
    MinutePytdxFetcher,
)

logger = logging.getLogger(__name__)


class MinuteService:
    """分钟 K 线 service（Pytdx 实时查询，无 collect/写库）"""

    META = ServiceMeta(
        name='minute_kline',  # service_name 稳定：URL / 日志查询键
        facet='tech',
        label='分钟 K 线',
        description='通达信 1/5/15/30/60 分钟 K 线（实时）',
        kind=ServiceKind.REALTIME,
        concurrency=1,
    )

    # 兼容前端/旧调用方传 '5'（裸数字）的情况
    _INTERVAL_ALIAS = {"1": "1min", "5": "5min", "15": "15min", "30": "30min", "60": "60min"}

    def __init__(self, fetcher: MinutePytdxFetcher | None = None) -> None:
        self._fetcher = fetcher or MinutePytdxFetcher()

    async def collect(self, params: dict) -> CollectResult:
        """collect 模式：实际上无数据写库，返回空"""
        return CollectResult(message="minute_kline 是实时查询 service，请使用 get()")

    @staticmethod
    def _normalize_interval(interval: str) -> str:
        return MinuteService._INTERVAL_ALIAS.get(str(interval).strip(), str(interval))

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


__all__ = ["MinuteService"]
