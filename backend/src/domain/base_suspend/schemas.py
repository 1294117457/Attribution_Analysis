"""base_suspend — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class BaseSuspendBO(BaseModel):
    symbol: str
    trade_date: date
    suspend_timing: Optional[date] = None
    suspend_type: Optional[str] = None

    def to_entity(self) -> "BaseSuspend":
        from domain.base_suspend.entity import BaseSuspend
        return BaseSuspend(**self.model_dump())


class BaseSuspendVO(BaseModel):
    symbol: str
    trade_date: date
    suspend_timing: Optional[date] = None
    suspend_type: Optional[str] = None
