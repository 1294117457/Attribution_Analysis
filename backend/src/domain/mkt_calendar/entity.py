"""mkt_calendar — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class MktCalendar:
    """交易日历"""

    exchange: str
    cal_date: date
    is_open: bool = True
    pretrade_date: Optional[date] = None
    data_source: str = "tushare"
