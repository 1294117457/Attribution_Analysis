"""mkt_market_daily — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import SymboledEntity


@dataclass
class MktMarketDaily(SymboledEntity):
    """市场行情日线（主键：market + trade_date）"""

    market: str = ""
    trade_date: Optional[date] = None
    close: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    pre_close: Optional[float] = None
    change: Optional[float] = None
    pct_chg: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
