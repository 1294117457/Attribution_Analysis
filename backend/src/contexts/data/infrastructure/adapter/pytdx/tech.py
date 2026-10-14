"""pytdx · 股票分 K Adapter"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from contexts.data.application.port.base import SourceUnavailable
from contexts.data.application.port.tech import (
    BARS_PER_DAY,
    MinuteInterval,
    MinuteKlineBO,
    MinuteKlineParams,
    MinuteKlinePort,
)
from contexts.data.infrastructure.adapter.core.base import AdapterBase
from contexts.data.infrastructure.adapter.pytdx.client import PytdxClient

logger = logging.getLogger(__name__)

_CATEGORY: dict[MinuteInterval, int] = {
    MinuteInterval.M1: 7,
    MinuteInterval.M5: 0,
    MinuteInterval.M15: 1,
    MinuteInterval.M30: 2,
    MinuteInterval.M60: 3,
}

_BATCH = 800


def symbol_to_market(symbol: str) -> int:
    """股票代码 → pytdx 市场代码（0=深圳 1=上海）"""
    return 1 if symbol[:2] in ("60", "68", "11", "51") else 0


class PytdxMinuteKlineAdapter(MinuteKlinePort, AdapterBase):
    tool = "pytdx"
    origin = "tdx"
    priority = 10
    throttle_group = "tdx"

    def __init__(self, client: PytdxClient) -> None:
        self._c = client

    def supports(self, p: MinuteKlineParams) -> bool:
        """北交所（8/4/92 开头）不在 pytdx 标准行情服务器中"""
        return not p.symbol.startswith(("8", "4", "92"))

    async def fetch(self, p: MinuteKlineParams) -> list[MinuteKlineBO]:
        category = _CATEGORY[p.interval]
        market = symbol_to_market(p.symbol)
        count = BARS_PER_DAY[p.interval] * p.days

        def pull(api):
            bars: list = []
            start = 0
            while len(bars) < count:
                size = min(_BATCH, count - len(bars))
                try:
                    batch = api.get_security_bars(category, market, p.symbol, start, size)
                except Exception as e:
                    self._c.mark_disconnected()
                    if not bars:
                        raise SourceUnavailable(f"pytdx 获取分K失败: {e!r}") from e
                    logger.warning("pytdx 获取分K中断，返回已取 %d 条: %s", len(bars), e)
                    break
                if not batch:
                    break
                bars.extend(batch)
                start += len(batch)
                if len(batch) < size:
                    break
            return api.to_df(bars) if bars else None

        df = await self._c.run(pull)
        return _parse(df, p.symbol, p.interval.value)


def _parse(df: Optional[pd.DataFrame], symbol: str, interval: str) -> list[MinuteKlineBO]:
    if df is None or df.empty:
        return []
    items: list[MinuteKlineBO] = []
    for _, row in df.iterrows():
        try:
            dt_str = row.get("datetime")
            if not dt_str:
                continue
            close = float(row.get("close", 0))
            if close <= 0:
                continue
            items.append(MinuteKlineBO(
                symbol=symbol,
                dt=datetime.strptime(str(dt_str), "%Y-%m-%d %H:%M"),
                interval=interval,
                open=float(row.get("open", 0)),
                high=float(row.get("high", 0)),
                low=float(row.get("low", 0)),
                close=close,
                volume=int(row.get("vol", 0)),
                amount=float(row.get("amount", 0)),
            ))
        except Exception as e:
            logger.warning("跳过无效分钟K线行: %s", e)
    return items


ADAPTERS = (PytdxMinuteKlineAdapter,)

__all__ = ["ADAPTERS", "PytdxMinuteKlineAdapter", "symbol_to_market"]
