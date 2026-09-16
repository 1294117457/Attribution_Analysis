"""cap_margin — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class CapMarginBO(BaseModel):
    trade_date: date
    exchange_id: str
    rzye: Optional[float] = None
    rzmre: Optional[float] = None
    rzche: Optional[float] = None
    rqye: Optional[float] = None
    rqmcl: Optional[float] = None
    rzrqye: Optional[float] = None
    rqyl: Optional[float] = None

    def to_entity(self) -> "CapMargin":
        from domain.cap_margin.entity import CapMargin
        return CapMargin(**self.model_dump())


class CapMarginVO(BaseModel):
    trade_date: date
    exchange_id: str
    rzye: Optional[float] = None
    rzmre: Optional[float] = None
    rzche: Optional[float] = None
    rqye: Optional[float] = None
    rzrqye: Optional[float] = None
