"""自动迁移自 domain/base_suspend/schemas.py（BO 部分）"""

from __future__ import annotations

from pydantic import BaseModel
from typing import Optional
from datetime import date


class BaseSuspendBO(BaseModel):
    symbol: str
    trade_date: date
    suspend_timing: Optional[date] = None
    suspend_type: Optional[str] = None

    def to_entity(self) -> "BaseSuspend":
        from domain.entitys.base_suspend.entity import BaseSuspend
        return BaseSuspend(**self.model_dump())