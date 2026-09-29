"""财报（利润表）采集 BO"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class FinReportBO(BaseModel):
    """Tushare income 一行（已按报告期去重）"""

    symbol: str
    end_date: date
    ann_date: Optional[date] = None
    report_type: Optional[str] = None
    comp_type: Optional[str] = None
    basic_eps: Optional[float] = None
    diluted_eps: Optional[float] = None
    total_revenue: Optional[float] = None
    revenue: Optional[float] = None
    operate_profit: Optional[float] = None
    total_profit: Optional[float] = None
    n_income: Optional[float] = None
    n_income_attr_p: Optional[float] = None

    def to_entity(self) -> "FinReport":
        from domain.entitys.fin_report.entity import FinReport
        return FinReport(**self.model_dump())
