"""K线聚合根（仅 OHLCV；技术指标见 domain/service/indicator_calculator.py，请求时实时计算）"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from contexts.shared.domain.base import AggregateRoot
from contexts.market.domain.kline.vo import StockCode, TradeDate


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

# ── 领域事件 ──

"""K线领域事件"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from contexts.shared.domain.base import DomainEvent


@dataclass(kw_only=True)
class KlineCollected(DomainEvent):
    """K线采集完成事件"""

    symbol: str = ""
    name: str = ""
    collected_count: int = 0
    total_count: int = 0
    source: str = "tushare"

    @property
    def is_new_data(self) -> bool:
        return self.collected_count > 0


@dataclass(kw_only=True)
class KlineDeleted(DomainEvent):
    """K线删除事件"""

    symbol: str = ""
    trade_date: Optional[str] = None
    deleted_count: int = 0


# ──


# ── K线领域异常（统一继承 DomainError） ──

from contexts.shared.domain.base import DomainError


class KlineNotFoundError(DomainError):
    """K线不存在"""

    def __init__(self, symbol: str, date: str = None):
        if date:
            msg = f"股票 {symbol} 在 {date} 的K线不存在"
        else:
            msg = f"股票 {symbol} 的K线不存在"
        super().__init__(msg, "KLINE_NOT_FOUND")
        self.symbol = symbol


class KlineDataError(DomainError):
    """K线数据错误"""

    def __init__(self, symbol: str, reason: str):
        super().__init__(f"股票 {symbol} 数据错误: {reason}", "KLINE_DATA_ERROR")
        self.symbol = symbol


class CollectionError(DomainError):
    """数据采集错误"""

    def __init__(self, symbol: str, reason: str):
        super().__init__(f"采集股票 {symbol} 失败: {reason}", "COLLECTION_ERROR")
        self.symbol = symbol


# ── 操作池相关异常 ──────────────────────────────────────────────
