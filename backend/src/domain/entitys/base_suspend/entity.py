"""base_suspend — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import SymboledDatedEntity


@dataclass
class BaseSuspend(SymboledDatedEntity):
    """停复牌"""

    suspend_timing: Optional[date] = None
    suspend_type: Optional[str] = None
