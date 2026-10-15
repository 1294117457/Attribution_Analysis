"""fin_top10_holders — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from shared.domain.base import SymboledEntity


@dataclass
class FinTop10Holders(SymboledEntity):
    """前十大股东（主键：symbol + holder_name + end_date）"""

    holder_name: str = ""
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_float_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None


    @classmethod
    def from_bo(cls, bo) -> "FinTop10Holders":
        """从 BO 构造 Entity（依赖倒置：Domain 接受 Application 的 BO）

        BO 在 application 层，Entity 在 domain 层；为避免循环依赖，
        此处不显式 import BO，只通过 duck typing 访问 bo 的属性。
        """
        data = bo.model_dump()
        kwargs = {}
        for fname in ['id', 'symbol', 'data_source', 'holder_name', 'end_date', 'ann_date', 'hold_amount', 'hold_ratio', 'hold_float_ratio', 'hold_change', 'holder_type']:
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