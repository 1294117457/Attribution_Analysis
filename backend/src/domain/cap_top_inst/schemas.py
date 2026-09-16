"""cap_top_inst — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class CapTopInstBO(BaseModel):
    trade_date: date
    symbol: str
    exalter: Optional[str] = None
    side: Optional[str] = None
    buy: Optional[float] = None
    buy_rate: Optional[float] = None
    sell: Optional[float] = None
    sell_rate: Optional[float] = None
    net_buy: Optional[float] = None
    reason: Optional[str] = None

    def to_entity(self) -> "CapTopInst":
        from domain.cap_top_inst.entity import CapTopInst
        return CapTopInst(**self.model_dump())


class CapTopInstVO(BaseModel):
    trade_date: date
    symbol: str
    exalter: Optional[str] = None
    side: Optional[str] = None
    buy: Optional[float] = None
    sell: Optional[float] = None
    net_buy: Optional[float] = None
    reason: Optional[str] = None
