"""基础资料 Port：股票基本信息 / 复权因子 / 停复牌 / 曾用名 / 分红送股"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from contexts.data.application.port.base import DataPort
from contexts.data.application.port.types import ListStatus, Symbol, SymbolParams, TradeDateParams


# ═══════════════════════════════════════════════════════════════════════════════
# BO
# ═══════════════════════════════════════════════════════════════════════════════


class StockInfoBO(BaseModel):
    """股票信息业务对象（字段对齐 Tushare stock_basic）"""

    symbol: str = Field(..., description="股票代码（6位）")
    ts_code: Optional[str] = Field(None, description="Tushare 统一代码")
    name: str = Field("", description="股票名称")
    area: Optional[str] = Field(None, description="地域")
    industry: Optional[str] = Field(None, description="行业")
    market: Optional[str] = Field(None, description="市场类型")
    exchange: Optional[str] = Field(None, description="交易所 SSE/SZSE/BSE")
    list_date: Optional[date] = Field(None, description="上市日期")
    delist_date: Optional[date] = Field(None, description="退市日期")
    list_status: Optional[str] = Field("L", description="上市状态 L/D/P")
    is_hs: Optional[str] = Field("N", description="沪深港通 N/H/S")
    act_name: Optional[str] = Field(None, description="实控人名称")
    act_ent_type: Optional[str] = Field(None, description="实控人企业性质")

    def to_entity(self, id: int = 0) -> "StockInfo":
        """转换为领域实体"""
        from contexts.market.domain.stock_info.entity import StockInfo
        return StockInfo.create(
            id=id,
            symbol=self.symbol,
            name=self.name,
            industry=self.industry,
            market=self.market,
            area=self.area,
            exchange=self.exchange,
            list_date=self.list_date,
            delist_date=self.delist_date,
            list_status=self.list_status,
            is_hs=self.is_hs,
            act_name=self.act_name,
            act_ent_type=self.act_ent_type,
            ts_code=self.ts_code,
        )


class BaseAdjFactorBO(BaseModel):
    symbol: str
    trade_date: date
    adj_factor: float

    def to_entity(self) -> "BaseAdjFactor":
        from contexts.market.domain.base_adj_factor.entity import BaseAdjFactor
        return BaseAdjFactor(**self.model_dump())


class BaseSuspendBO(BaseModel):
    symbol: str
    trade_date: date
    suspend_timing: Optional[date] = None
    suspend_type: Optional[str] = None

    def to_entity(self) -> "BaseSuspend":
        from contexts.market.domain.base_suspend.entity import BaseSuspend
        return BaseSuspend(**self.model_dump())


class BaseNameChangeBO(BaseModel):
    symbol: str
    name: str
    start_date: date
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    change_reason: Optional[str] = None

    def to_entity(self) -> "BaseNameChange":
        from contexts.market.domain.base_name_change.entity import BaseNameChange
        return BaseNameChange(**self.model_dump())


class BaseDividendBO(BaseModel):
    symbol: str
    end_date: date
    ann_date: Optional[date] = None
    record_date: Optional[date] = None
    ex_date: Optional[date] = None
    pay_date: Optional[date] = None
    div_proc: Optional[str] = None
    stk_div: Optional[float] = None
    stk_bo_rate: Optional[float] = None
    stk_co_rate: Optional[float] = None
    cash_div: Optional[float] = None
    cash_div_tax: Optional[float] = None

    def to_entity(self) -> "BaseDividend":
        from contexts.market.domain.base_dividend.entity import BaseDividend
        return BaseDividend(**self.model_dump())


# ═══════════════════════════════════════════════════════════════════════════════
# Params
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
