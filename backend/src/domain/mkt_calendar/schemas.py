"""mkt_calendar — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class MktCalendarBO(BaseModel):
    exchange: str
    cal_date: date
    is_open: bool = True
    pretrade_date: Optional[date] = None

    def to_entity(self) -> "MktCalendar":
        from domain.mkt_calendar.entity import MktCalendar
        return MktCalendar(**self.model_dump())


class MktCalendarVO(BaseModel):
    exchange: str
    cal_date: date
    is_open: bool
    pretrade_date: Optional[date] = None
