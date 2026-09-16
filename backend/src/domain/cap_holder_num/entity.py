"""cap_holder_num — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class CapHolderNum:
    """股东户数"""

    symbol: str
    end_date: date
    ann_date: Optional[date] = None
    holder_num: Optional[int] = None
    holder_nums: Optional[float] = None
    data_source: str = "tushare"
