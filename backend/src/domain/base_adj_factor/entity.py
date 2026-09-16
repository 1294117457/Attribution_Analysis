"""base_adj_factor — 领域实体"""

from dataclasses import dataclass
from datetime import date


@dataclass
class BaseAdjFactor:
    """复权因子"""

    symbol: str
    trade_date: date
    adj_factor: float
    data_source: str = "tushare"
