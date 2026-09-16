"""mkt_index_member — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class MktIndexMember:
    """板块成分"""

    sector_type: str
    sector_code: str
    symbol: str
    sector_name: Optional[str] = None
    name: Optional[str] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    is_new: Optional[str] = None
    data_source: str = "tushare"
