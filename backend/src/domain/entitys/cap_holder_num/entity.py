"""cap_holder_num — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import SymboledEntity


@dataclass
class CapHolderNum(SymboledEntity):
    """股东户数（主键：symbol + end_date）"""

    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    holder_num: Optional[int] = None
    holder_nums: Optional[float] = None
