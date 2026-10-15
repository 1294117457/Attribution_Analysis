"""技术面 Port：日 K / 分 K"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contexts.data.application.port.base import CachePolicy, DataPort
from contexts.data.application.port.types import Symbol, TradeDate

from contexts.market.application.bo.kline import KlineBO, MinuteKlineBO, MinuteInterval, BARS_PER_DAY

# ═══════════════════════════════════════════════════════════════════════════════
# 日 K
# ═══════════════════════════════════════════════════════════════════════════════

class DailyKlineParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: Symbol
    start_date: TradeDate
    end_date: TradeDate

    @model_validator(mode="after")
    def _ordered(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date 不能晚于 end_date")
        return self

class DailyKlinePort(DataPort[DailyKlineParams, KlineBO]):
    name, label = "daily_kline", "日 K 线"
    facet, sub_facet = "tech", "kline"
    description = "单只股票日线 OHLCV（不复权）"
    Params, Item = DailyKlineParams, KlineBO
    unit = "symbol"
    sample_params = {"symbol": "600519", "start_date": "2026-01-05", "end_date": "2026-01-09"}

# ═══════════════════════════════════════════════════════════════════════════════
# 分 K（实时接口）
# ═══════════════════════════════════════════════════════════════════════════════

class MinuteKlineParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: Symbol
    interval: MinuteInterval = MinuteInterval.M5     # 粒度
    days: int = Field(1, ge=1, le=5)                 # 范围：最近 N 个交易日

    @model_validator(mode="after")
    def _one_day_for_1min(self):
        if self.interval is MinuteInterval.M1 and self.days != 1:
            raise ValueError("1min 只支持当天")
        return self

class MinuteKlinePort(DataPort[MinuteKlineParams, MinuteKlineBO]):
    name, label = "stock_minute_kline", "股票分 K"
    facet, sub_facet = "tech", "kline"
    description = "通达信 1/5/15/30/60 分钟 K 线；1 分钟仅当天，其他周期最多 5 日"
    Params, Item = MinuteKlineParams, MinuteKlineBO
    cache = CachePolicy(ttl_trading=15, consumers=("股票列表展开行 · 分 K",))
    sample_params = {"symbol": "600519", "interval": "5min", "days": 1}
    sort_order = 50

__all__ = [
    "BARS_PER_DAY",
    "DailyKlineParams",
    "DailyKlinePort",
    "KlineBO",
    "MinuteInterval",
    "MinuteKlineBO",
    "MinuteKlineParams",
    "MinuteKlinePort",
]
