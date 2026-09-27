"""fin_top10_float — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import SymboledEntity


@dataclass
class FinTop10Float(SymboledEntity):
    """前十大流通股东（主键：symbol + holder_name + end_date）"""

    holder_name: str = ""
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None
