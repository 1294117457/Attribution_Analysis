"""mkt_sector_daily — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class MktSectorDailyBO(BaseModel):
    sector_type: str
    sector_code: str
    trade_date: date
    sector_name: Optional[str] = None
    close: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    pre_close: Optional[float] = None
    change: Optional[float] = None
    pct_change: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
    turnover_rate: Optional[float] = None

    def to_entity(self) -> "MktSectorDaily":
        from domain.mkt_sector_daily.entity import MktSectorDaily
        return MktSectorDaily(**self.model_dump())


class MktSectorDailyVO(BaseModel):
    sector_type: str
    sector_code: str
    sector_name: Optional[str] = None
    trade_date: date
    close: Optional[float] = None
    pct_change: Optional[float] = None
    amount: Optional[float] = None
    turnover_rate: Optional[float] = None
