"""base_name_change — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class BaseNameChange:
    """股票曾用名"""

    symbol: str
    name: str
    start_date: date
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    change_reason: Optional[str] = None
    data_source: str = "tushare"
