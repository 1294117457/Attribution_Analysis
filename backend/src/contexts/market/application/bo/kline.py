"""bo — 从 contexts/data/application/port 拆出（step7-c）"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from contexts.data.application.port.base import CachePolicy, DataPort
from shared.interface.validators import Symbol, TradeDate
from contexts.market.domain.entities.kline.entity import Kline


class KlineBO(BaseModel):
    """日 K BO（字段与 kline 聚合 entity 一一对应）"""

    symbol: str = Field(..., description="股票代码")
    trade_date: Optional[date] = None
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
        """BO -> Entity 便利方法（委托 from_bo）"""
        return Kline.from_bo(self)


    @classmethod
    def from_entity(cls, entity) -> "KlineBO":
        """从 Entity 构造 BO（Application 接受 Domain 的 Entity）

        利用 BO 的 model_fields 判断哪些字段是必需的；
        Entity 中为 None 的字段会跳过（让 BO 用默认值）。
        """
        kwargs = {}
        for fname, field in cls.model_fields.items():
            if fname == "symbol":
                kwargs[fname] = entity.symbol
                continue
            if not hasattr(entity, fname):
                continue
            value = getattr(entity, fname)
            # 如果字段是必需的且 Entity 值为 None，则跳过（BO 会有默认值）
            if value is None and field.is_required():
                continue
            kwargs[fname] = value
        return cls(**kwargs)
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


