"""股票信息聚合根"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import AggregateRoot
from domain.stock_info.value_objects import Industry, Market


@dataclass
class StockInfo(AggregateRoot):
    """股票信息聚合根"""

    id: int
    symbol: str
    name: str
    industry: Optional[Industry] = None
    market: Optional[Market] = None
    list_date: Optional[date] = None
    total_shares: Optional[int] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

    def __post_init__(self):
        AggregateRoot.__init__(self)

    @classmethod
    def create(
        cls,
        symbol: str,
        name: str,
        industry: Optional[str] = None,
        market: Optional[str] = None,
        list_date: Optional[date] = None,
        total_shares: Optional[int] = None,
        id: int = 0,
    ) -> StockInfo:
        return cls(
            id=id,
            symbol=symbol,
            name=name,
            industry=Industry(industry) if industry else None,
            market=Market.from_code(market) if market else None,
            list_date=list_date,
            total_shares=total_shares,
        )

    def update_name(self, name: str) -> None:
        self.name = name

    def update_industry(self, industry: str) -> None:
        self.industry = Industry(industry)
