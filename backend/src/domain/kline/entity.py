"""K线聚合根"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import AggregateRoot
from domain.kline.value_objects import StockCode, TradeDate


@dataclass
class Kline(AggregateRoot):
    """K线聚合根

    业务规则：high >= low, high >= open, high >= close, low <= open, low <= close
    """

    id: int
    symbol: StockCode
    trade_date: TradeDate
    name: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

    def __post_init__(self):
        # 调用父类初始化（设置 _domain_events 列表）
        AggregateRoot.__init__(self)

    @property
    def is_up(self) -> bool:
        return self.close > self.open

    @property
    def is_down(self) -> bool:
        return self.close < self.open

    @property
    def price_range(self) -> float:
        return self.high - self.low

    def validate(self) -> None:
        """业务规则验证"""
        errors = []
        if self.high < self.low:
            errors.append("最高价不能低于最低价")
        if self.high < self.open or self.high < self.close:
            errors.append("最高价不能低于开盘价或收盘价")
        if self.low > self.open or self.low > self.close:
            errors.append("最低价不能高于开盘价或收盘价")
        if self.volume < 0:
            errors.append("成交量不能为负")
        if self.amount < 0:
            errors.append("成交额不能为负")
        if errors:
            raise ValueError(f"K线数据验证失败: {'; '.join(errors)}")

    @classmethod
    def create(
        cls,
        symbol: str,
        name: str,
        trade_date: date,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        amount: float,
        change_pct: Optional[float] = None,
        id: int = 0,
    ) -> Kline:
        """工厂方法：创建K线聚合根"""
        kline = cls(
            id=id,
            symbol=StockCode(symbol),
            trade_date=TradeDate(trade_date),
            name=name,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            amount=amount,
            change_pct=change_pct,
        )
        kline.validate()
        return kline
