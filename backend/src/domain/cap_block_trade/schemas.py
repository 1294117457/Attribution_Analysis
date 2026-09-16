"""cap_block_trade — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class CapBlockTradeBO(BaseModel):
    trade_date: date
    symbol: str
    name: Optional[str] = None
    price: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None

    def to_entity(self) -> "CapBlockTrade":
        from domain.cap_block_trade.entity import CapBlockTrade
        return CapBlockTrade(**self.model_dump())


class CapBlockTradeVO(BaseModel):
    trade_date: date
    symbol: str
    name: Optional[str] = None
    price: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None
