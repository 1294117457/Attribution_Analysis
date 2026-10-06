"""自动迁移自 domain/base_name_change/schemas.py（BO 部分）"""

from __future__ import annotations

from pydantic import BaseModel
from typing import Optional
from datetime import date


class BaseNameChangeBO(BaseModel):
    symbol: str
    name: str
    start_date: date
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    change_reason: Optional[str] = None

    def to_entity(self) -> "BaseNameChange":
        from domain.entitys.base_name_change.entity import BaseNameChange
        return BaseNameChange(**self.model_dump())