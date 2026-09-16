"""cap_top_inst — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class CapTopInst:
    """龙虎榜机构席位明细"""

    trade_date: date
    symbol: str
    exalter: Optional[str] = None
    side: Optional[str] = None
    buy: Optional[float] = None
    buy_rate: Optional[float] = None
    sell: Optional[float] = None
    sell_rate: Optional[float] = None
    net_buy: Optional[float] = None
    reason: Optional[str] = None
    data_source: str = "tushare"
