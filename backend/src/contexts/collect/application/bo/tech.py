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
    # §2.1 修复：Tushare 文档 suspend_timing 是字符串（如 "09:30-10:00"），不是 date
    suspend_timing: Optional[str] = None
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
    # §2.8 补 Tushare dividend 文档字段
    div_listdate: Optional[date] = None     # 红股上市日
    imp_ann_date: Optional[date] = None     # 实施公告日


__all__ = [
    "BaseAdjFactorBO", "BaseSuspendBO", "BaseNameChangeBO", "BaseDividendBO",
]
