"""mkt_sector_daily — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import SymboledEntity


@dataclass
class MktSectorDaily(SymboledEntity):
    """板块行情日线（主键：sector_type + sector_code + trade_date）"""

    sector_type: str = ""
    sector_code: str = ""
    trade_date: Optional[date] = None
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
