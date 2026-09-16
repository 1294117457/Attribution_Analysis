"""cap_moneyflow — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class CapMoneyflow:
    """个股资金流向（领域实体）

    一行 = (symbol, trade_date)
    """

    symbol: str
    trade_date: date
    # 小单
    buy_sm_vol: Optional[float] = None
    buy_sm_amount: Optional[float] = None
    sell_sm_vol: Optional[float] = None
    sell_sm_amount: Optional[float] = None
    # 中单
    buy_md_vol: Optional[float] = None
    buy_md_amount: Optional[float] = None
    sell_md_vol: Optional[float] = None
    sell_md_amount: Optional[float] = None
    # 大单
    buy_lg_vol: Optional[float] = None
    buy_lg_amount: Optional[float] = None
    sell_lg_vol: Optional[float] = None
    sell_lg_amount: Optional[float] = None
    # 特大单
    buy_elg_vol: Optional[float] = None
    buy_elg_amount: Optional[float] = None
    sell_elg_vol: Optional[float] = None
    sell_elg_amount: Optional[float] = None
    # 净流入
    net_mf_vol: Optional[float] = None
    net_mf_amount: Optional[float] = None
    data_source: str = "tushare"

    @property
    def net_large(self) -> Optional[float]:
        """大单净流入（买入减卖出）"""
        if self.buy_lg_amount is None or self.sell_lg_amount is None:
            return None
        return self.buy_lg_amount - self.sell_lg_amount

    @property
    def net_extra_large(self) -> Optional[float]:
        """特大单净流入"""
        if self.buy_elg_amount is None or self.sell_elg_amount is None:
            return None
        return self.buy_elg_amount - self.sell_elg_amount
