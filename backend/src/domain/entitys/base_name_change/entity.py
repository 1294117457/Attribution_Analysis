"""base_name_change — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import SymboledEntity


@dataclass
class BaseNameChange(SymboledEntity):
    """股票曾用名（主键：symbol + start_date + name）"""

    name: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    change_reason: Optional[str] = None
