"""自动迁移自 domain/cap_block_trade/schemas.py（BO 部分）"""

from __future__ import annotations

from pydantic import BaseModel
from typing import Optional
from datetime import date


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
        from domain.entitys.cap_block_trade.entity import CapBlockTrade
        return CapBlockTrade(**self.model_dump())