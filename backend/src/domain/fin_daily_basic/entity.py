"""fin_daily_basic — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class FinDailyBasic:
    """日频估值"""

    symbol: str
    trade_date: date
    close: Optional[float] = None
    turnover_rate: Optional[float] = None
    turnover_rate_f: Optional[float] = None
    volume_ratio: Optional[float] = None
    pe: Optional[float] = None
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    ps_ttm: Optional[float] = None
    dv_ratio: Optional[float] = None
    dv_ttm: Optional[float] = None
    total_share: Optional[float] = None
    float_share: Optional[float] = None
    free_share: Optional[float] = None
    total_mv: Optional[float] = None
    circ_mv: Optional[float] = None
    data_source: str = "tushare"
