"""K线领域 Schema（BO/VO）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from domain.kline.entity import Kline


class KlineBO(BaseModel):
    """K线业务对象（采集层产出 → 应用层）

    字段名与外部数据源对齐。
    """

    symbol: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    trade_date: date = Field(..., description="交易日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量（手）")
    amount: float = Field(..., description="成交额（元）")
    change_pct: Optional[float] = Field(None, description="涨跌幅 %")

    def to_entity(self, id: int = 0) -> Kline:
        """转换为领域实体"""
        return Kline.create(
            id=id,
            symbol=self.symbol,
            name=self.name,
            trade_date=self.trade_date,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            amount=self.amount,
            change_pct=self.change_pct,
        )


class KlineVO(BaseModel):
    """K线视图对象（API 出参）

    注意：date 字段（不使用 trade_date），方便前端直接使用。
    """

    symbol: str
    name: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_entity(cls, kline: Kline) -> "KlineVO":
        return cls(
            symbol=kline.symbol.code,
            name=kline.name,
            date=kline.trade_date.date,
            open=kline.open,
            high=kline.high,
            low=kline.low,
            close=kline.close,
            volume=kline.volume,
            amount=kline.amount,
            change_pct=kline.change_pct,
        )


class KlineStatsVO(BaseModel):
    """K线统计视图"""

    symbol: str
    name: str
    count: int = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    latest_close: Optional[float] = None
    latest_volume: Optional[int] = None
