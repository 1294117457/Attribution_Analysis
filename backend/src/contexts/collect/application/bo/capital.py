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


# §1.2 新增 — Tushare moneyflow_hsgt 接口（按股票粒度，对齐文档 12 字段）
class CapMoneyflowHsgtBO(BaseModel):
    """沪深港通资金流向（按股票）"""
    trade_date: date
    symbol: str
    name: Optional[str] = None
    market_type: str                          # 1=沪市 / 3=深市
    close: Optional[float] = None
    p_change: Optional[float] = None          # 涨跌额(元) — 文档字段 change
    pct_change: Optional[float] = None        # 涨跌幅(%)
    rank: Optional[int] = None
    amount: Optional[float] = None
    net_amount: Optional[float] = None
    buy: Optional[float] = None
    sell: Optional[float] = None


# §1.4 新增 — Tushare hsgt_top10 接口（按股票+rank 粒度，对齐文档 11 字段）
class CapHsgtTop10BO(BaseModel):
    """沪深股通十大成交股"""
    trade_date: date
    symbol: str
    name: Optional[str] = None
    market_type: str                          # 1=沪市 / 3=深市
    rank: int
    close: Optional[float] = None
    p_change: Optional[float] = None          # 涨跌额(元) — 文档字段 change
    amount: Optional[float] = None
    net_amount: Optional[float] = None
    buy: Optional[float] = None
    sell: Optional[float] = None


# §1.3 新增 — Tushare limit_list_d 接口（按股票+limit_type 粒度，对齐文档 18 字段）
class CapLimitListDBO(BaseModel):
    """每日涨跌停列表"""
    trade_date: date
    symbol: str
    industry: Optional[str] = None
    name: Optional[str] = None
    close: Optional[float] = None
    pct_chg: Optional[float] = None
    amount: Optional[float] = None
    limit_amount: Optional[float] = None
    float_mv: Optional[float] = None
    total_mv: Optional[float] = None
    turnover_ratio: Optional[float] = None
    fd_amount: Optional[float] = None
    first_time: Optional[str] = None         # 字符串时间如 "093000"
    last_time: Optional[str] = None
    open_times: Optional[int] = None
    up_stat: Optional[str] = None
    limit_times: Optional[int] = None
    limit_type: str                          # D=跌停/U=涨停/Z=炸板 — 文档字段 limit


class CapMarginDetailBO(BaseModel):
    symbol: str
    name: Optional[str] = None               # §2.3 补 Tushare margin_detail 文档
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
    "CapMoneyflowBO",
    "CapMoneyflowHsgtBO", "CapHsgtTop10BO", "CapLimitListDBO",  # §1.2/1.3/1.4
    "CapMarginDetailBO", "CapTopListBO", "CapTopInstBO",
    "CapBlockTradeBO", "CapHolderNumBO",
]
