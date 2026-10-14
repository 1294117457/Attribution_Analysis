"""基本面 Port：日频估值 / 利润表 / 前十大股东"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from contexts.data.application.port.base import DataPort
from contexts.data.application.port.types import Symbol, TradeDate, TradeDateParams


# ═══════════════════════════════════════════════════════════════════════════════
# BO
# ═══════════════════════════════════════════════════════════════════════════════


class FinDailyBasicBO(BaseModel):
    symbol: str
    trade_date: date
    close: Optional[float] = None
    turnover_rate: Optional[float] = None
    turnover_rate_f: Optional[float] = None
    volume_ratio: Optional[float] = None
    pe: Optional[float] = None
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    ps_ttm: Optional[float] = None
    dv_ratio: Optional[float] = None
    dv_ttm: Optional[float] = None
    total_share: Optional[float] = None
    float_share: Optional[float] = None
    free_share: Optional[float] = None
    total_mv: Optional[float] = None
    circ_mv: Optional[float] = None

    def to_entity(self) -> "FinDailyBasic":
        from domain.entitys.fin_daily_basic.entity import FinDailyBasic
        return FinDailyBasic(**self.model_dump())


class FinReportBO(BaseModel):
    """Tushare income 一行（已按报告期去重）"""

    symbol: str
    end_date: date
    ann_date: Optional[date] = None
    report_type: Optional[str] = None
    comp_type: Optional[str] = None
    basic_eps: Optional[float] = None
    diluted_eps: Optional[float] = None
    total_revenue: Optional[float] = None
    revenue: Optional[float] = None
    operate_profit: Optional[float] = None
    total_profit: Optional[float] = None
    n_income: Optional[float] = None
    n_income_attr_p: Optional[float] = None

    def to_entity(self) -> "FinReport":
        from domain.entitys.fin_report.entity import FinReport
        return FinReport(**self.model_dump())


class FinTop10HoldersBO(BaseModel):
    symbol: str
    ann_date: Optional[date] = None
    end_date: Optional[date] = None
    holder_name: str
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_float_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None

    def to_entity(self) -> "FinTop10Holders":
        from domain.entitys.fin_top10_holders.entity import FinTop10Holders
        return FinTop10Holders(**self.model_dump())


class FinTop10FloatHoldersBO(BaseModel):
    symbol: str
    ann_date: Optional[date] = None
    end_date: Optional[date] = None
    holder_name: str
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None

    def to_entity(self) -> "FinTop10Float":
        from domain.entitys.fin_top10_float.entity import FinTop10Float
        return FinTop10Float(**self.model_dump())


# ═══════════════════════════════════════════════════════════════════════════════
# Params
# ═══════════════════════════════════════════════════════════════════════════════


class FinIncomeParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: Symbol
    start_date: Optional[TradeDate] = None    # 按公告日过滤
    end_date: Optional[TradeDate] = None


class Top10HoldersParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: Symbol
    period: Optional[TradeDate] = None        # 报告期，不传取全部


# ═══════════════════════════════════════════════════════════════════════════════
# Port
# ═══════════════════════════════════════════════════════════════════════════════


class DailyBasicPort(DataPort[TradeDateParams, FinDailyBasicBO]):
    name, label = "daily_basic", "日频估值"
    facet, sub_facet = "fundamental", "valuation"
    description = "PE / PB / PS / 股息率 + 股本市值 + 换手率 / 量比"
    Params, Item = TradeDateParams, FinDailyBasicBO
    unit = "trade_date"
    sample_params = {"trade_date": "20260105"}


class FinIncomePort(DataPort[FinIncomeParams, FinReportBO]):
    name, label = "fin_income", "季报财务"
    facet, sub_facet = "fundamental", "report"
    description = "利润表：营收 / 净利润 / EPS（tushare income，合并报表），面板净利润率数据来源"
    Params, Item = FinIncomeParams, FinReportBO
    unit = "symbol"
    sample_params = {"symbol": "600519"}


class Top10HoldersPort(DataPort[Top10HoldersParams, FinTop10HoldersBO]):
    name, label = "top10_holders", "前十大股东"
    facet, sub_facet = "fundamental", "holder"
    description = "股权结构（tushare top10_holders）"
    Params, Item = Top10HoldersParams, FinTop10HoldersBO
    unit = "symbol"
    sample_params = {"symbol": "600519"}


class Top10FloatHoldersPort(DataPort[Top10HoldersParams, FinTop10FloatHoldersBO]):
    name, label = "top10_float_holders", "前十大流通股东"
    facet, sub_facet = "fundamental", "holder"
    description = "流通盘筹码（tushare top10_floatholders）"
    Params, Item = Top10HoldersParams, FinTop10FloatHoldersBO
    unit = "symbol"
    sample_params = {"symbol": "600519"}


__all__ = [
    "DailyBasicPort",
    "FinDailyBasicBO",
    "FinIncomeParams",
    "FinIncomePort",
    "FinReportBO",
    "FinTop10FloatHoldersBO",
    "FinTop10HoldersBO",
    "Top10FloatHoldersPort",
    "Top10HoldersParams",
    "Top10HoldersPort",
]
