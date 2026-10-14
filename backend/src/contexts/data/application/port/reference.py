"""基础资料 Port：股票基本信息 / 复权因子 / 停复牌 / 曾用名 / 分红送股"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from contexts.data.application.port.base import DataPort
from contexts.data.application.port.types import ListStatus, Symbol, SymbolParams, TradeDateParams

from contexts.market.domain.stock_info.bo import StockInfoBO
from contexts.market.domain.base_adj_factor.bo import BaseAdjFactorBO
from contexts.market.domain.base_suspend.bo import BaseSuspendBO
from contexts.market.domain.base_name_change.bo import BaseNameChangeBO
from contexts.market.domain.base_dividend.bo import BaseDividendBO

# ═══════════════════════════════════════════════════════════════════════════════
# BO
# ═══════════════════════════════════════════════════════════════════════════════

class StockBasicParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    list_status: ListStatus = ListStatus.LISTED

class NameChangeParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: Optional[Symbol] = None            # 不传则拉全市场

# ═══════════════════════════════════════════════════════════════════════════════
# Port
# ═══════════════════════════════════════════════════════════════════════════════

class StockBasicPort(DataPort[StockBasicParams, StockInfoBO]):
    name, label = "stock_basic", "股票基本信息"
    facet, sub_facet = "fundamental", "core"
    description = "全量代码/名称/行业/上市信息（5000+ 只）"
    Params, Item = StockBasicParams, StockInfoBO
    sample_params = {"list_status": "L"}

class AdjFactorPort(DataPort[SymbolParams, BaseAdjFactorBO]):
    name, label = "adj_factor", "复权因子"
    facet, sub_facet = "tech", "base"
    description = "前/后复权计算（tushare adj_factor）"
    Params, Item = SymbolParams, BaseAdjFactorBO
    unit = "symbol"
    sample_params = {"symbol": "600519"}

class SuspendPort(DataPort[TradeDateParams, BaseSuspendBO]):
    name, label = "suspend", "停复牌"
    facet, sub_facet = "tech", "base"
    description = "K 线断点标识（tushare suspend_d）"
    Params, Item = TradeDateParams, BaseSuspendBO
    unit = "trade_date"
    sample_params = {"trade_date": "20260105"}

class NameChangePort(DataPort[NameChangeParams, BaseNameChangeBO]):
    name, label = "name_change", "股票曾用名"
    facet, sub_facet = "tech", "base"
    description = "历史 K 线展示（tushare namechange）"
    Params, Item = NameChangeParams, BaseNameChangeBO
    unit = "symbol"
    sample_params = {"symbol": "600519"}

class DividendPort(DataPort[SymbolParams, BaseDividendBO]):
    name, label = "dividend", "分红送股"
    facet, sub_facet = "fundamental", "dividend"
    description = "复权事件 + 高股息筛选（tushare dividend）"
    Params, Item = SymbolParams, BaseDividendBO
    unit = "symbol"
    sample_params = {"symbol": "600519"}

__all__ = [
    "AdjFactorPort",
    "BaseAdjFactorBO",
    "BaseDividendBO",
    "BaseNameChangeBO",
    "BaseSuspendBO",
    "DividendPort",
    "NameChangeParams",
    "NameChangePort",
    "StockBasicParams",
    "StockBasicPort",
    "StockInfoBO",
    "SuspendPort",
]
