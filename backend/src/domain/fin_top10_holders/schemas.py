"""fin_top10_holders — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class FinTop10HolderBO(BaseModel):
    symbol: str
    holder_name: str
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_float_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None

    def to_entity(self) -> "FinTop10Holder":
        from domain.fin_top10_holders.entity import FinTop10Holder
        return FinTop10Holder(**self.model_dump())


class FinTop10HolderVO(BaseModel):
    symbol: str
    holder_name: str
    end_date: Optional[date] = None
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_float_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None
