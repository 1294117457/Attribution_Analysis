"""bo — 从 contexts/data/application/port 拆出（step7-c）"""
from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict
from contexts.data.application.port.base import DataPort
from shared.interface.validators import Symbol, TradeDate
from contexts.data.application.port.types import TradeDateParams


class CapHolderNumBO(BaseModel):
    symbol: str
    ann_date: Optional[date] = None
    end_date: date
    holder_num: Optional[int] = None
    holder_nums: Optional[float] = None

    def to_entity(self) -> "CapHolderNum":
        from contexts.market.domain.cap_holder_num.entity import CapHolderNum
        return CapHolderNum(**self.model_dump())


# ═══════════════════════════════════════════════════════════════════════════════
# Params
# ═══════════════════════════════════════════════════════════════════════════════


