"""cap_holder_num — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class CapHolderNumBO(BaseModel):
    symbol: str
    end_date: date
    ann_date: Optional[date] = None
    holder_num: Optional[int] = None
    holder_nums: Optional[float] = None

    def to_entity(self) -> "CapHolderNum":
        from domain.cap_holder_num.entity import CapHolderNum
        return CapHolderNum(**self.model_dump())


class CapHolderNumVO(BaseModel):
    symbol: str
    end_date: date
    ann_date: Optional[date] = None
    holder_num: Optional[int] = None
    holder_nums: Optional[float] = None
