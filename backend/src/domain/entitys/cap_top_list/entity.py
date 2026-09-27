"""cap_top_list — 领域实体"""

from dataclasses import dataclass
from typing import Optional

from domain.base import SymboledDatedEntity


@dataclass
class CapTopList(SymboledDatedEntity):
    """龙虎榜汇总"""

    name: Optional[str] = None
    close: Optional[float] = None
    pct_change: Optional[float] = None
    turnover_rate: Optional[float] = None
    amount: Optional[float] = None
    l_sell: Optional[float] = None
    l_buy: Optional[float] = None
    l_amount: Optional[float] = None
    net_amount: Optional[float] = None
    net_rate: Optional[float] = None
    amount_rate: Optional[float] = None
    float_values: Optional[float] = None
    reason: Optional[str] = None
