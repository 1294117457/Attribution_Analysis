"""fundamental 类 BO（每日指标、财报、十大股东）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel

class FinDailyBasicBO(BaseModel):
    symbol: str
    trade_date: date
    close: Optional[float] = None
    turnover_rate: Optional[float] = None
    turnover_rate_f: Optional[float] = None
    volume_ratio: Optional[float] = None
    pe: Optional[float] = None
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    ps_ttm: Optional[float] = None
    dv_ratio: Optional[float] = None
    dv_ttm: Optional[float] = None
    total_share: Optional[float] = None
    float_share: Optional[float] = None
    free_share: Optional[float] = None
    total_mv: Optional[float] = None
    circ_mv: Optional[float] = None
    # §2.7 补 Tushare daily_basic 文档 limit_status 字段
    limit_status: Optional[int] = None


class FinReportBO(BaseModel):
    symbol: str
    end_date: date
    ann_date: Optional[date] = None
    report_type: Optional[str] = None
    comp_type: Optional[str] = None
    # §1.5 补 Tushare income 文档 end_type 字段
    end_type: Optional[str] = None
    basic_eps: Optional[float] = None
    diluted_eps: Optional[float] = None
    total_revenue: Optional[float] = None
    revenue: Optional[float] = None
    operate_profit: Optional[float] = None
    total_profit: Optional[float] = None
    n_income: Optional[float] = None
    n_income_attr_p: Optional[float] = None


class FinTop10HoldersBO(BaseModel):
    symbol: str
    ann_date: Optional[date] = None
    end_date: Optional[date] = None
    holder_name: str
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_float_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None
class FinTop10FloatHoldersBO(BaseModel):
    symbol: str
    ann_date: Optional[date] = None
    end_date: Optional[date] = None
    holder_name: str
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None

__all__ = [
    "FinDailyBasicBO", "FinReportBO",
    "FinTop10HoldersBO", "FinTop10FloatHoldersBO",
]
