"""bo — 从 contexts/data/application/port 拆出（step7-c）"""
from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict
from contexts.data.application.port.base import DataPort
from shared.interface.validators import Symbol, TradeDate
from contexts.data.application.port.types import TradeDateParams


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
        from contexts.market.domain.cap_top_inst.entity import CapTopInst
        return CapTopInst(**self.model_dump())


