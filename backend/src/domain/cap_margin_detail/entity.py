"""cap_margin_detail — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class CapMarginDetail:
    """个股两融明细"""

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
    data_source: str = "tushare"
