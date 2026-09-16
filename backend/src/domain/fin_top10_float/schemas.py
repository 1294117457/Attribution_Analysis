"""fin_top10_float — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class FinTop10FloatHolderBO(BaseModel):
    symbol: str
    holder_name: str
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None

    def to_entity(self) -> "FinTop10FloatHolder":
        from domain.fin_top10_float.entity import FinTop10FloatHolder
        return FinTop10FloatHolder(**self.model_dump())


class FinTop10FloatHolderVO(BaseModel):
    symbol: str
    holder_name: str
    end_date: Optional[date] = None
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None
