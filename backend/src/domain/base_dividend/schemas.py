"""base_dividend — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class BaseDividendBO(BaseModel):
    symbol: str
    end_date: date
    ann_date: Optional[date] = None
    record_date: Optional[date] = None
    ex_date: Optional[date] = None
    pay_date: Optional[date] = None
    div_proc: Optional[str] = None
    stk_div: Optional[float] = None
    stk_bo_rate: Optional[float] = None
    stk_co_rate: Optional[float] = None
    cash_div: Optional[float] = None
    cash_div_tax: Optional[float] = None

    def to_entity(self) -> "BaseDividend":
        from domain.base_dividend.entity import BaseDividend
        return BaseDividend(**self.model_dump())


class BaseDividendVO(BaseModel):
    symbol: str
    end_date: date
    ann_date: Optional[date] = None
    record_date: Optional[date] = None
    ex_date: Optional[date] = None
    pay_date: Optional[date] = None
    div_proc: Optional[str] = None
    stk_div: Optional[float] = None
    cash_div: Optional[float] = None
    cash_div_tax: Optional[float] = None
