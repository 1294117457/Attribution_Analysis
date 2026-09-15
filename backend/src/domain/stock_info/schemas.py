"""股票信息 Schema"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from domain.stock_info.entity import StockInfo


class StockInfoVO(BaseModel):
    """股票信息视图对象"""

    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    list_date: Optional[date] = None
    total_shares: Optional[int] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_entity(cls, entity: StockInfo) -> "StockInfoVO":
        return cls(
            symbol=entity.symbol,
            name=entity.name,
            industry=entity.industry.name if entity.industry else None,
            market=entity.market.code if entity.market else None,
            list_date=entity.list_date,
            total_shares=entity.total_shares,
        )


class StockListItemVO(BaseModel):
    """股票列表项（含K线统计）"""

    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end: Optional[date] = None
