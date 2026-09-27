"""base_dividend — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import SymboledEntity


@dataclass
class BaseDividend(SymboledEntity):
    """分红送股（主键：symbol + end_date）"""

    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    record_date: Optional[date] = None
    ex_date: Optional[date] = None
    pay_date: Optional[date] = None
    div_proc: Optional[str] = None
    stk_div: Optional[float] = None
    stk_bo_rate: Optional[float] = None
    stk_co_rate: Optional[float] = None
    cash_div: Optional[float] = None
    cash_div_tax: Optional[float] = None
