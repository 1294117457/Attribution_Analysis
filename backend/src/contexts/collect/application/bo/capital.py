"""capital 类 BO（资金流、融资融券、龙虎榜、大宗交易、股东数）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class CapMoneyflowBO(BaseModel):
    symbol: str
    trade_date: date
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


class CapMarginDetailBO(BaseModel):
    symbol: str
    trade_date: date
    rzye: Optional[float] = None
    rqye: Optional[float] = None
    rzmre: Optional[float] = None
    rqyl: Optional[float] = None
    rzche: Optional[float] = None
    rqchl: Optional[float] = None
    rqmcl: Optional[float] = None
    rzrqye: Optional[float] = None


class CapTopListBO(BaseModel):
    trade_date: date
    symbol: str
    name: Optional[str] = None
    reason: Optional[str] = None
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


class CapTopInstBO(BaseModel):
    trade_date: date
    symbol: str
    exalter: Optional[str] = None
    side: Optional[str] = None
    reason: Optional[str] = None
    buy: Optional[float] = None
    buy_rate: Optional[float] = None
    sell: Optional[float] = None
    sell_rate: Optional[float] = None
    net_buy: Optional[float] = None


class CapBlockTradeBO(BaseModel):
    trade_date: date
    symbol: str
    name: Optional[str] = None
    price: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None


class CapHolderNumBO(BaseModel):
    symbol: str
    ann_date: Optional[date] = None
    end_date: date
    holder_num: Optional[int] = None
    holder_nums: Optional[float] = None


__all__ = [
    "CapMoneyflowBO", "CapMarginDetailBO", "CapTopListBO", "CapTopInstBO",
    "CapBlockTradeBO", "CapHolderNumBO",
]
