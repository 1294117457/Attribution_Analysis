"""base_name_change — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class BaseNameChangeBO(BaseModel):
    symbol: str
    name: str
    start_date: date
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    change_reason: Optional[str] = None

    def to_entity(self) -> "BaseNameChange":
        from domain.base_name_change.entity import BaseNameChange
        return BaseNameChange(**self.model_dump())


class BaseNameChangeVO(BaseModel):
    symbol: str
    name: str
    start_date: date
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    change_reason: Optional[str] = None
