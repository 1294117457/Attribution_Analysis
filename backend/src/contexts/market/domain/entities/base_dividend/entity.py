"""base_dividend — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from shared.domain.base import SymboledEntity


@dataclass
class BaseDividend(SymboledEntity):
    """分红送股（主键：symbol + end_date）"""

    end_date: Optional[date] = None
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


    @classmethod
    def from_bo(cls, bo) -> "BaseDividend":
        """从 BO 构造 Entity（依赖倒置：Domain 接受 Application 的 BO）

        BO 在 application 层，Entity 在 domain 层；为避免循环依赖，
        此处不显式 import BO，只通过 duck typing 访问 bo 的属性。
        """
        data = bo.model_dump()
        kwargs = {}
        for fname in ['id', 'symbol', 'data_source', 'end_date', 'ann_date', 'record_date', 'ex_date', 'pay_date', 'div_proc', 'stk_div', 'stk_bo_rate', 'stk_co_rate', 'cash_div', 'cash_div_tax']:
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