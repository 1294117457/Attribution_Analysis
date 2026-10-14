"""bo — 从 contexts/data/application/port 拆出（step7-c）"""
from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from contexts.data.application.port.base import DataPort
from shared.interface.validators import Symbol
from contexts.data.application.port.types import ListStatus, SymbolParams, TradeDateParams


class BaseAdjFactorBO(BaseModel):
    symbol: str
    trade_date: date
    adj_factor: float

    def to_entity(self) -> "BaseAdjFactor":
        from contexts.market.domain.base_adj_factor.entity import BaseAdjFactor
        return BaseAdjFactor(**self.model_dump())


