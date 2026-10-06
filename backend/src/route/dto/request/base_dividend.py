"""自动迁移自 domain/base_dividend/schemas.py（BO 部分）"""

from __future__ import annotations

from pydantic import BaseModel
from typing import Optional
from datetime import date


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
        from domain.entitys.base_dividend.entity import BaseDividend
        return BaseDividend(**self.model_dump())