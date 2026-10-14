"""资金面 Port：资金流向 / 融资融券 / 龙虎榜 / 大宗交易 / 股东户数"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from contexts.data.application.port.base import DataPort
from contexts.data.application.port.types import Symbol, TradeDate, TradeDateParams

from contexts.market.domain.cap_moneyflow.bo import CapMoneyflowBO
from contexts.market.domain.cap_margin_detail.bo import CapMarginDetailBO
from contexts.market.domain.cap_top_list.bo import CapTopListBO
from contexts.market.domain.cap_top_inst.bo import CapTopInstBO
from contexts.market.domain.cap_block_trade.bo import CapBlockTradeBO
from contexts.market.domain.cap_holder_num.bo import CapHolderNumBO

# ═══════════════════════════════════════════════════════════════════════════════
# BO
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
