"""cap_holder_num — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from shared.domain.base import SymboledEntity


@dataclass
class CapHolderNum(SymboledEntity):
    """股东户数（主键：symbol + end_date）"""

    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    holder_num: Optional[int] = None
    holder_nums: Optional[float] = None


    @classmethod
    def from_bo(cls, bo) -> "CapHolderNum":
        """从 BO 构造 Entity（依赖倒置：Domain 接受 Application 的 BO）

        BO 在 application 层，Entity 在 domain 层；为避免循环依赖，
        此处不显式 import BO，只通过 duck typing 访问 bo 的属性。
        """
        data = bo.model_dump()
        kwargs = {}
        for fname in ['id', 'symbol', 'data_source', 'end_date', 'ann_date', 'holder_num', 'holder_nums']:
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