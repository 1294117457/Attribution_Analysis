"""自动迁移自 domain/cap_holder_num/schemas.py（BO 部分）"""

from __future__ import annotations

from pydantic import BaseModel
from typing import Optional
from datetime import date


class CapHolderNumBO(BaseModel):
    symbol: str
    ann_date: Optional[date] = None
    end_date: date
    holder_num: Optional[int] = None
    holder_nums: Optional[float] = None

    def to_entity(self) -> "CapHolderNum":
        from domain.entitys.cap_holder_num.entity import CapHolderNum
        return CapHolderNum(**self.model_dump())