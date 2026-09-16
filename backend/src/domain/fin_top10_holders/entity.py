"""fin_top10_holders — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class FinTop10Holder:
    """前十大股东"""

    symbol: str
    holder_name: str
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_float_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None
    data_source: str = "tushare"
