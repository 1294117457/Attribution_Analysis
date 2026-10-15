"""cap_top_list — 领域实体"""

from dataclasses import dataclass
from typing import Optional

from shared.domain.base import SymboledDatedEntity


@dataclass
class CapTopList(SymboledDatedEntity):
    """龙虎榜汇总"""

    name: Optional[str] = None
    close: Optional[float] = None
    pct_change: Optional[float] = None
    turnover_rate: Optional[float] = None
    amount: Optional[float] = None
    l_sell: Optional[float] = None
    l_buy: Optional[float] = None
    l_amount: Optional[float] = None
    net_amount: Optional[float] = None
    net_rate: Optional[float] = None
    amount_rate: Optional[float] = None
    float_values: Optional[float] = None
    reason: Optional[str] = None


    @classmethod
    def from_bo(cls, bo) -> "CapTopList":
        """从 BO 构造 Entity（依赖倒置：Domain 接受 Application 的 BO）

        BO 在 application 层，Entity 在 domain 层；为避免循环依赖，
        此处不显式 import BO，只通过 duck typing 访问 bo 的属性。
        """
        data = bo.model_dump()
        kwargs = {}
        for fname in ['id', 'symbol', 'data_source', 'name', 'close', 'pct_change', 'turnover_rate', 'amount', 'l_sell', 'l_buy', 'l_amount', 'net_amount', 'net_rate', 'amount_rate', 'float_values', 'reason']:
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