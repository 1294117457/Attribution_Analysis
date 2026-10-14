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
        """委托给 converter（step7-e）"""
        from contexts.market.application.base_suspend.converter import base_suspend_bo_to_entity
        return base_suspend_bo_to_entity(self)


