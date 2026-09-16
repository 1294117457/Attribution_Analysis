"""base_suspend — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class BaseSuspend:
    """停复牌"""

    symbol: str
    trade_date: date
    suspend_timing: Optional[date] = None
    suspend_type: Optional[str] = None
    data_source: str = "tushare"
