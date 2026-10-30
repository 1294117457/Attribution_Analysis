"""MinuteKlinePytdxFetcher：分 K 线（Pytdx）—— step7 重构版"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pandas as pd
from pydantic import BaseModel

from collectors.schemas import (
    BARS_PER_DAY,
    MinuteInterval,
    MinuteKlineBO,
    MinuteKlineParams,
)
from collectors.base import BaseFetcher
from core.errors import SourceUnavailable
from core.pytdx_client import get_pytdx_client

logger = logging.getLogger(__name__)

_CATEGORY: dict[MinuteInterval, int] = {
    MinuteInterval.M1: 7, MinuteInterval.M5: 0,
    MinuteInterval.M15: 1, MinuteInterval.M30: 2, MinuteInterval.M60: 3,
}
_BATCH = 800


def symbol_to_market(symbol: str) -> int:
    return 1 if symbol[:2] in ("60", "68", "11", "51") else 0


class MinuteKlinePytdxFetcher(BaseFetcher):
    """分 K 线 fetcher（Pytdx 实时）"""

    fetcher_type = "minute_kline_pytdx"
    source = "pytdx"
    label = "分 K 线（Pytdx）"
    description = "通达信 1/5/15/30/60 分钟 K 线"

    def __init__(self) -> None:
        self._c = get_pytdx_client()

    def supports(self, p: MinuteKlineParams) -> bool:
        return not p.symbol.startswith(("8", "4", "92"))

    async def fetch(self, **params) -> list[BaseModel]:
        p = MinuteKlineParams.model_validate(params)
        if not self.supports(p):
            raise ValueError(f"{p.symbol} 北交所代码，分K不支持")
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
                        raise RuntimeError(f"pytdx 获取分K失败: {e!r}") from e
                    logger.warning("pytdx 获取分K中断，返回已取 %d 条: %s", len(bars), e)
                    break
                if not batch:
                    # ★ 连接成功但没数据 → 可能是「空站」（行情接口关闭）
                    #   → 通知 client，连续空就换服务器重试
                    self._c.mark_empty_response()
                    break
                self._c.mark_data_ok()
                bars.extend(batch)
                start += len(batch)
                if len(batch) < size:
                    break
            return api.to_df(bars) if bars else None

        df = await self._c.run_with_failover(pull)
        # 注：MinuteKlineParams.interval 是 str（"1min" 等），直接传字符串即可
        items = _parse(df, p.symbol, p.interval)
        if not items:
            # ★ 明确报错而不是「静默返回空列表」——
            #   上游取不到数据时必须让调用方知道，否则前端只看到「没有数据」，
            #   无法区分「今天没数据」和「数据源挂了」。
            raise SourceUnavailable(
                f"pytdx 未返回 {p.symbol} 的 {p.interval} K 线"
                "（所有通达信服务器均无数据或行情接口不可用）"
            )
        return items


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


__all__ = ["MinuteKlinePytdxFetcher", "symbol_to_market"]
