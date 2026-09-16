"""cap_top_list — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class CapTopListBO(BaseModel):
    trade_date: date
    symbol: str
    name: Optional[str] = None
    close: Optional[float] = None
    pct_change: Optional[float] = None
    turnover_rate: Optional[float] = None
    amount: Optional[float] = None
    l_sell: Optional[float] = None
    l_buy: Optional[float] = None
    l_amount: Optional[float] = None
    net_amount: Optional[float] = None
    net_rate: Optional[float] = None
    amount_rate: Optional[float] = None
    float_values: Optional[float] = None
    reason: Optional[str] = None

    def to_entity(self) -> "CapTopList":
        from domain.cap_top_list.entity import CapTopList
        return CapTopList(**self.model_dump())


class CapTopListVO(BaseModel):
    trade_date: date
    symbol: str
    name: Optional[str] = None
    close: Optional[float] = None
    pct_change: Optional[float] = None
    amount: Optional[float] = None
    net_amount: Optional[float] = None
    reason: Optional[str] = None
