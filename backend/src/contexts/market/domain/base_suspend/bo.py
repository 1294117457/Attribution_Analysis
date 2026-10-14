"""bo — 从 contexts/data/application/port 拆出（step7-c）"""
from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from contexts.data.application.port.base import DataPort
from shared.interface.validators import Symbol
from contexts.data.application.port.types import ListStatus, SymbolParams, TradeDateParams


class BaseSuspendBO(BaseModel):
    symbol: str
    trade_date: date
    suspend_timing: Optional[date] = None
    suspend_type: Optional[str] = None

    def to_entity(self) -> "BaseSuspend":
        from contexts.market.domain.base_suspend.entity import BaseSuspend
        return BaseSuspend(**self.model_dump())


