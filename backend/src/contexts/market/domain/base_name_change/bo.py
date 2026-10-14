"""bo — 从 contexts/data/application/port 拆出（step7-c）"""
from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from contexts.data.application.port.base import DataPort
from shared.interface.validators import Symbol
from contexts.data.application.port.types import ListStatus, SymbolParams, TradeDateParams


class BaseNameChangeBO(BaseModel):
    symbol: str
    name: str
    start_date: date
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    change_reason: Optional[str] = None

    def to_entity(self) -> "BaseNameChange":
        from contexts.market.domain.base_name_change.entity import BaseNameChange
        return BaseNameChange(**self.model_dump())


