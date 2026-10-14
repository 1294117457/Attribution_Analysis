"""基本面 Port：日频估值 / 利润表 / 前十大股东"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from contexts.data.application.port.base import DataPort
from contexts.data.application.port.types import Symbol, TradeDate, TradeDateParams

from contexts.market.domain.fin_daily_basic.bo import FinDailyBasicBO
from contexts.market.domain.fin_report.bo import FinReportBO
from contexts.market.domain.fin_top10_holders.bo import FinTop10HoldersBO
from contexts.market.domain.fin_top10_float.bo import FinTop10FloatHoldersBO

# ═══════════════════════════════════════════════════════════════════════════════
# BO
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
