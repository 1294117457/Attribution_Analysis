"""mkt_market_daily — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class MktMarketDailyBO(BaseModel):
    market: str
    trade_date: date
    close: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    pre_close: Optional[float] = None
    change: Optional[float] = None
    pct_chg: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None

    def to_entity(self) -> "MktMarketDaily":
        from domain.mkt_market_daily.entity import MktMarketDaily
        return MktMarketDaily(**self.model_dump())


class MktMarketDailyVO(BaseModel):
    market: str
    trade_date: date
    close: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    pre_close: Optional[float] = None
    change: Optional[float] = None
    pct_chg: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
