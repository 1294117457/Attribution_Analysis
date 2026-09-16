"""cap_moneyflow — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class CapMoneyflowBO(BaseModel):
    """资金流向 BO（采集层产出）"""

    symbol: str = Field(..., description="股票代码")
    trade_date: date = Field(..., description="交易日期")
    buy_sm_vol: Optional[float] = None
    buy_sm_amount: Optional[float] = None
    sell_sm_vol: Optional[float] = None
    sell_sm_amount: Optional[float] = None
    buy_md_vol: Optional[float] = None
    buy_md_amount: Optional[float] = None
    sell_md_vol: Optional[float] = None
    sell_md_amount: Optional[float] = None
    buy_lg_vol: Optional[float] = None
    buy_lg_amount: Optional[float] = None
    sell_lg_vol: Optional[float] = None
    sell_lg_amount: Optional[float] = None
    buy_elg_vol: Optional[float] = None
    buy_elg_amount: Optional[float] = None
    sell_elg_vol: Optional[float] = None
    sell_elg_amount: Optional[float] = None
    net_mf_vol: Optional[float] = None
    net_mf_amount: Optional[float] = None

    def to_entity(self) -> "CapMoneyflow":
        from domain.cap_moneyflow.entity import CapMoneyflow
        return CapMoneyflow(
            symbol=self.symbol,
            trade_date=self.trade_date,
            buy_sm_vol=self.buy_sm_vol,
            buy_sm_amount=self.buy_sm_amount,
            sell_sm_vol=self.sell_sm_vol,
            sell_sm_amount=self.sell_sm_amount,
            buy_md_vol=self.buy_md_vol,
            buy_md_amount=self.buy_md_amount,
            sell_md_vol=self.sell_md_vol,
            sell_md_amount=self.sell_md_amount,
            buy_lg_vol=self.buy_lg_vol,
            buy_lg_amount=self.buy_lg_amount,
            sell_lg_vol=self.sell_lg_vol,
            sell_lg_amount=self.sell_lg_amount,
            buy_elg_vol=self.buy_elg_vol,
            buy_elg_amount=self.buy_elg_amount,
            sell_elg_vol=self.sell_elg_vol,
            sell_elg_amount=self.sell_elg_amount,
            net_mf_vol=self.net_mf_vol,
            net_mf_amount=self.net_mf_amount,
        )


class CapMoneyflowVO(BaseModel):
    """资金流向 VO（API 出参）"""

    symbol: str
    trade_date: date
    net_mf_amount: Optional[float] = None
    net_mf_vol: Optional[float] = None
    buy_lg_amount: Optional[float] = None
    sell_lg_amount: Optional[float] = None
    buy_elg_amount: Optional[float] = None
    sell_elg_amount: Optional[float] = None
    buy_sm_amount: Optional[float] = None
    sell_sm_amount: Optional[float] = None
    buy_md_amount: Optional[float] = None
    sell_md_amount: Optional[float] = None
