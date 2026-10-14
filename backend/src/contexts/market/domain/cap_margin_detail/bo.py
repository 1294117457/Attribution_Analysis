"""bo — 从 contexts/data/application/port 拆出（step7-c）"""
from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict
from contexts.data.application.port.base import DataPort
from shared.interface.validators import Symbol, TradeDate
from contexts.data.application.port.types import TradeDateParams


class CapMarginDetailBO(BaseModel):
    symbol: str
    trade_date: date
    rzye: Optional[float] = None
    rqye: Optional[float] = None
    rzmre: Optional[float] = None
    rqyl: Optional[float] = None
    rzche: Optional[float] = None
    rqchl: Optional[float] = None
    rqmcl: Optional[float] = None
    rzrqye: Optional[float] = None

    def to_entity(self) -> "CapMarginDetail":
        from contexts.market.domain.cap_margin_detail.entity import CapMarginDetail
        return CapMarginDetail(**self.model_dump())


