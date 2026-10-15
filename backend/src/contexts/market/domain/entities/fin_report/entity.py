"""fin_report — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from shared.domain.base import SymboledEntity


@dataclass
class FinReport(SymboledEntity):
    """财务三大表（主键：symbol + end_date + report_type）"""

    end_date: Optional[date] = None
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


    @classmethod
    def from_bo(cls, bo) -> "FinReport":
        """从 BO 构造 Entity（依赖倒置：Domain 接受 Application 的 BO）

        BO 在 application 层，Entity 在 domain 层；为避免循环依赖，
        此处不显式 import BO，只通过 duck typing 访问 bo 的属性。
        """
        data = bo.model_dump()
        kwargs = {}
        for fname in ['id', 'symbol', 'data_source', 'end_date', 'ann_date', 'report_type', 'comp_type', 'basic_eps', 'diluted_eps', 'total_revenue', 'revenue', 'operate_profit', 'total_profit', 'n_income', 'n_income_attr_p', 'total_assets', 'total_liab', 'total_hldr_eqy_exc_min_int', 'n_cashflow_act', 'n_cash_flows_fnc_act', 'n_cashflow_inv_act']:
            if fname in data:
                kwargs[fname] = data[fname]
            elif fname == "id":
                kwargs[fname] = 0  # 未持久化
            elif fname == "data_source":
                kwargs[fname] = "tushare"
            elif fname == "symbol":
                kwargs[fname] = ""  # SymboledEntity 默认
            # trade_date 保持 None（SymboledDatedEntity 默认）
        return cls(**kwargs)