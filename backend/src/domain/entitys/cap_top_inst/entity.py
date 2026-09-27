"""cap_top_inst — 领域实体"""

from dataclasses import dataclass
from typing import Optional

from domain.base import SymboledDatedEntity


@dataclass
class CapTopInst(SymboledDatedEntity):
    """龙虎榜机构明细"""

    exalter: Optional[str] = None
    side: Optional[str] = None
    buy: Optional[float] = None
    buy_rate: Optional[float] = None
    sell: Optional[float] = None
    sell_rate: Optional[float] = None
    net_buy: Optional[float] = None
    reason: Optional[str] = None
