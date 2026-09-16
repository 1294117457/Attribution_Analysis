"""mkt_market_daily — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class MktMarketDaily:
    """市场整体行情"""

    market: str
    trade_date: date
    close: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    pre_close: Optional[float] = None
    change: Optional[float] = None
    pct_chg: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
    data_source: str = "tushare"
