"""fin_report — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class FinReport:
    """财务报表"""

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

    total_assets: Optional[float] = None
    total_liab: Optional[float] = None
    total_hldr_eqy_exc_min_int: Optional[float] = None

    n_cashflow_act: Optional[float] = None
    n_cash_flows_fnc_act: Optional[float] = None
    n_cashflow_inv_act: Optional[float] = None

    data_source: str = "tushare"
