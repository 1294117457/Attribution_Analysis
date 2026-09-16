"""cap_margin_detail — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


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
        from domain.cap_margin_detail.entity import CapMarginDetail
        return CapMarginDetail(
            symbol=self.symbol,
            trade_date=self.trade_date,
            rzye=self.rzye, rqye=self.rqye, rzmre=self.rzmre, rqyl=self.rqyl,
            rzche=self.rzche, rqchl=self.rqchl, rqmcl=self.rqmcl, rzrqye=self.rzrqye,
        )


class CapMarginDetailVO(BaseModel):
    symbol: str
    trade_date: date
    rzye: Optional[float] = None
    rqye: Optional[float] = None
    rzmre: Optional[float] = None
    rqyl: Optional[float] = None
    rzrqye: Optional[float] = None
