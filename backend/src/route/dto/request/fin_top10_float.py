"""自动迁移自 domain/fin_top10_float/schemas.py（BO 部分）"""

from __future__ import annotations

from pydantic import BaseModel
from typing import Optional
from datetime import date


class FinTop10FloatHoldersBO(BaseModel):
    symbol: str
    ann_date: Optional[date] = None
    end_date: Optional[date] = None
    holder_name: str
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None

    def to_entity(self) -> "FinTop10Float":
        from domain.entitys.fin_top10_float.entity import FinTop10Float
        return FinTop10Float(**self.model_dump())