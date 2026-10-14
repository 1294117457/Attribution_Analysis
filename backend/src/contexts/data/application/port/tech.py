"""技术面 Port：日 K / 分 K"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contexts.data.application.port.base import CachePolicy, DataPort
from contexts.data.application.port.types import Symbol, TradeDate


# ═══════════════════════════════════════════════════════════════════════════════
# 日 K
# ═══════════════════════════════════════════════════════════════════════════════


class KlineBO(BaseModel):
    """日 K BO（字段与 kline 聚合 entity 一一对应）"""

    symbol: str = Field(..., description="股票代码")
    trade_date: date = Field(..., description="交易日")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., ge=0, description="成交量（股）")
    amount: float = Field(..., ge=0.0, description="成交额（元）")
    change_pct: Optional[float] = Field(default=None, description="涨跌幅 %")
    name: Optional[str] = Field(default=None, description="股票名称（可选）")
    source: str = Field(default="tushare", description="数据源")

    model_config = {"from_attributes": True}

    def to_entity_args(self) -> dict:
        """返回用于 Kline.create(**) 的字段。"""
        return {
            "symbol": self.symbol,
            "trade_date": self.trade_date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
            "change_pct": self.change_pct,
            "name": self.name or self.symbol,
            "source": self.source,
        }

    def to_entity(self) -> "Kline":
        from contexts.market.domain.kline.entity import Kline
        args = self.to_entity_args()
        args.pop("source")
        return Kline.create(**args)


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


class MinuteInterval(StrEnum):
    M1 = "1min"
    M5 = "5min"
    M15 = "15min"
    M30 = "30min"
    M60 = "60min"


BARS_PER_DAY: dict[MinuteInterval, int] = {
    MinuteInterval.M1: 240,
    MinuteInterval.M5: 48,
    MinuteInterval.M15: 16,
    MinuteInterval.M30: 8,
    MinuteInterval.M60: 4,
}


class MinuteKlineBO(BaseModel):
    """分钟 K 线 BO"""

    symbol: str
    name: str = ""
    dt: datetime
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float


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
