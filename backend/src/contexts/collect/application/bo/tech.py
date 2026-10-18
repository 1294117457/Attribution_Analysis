"""tech / base 类 BO（K 线、复权因子、停牌、名称变更、分红）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class BaseAdjFactorBO(BaseModel):
    symbol: str
    trade_date: date
    adj_factor: float


class BaseSuspendBO(BaseModel):
    symbol: str
    trade_date: date
    suspend_timing: Optional[date] = None
    suspend_type: Optional[str] = None


class BaseNameChangeBO(BaseModel):
    symbol: str
    name: str
    start_date: date
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    change_reason: Optional[str] = None


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


__all__ = [
    "BaseAdjFactorBO", "BaseSuspendBO", "BaseNameChangeBO", "BaseDividendBO",
]
