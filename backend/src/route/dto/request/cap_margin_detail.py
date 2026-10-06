"""自动迁移自 domain/cap_margin_detail/schemas.py（BO 部分）"""

from __future__ import annotations

from pydantic import BaseModel
from typing import Optional
from datetime import date


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
        from domain.entitys.cap_margin_detail.entity import CapMarginDetail
        return CapMarginDetail(**self.model_dump())