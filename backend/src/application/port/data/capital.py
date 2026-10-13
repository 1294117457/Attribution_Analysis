"""资金面 Port：资金流向 / 融资融券 / 龙虎榜 / 大宗交易 / 股东户数"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from application.port.data.base import DataPort
from application.port.data.types import Symbol, TradeDate, TradeDateParams


# ═══════════════════════════════════════════════════════════════════════════════
# BO
# ═══════════════════════════════════════════════════════════════════════════════


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

    def to_entity(self) -> "CapMoneyflow":
        from domain.entitys.cap_moneyflow.entity import CapMoneyflow
        return CapMoneyflow(**self.model_dump())


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

    def to_entity(self) -> "CapMarginDetail":
        from domain.entitys.cap_margin_detail.entity import CapMarginDetail
        return CapMarginDetail(**self.model_dump())


class CapTopListBO(BaseModel):
    trade_date: date
    symbol: str
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

    def to_entity(self) -> "CapTopList":
        from domain.entitys.cap_top_list.entity import CapTopList
        return CapTopList(**self.model_dump())


class CapTopInstBO(BaseModel):
    trade_date: date
    symbol: str
    exalter: Optional[str] = None
    side: Optional[str] = None
    buy: Optional[float] = None
    buy_rate: Optional[float] = None
    sell: Optional[float] = None
    sell_rate: Optional[float] = None
    net_buy: Optional[float] = None
    reason: Optional[str] = None

    def to_entity(self) -> "CapTopInst":
        from domain.entitys.cap_top_inst.entity import CapTopInst
        return CapTopInst(**self.model_dump())


class CapBlockTradeBO(BaseModel):
    trade_date: date
    symbol: str
    name: Optional[str] = None
    price: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None

    def to_entity(self) -> "CapBlockTrade":
        from domain.entitys.cap_block_trade.entity import CapBlockTrade
        return CapBlockTrade(**self.model_dump())


class CapHolderNumBO(BaseModel):
    symbol: str
    ann_date: Optional[date] = None
    end_date: date
    holder_num: Optional[int] = None
    holder_nums: Optional[float] = None

    def to_entity(self) -> "CapHolderNum":
        from domain.entitys.cap_holder_num.entity import CapHolderNum
        return CapHolderNum(**self.model_dump())


# ═══════════════════════════════════════════════════════════════════════════════
# Params
# ═══════════════════════════════════════════════════════════════════════════════


class MoneyflowParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trade_date: TradeDate
    symbols: Optional[list[Symbol]] = None


class HolderNumberParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: Symbol
    ann_date: Optional[TradeDate] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Port
# ═══════════════════════════════════════════════════════════════════════════════


class MoneyflowPort(DataPort[MoneyflowParams, CapMoneyflowBO]):
    name, label = "moneyflow", "个股资金流向"
    facet, sub_facet = "capital", "moneyflow"
    description = "大小单净额、净流入（tushare moneyflow）"
    Params, Item = MoneyflowParams, CapMoneyflowBO
    unit = "trade_date"
    sample_params = {"trade_date": "20260105"}


class MarginDetailPort(DataPort[TradeDateParams, CapMarginDetailBO]):
    name, label = "margin_detail", "个股融资融券"
    facet, sub_facet = "capital", "margin"
    description = "融资余额 / 融券余额（tushare margin_detail）"
    Params, Item = TradeDateParams, CapMarginDetailBO
    unit = "trade_date"
    sample_params = {"trade_date": "20260105"}


class TopListPort(DataPort[TradeDateParams, CapTopListBO]):
    name, label = "top_list", "龙虎榜每日"
    facet, sub_facet = "capital", "dragon_tiger"
    description = "上榜汇总 + 净买卖额（tushare top_list）"
    Params, Item = TradeDateParams, CapTopListBO
    unit = "trade_date"
    sample_params = {"trade_date": "20260105"}


class TopInstPort(DataPort[TradeDateParams, CapTopInstBO]):
    name, label = "top_inst", "龙虎榜机构"
    facet, sub_facet = "capital", "dragon_tiger"
    description = "机构席位买卖明细（tushare top_inst）"
    Params, Item = TradeDateParams, CapTopInstBO
    unit = "trade_date"
    sample_params = {"trade_date": "20260105"}


class BlockTradePort(DataPort[TradeDateParams, CapBlockTradeBO]):
    name, label = "block_trade", "大宗交易"
    facet, sub_facet = "capital", "block_trade"
    description = "折溢价 + 买卖方营业部（tushare block_trade）"
    Params, Item = TradeDateParams, CapBlockTradeBO
    unit = "trade_date"
    sample_params = {"trade_date": "20260105"}


class HolderNumberPort(DataPort[HolderNumberParams, CapHolderNumBO]):
    name, label = "holder_number", "股东户数"
    facet, sub_facet = "capital", "chip"
    description = "股东户数 + 季频（tushare stk_holdernumber）"
    Params, Item = HolderNumberParams, CapHolderNumBO
    unit = "symbol"
    sample_params = {"symbol": "600519"}


__all__ = [
    "BlockTradePort",
    "CapBlockTradeBO",
    "CapHolderNumBO",
    "CapMarginDetailBO",
    "CapMoneyflowBO",
    "CapTopInstBO",
    "CapTopListBO",
    "HolderNumberParams",
    "HolderNumberPort",
    "MarginDetailPort",
    "MoneyflowParams",
    "MoneyflowPort",
    "TopInstPort",
    "TopListPort",
]
