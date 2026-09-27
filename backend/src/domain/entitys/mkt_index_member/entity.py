"""mkt_index_member — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import SymboledEntity


@dataclass
class MktIndexMember(SymboledEntity):
    """指数成分股（主键：sector_type + sector_code + symbol）"""

    sector_type: str = ""
    sector_code: str = ""
    sector_name: Optional[str] = None
    name: Optional[str] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    is_new: Optional[str] = None
