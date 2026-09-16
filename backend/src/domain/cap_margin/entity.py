"""cap_margin — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class CapMargin:
    """两融汇总（按交易所）"""

    trade_date: date
    exchange_id: str
    rzye: Optional[float] = None
    rzmre: Optional[float] = None
    rzche: Optional[float] = None
    rqye: Optional[float] = None
    rqmcl: Optional[float] = None
    rzrqye: Optional[float] = None
    rqyl: Optional[float] = None
    data_source: str = "tushare"
