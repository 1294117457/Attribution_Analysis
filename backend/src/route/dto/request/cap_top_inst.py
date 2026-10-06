"""自动迁移自 domain/cap_top_inst/schemas.py（BO 部分）"""

from __future__ import annotations

from pydantic import BaseModel
from typing import Optional
from datetime import date


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
        from domain.entitys.cap_top_inst.entity import CapTopInst
        return CapTopInst(**self.model_dump())