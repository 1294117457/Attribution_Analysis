"""cap_margin — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import SymboledEntity


@dataclass
class CapMargin(SymboledEntity):
    """两融汇总（按交易所，主键：exchange_id + trade_date）"""

    trade_date: Optional[date] = None
    exchange_id: str = ""
    rzye: Optional[float] = None
    rzmre: Optional[float] = None
    rzche: Optional[float] = None
    rqye: Optional[float] = None
    rqmcl: Optional[float] = None
    rzrqye: Optional[float] = None
    rqyl: Optional[float] = None
