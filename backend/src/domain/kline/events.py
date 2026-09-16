"""K线领域事件"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from domain.base import DomainEvent


@dataclass
class KlineCollected(DomainEvent):
    """K线采集完成事件"""

    symbol: str = ""
    name: str = ""
    collected_count: int = 0
    total_count: int = 0
    source: str = "tushare"

    def __init__(
        self,
        symbol: str,
        name: str = "",
        collected_count: int = 0,
        total_count: int = 0,
        source: str = "tushare",
    ):
        self.symbol = symbol
        self.name = name
        self.collected_count = collected_count
        self.total_count = total_count
        self.source = source
        self.occurred_on = datetime.now()

    @property
    def is_new_data(self) -> bool:
        return self.collected_count > 0


@dataclass
class KlineDeleted(DomainEvent):
    """K线删除事件"""

    symbol: str = ""
    trade_date: Optional[str] = None
    deleted_count: int = 0

    def __init__(
        self,
        symbol: str,
        trade_date: Optional[str] = None,
        deleted_count: int = 0,
    ):
        self.symbol = symbol
        self.trade_date = trade_date
        self.deleted_count = deleted_count
        self.occurred_on = datetime.now()
