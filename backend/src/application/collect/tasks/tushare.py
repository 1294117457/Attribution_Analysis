"""Tushare 系声明式采集任务（14 个）

元数据（facet / sub_facet / label / description）默认取 Port；
task_type、default_params、full_params、sort_order 与汇总文案保持原样。
"""
from __future__ import annotations

from datetime import date, timedelta

from application.collect.declarative import DeclarativeCollectTask
from application.collect.planners import SymbolPlanner, TradeDatePlanner
from application.collect.task import UnitTally
from application.port.data.capital import (
    BlockTradePort,
    HolderNumberPort,
    MarginDetailPort,
    MoneyflowPort,
    TopInstPort,
    TopListPort,
)
from application.port.data.fundamental import (
    DailyBasicPort,
    FinIncomePort,
    Top10FloatHoldersPort,
    Top10HoldersPort,
)
from application.port.data.reference import (
    AdjFactorPort,
    DividendPort,
    NameChangePort,
    SuspendPort,
)

_TRADE_DATE = TradeDatePlanner()
_SYMBOL = SymbolPlanner()


# ═══════════════════════════════════════════════════════════════════════════════
# 按交易日（7 个）
# ═══════════════════════════════════════════════════════════════════════════════


class _TradeDateTask(DeclarativeCollectTask):
    planner = _TRADE_DATE
    unit_word = "交易日"
    default_params = {"days": 1}
    full_params = {"days": 365}


class DailyBasicCollectTask(_TradeDateTask):
    """业务入口 POST /stocks/sync-daily-basic 经 run_one 复用 collect_one"""

    name = "daily_basic"
    port = DailyBasicPort
    sort_order = 0

    def summary_message(self, t: UnitTally) -> str:
        return f"完成: {t.success} 天（非交易日 {t.skip}），失败 {t.fail}；写入 {t.saved} 条"


class BaseSuspendCollectTask(_TradeDateTask):
    name = "base_suspend"
    port = SuspendPort
    empty_word = "无停复牌"
    sort_order = 20


class CapMoneyflowCollectTask(_TradeDateTask):
    name = "cap_moneyflow"
    port = MoneyflowPort
    sort_order = 10


class CapMarginDetailCollectTask(_TradeDateTask):
    name = "cap_margin_detail"
    port = MarginDetailPort
    sort_order = 20


class CapTopListCollectTask(_TradeDateTask):
    name = "cap_top_list"
    port = TopListPort
    empty_word = "无上榜"
    sort_order = 10


class CapTopInstCollectTask(_TradeDateTask):
    name = "cap_top_inst"
    port = TopInstPort
    empty_word = "无机构"
    sort_order = 20


class CapBlockTradeCollectTask(_TradeDateTask):
    name = "cap_block_trade"
    port = BlockTradePort
    empty_word = "无大宗"
    sort_order = 10


# ═══════════════════════════════════════════════════════════════════════════════
# 按股票（7 个）
# ═══════════════════════════════════════════════════════════════════════════════


class _SymbolTask(DeclarativeCollectTask):
    planner = _SYMBOL
    unit_word = "股票"
    default_params = {}


class BaseAdjFactorCollectTask(_SymbolTask):
    name = "base_adj_factor"
    port = AdjFactorPort
    sort_order = 10


class BaseDividendCollectTask(_SymbolTask):
    name = "base_dividend"
    port = DividendPort
    empty_word = "无分红"
    sort_order = 10


class CapHolderNumCollectTask(_SymbolTask):
    """季频数据，默认只采库中没有的股票"""

    name = "cap_holder_num"
    port = HolderNumberPort
    default_params = {"only_missing": True}
    sort_order = 20


class FinTop10HoldersCollectTask(_SymbolTask):
    name = "fin_top10_holders"
    port = Top10HoldersPort
    empty_word = "无股东"
    sort_order = 10

    def build_params(self, unit: str, params: dict) -> dict:
        return {"symbol": unit, "period": params.get("period")}


class FinTop10FloatHoldersCollectTask(_SymbolTask):
    name = "fin_top10_floatholders"
    port = Top10FloatHoldersPort
    empty_word = "无股东"
    sort_order = 20

    def build_params(self, unit: str, params: dict) -> dict:
        return {"symbol": unit, "period": params.get("period")}


class FinReportCollectTask(_SymbolTask):
    """利润表（合并报表）；years 按公告日回溯年数，symbol 只采单只，only_missing 断点续采，limit 调试"""

    name = "fin_report"
    port = FinIncomePort
    empty_word = "无财报"
    default_params = {"years": 1}
    full_params = {"years": 3}

    def build_params(self, unit: str, params: dict) -> dict:
        years = params.get("years", 1)
        start = date.today() - timedelta(days=int(float(years) * 365)) if years else None
        return {"symbol": unit, "start_date": start}

    def summary_message(self, t: UnitTally) -> str:
        return f"完成: 股票 {t.success}（无财报 {t.skip}），失败 {t.fail}；写入报告期 {t.saved} 条"


class BaseNameChangeCollectTask(_SymbolTask):
    """单元 = "all"（一次拉全市场）；传 symbol 时只拉单只；不做增量跳过"""

    name = "base_name_change"
    port = NameChangePort
    incremental = False
    sort_order = 30

    async def list_units(self, params: dict) -> list[str]:
        if params.get("symbol"):
            return [str(params["symbol"]).zfill(6)]
        return ["all"]

    def build_params(self, unit: str, params: dict) -> dict:
        return {"symbol": None if unit == "all" else unit}

    def summary_message(self, t: UnitTally) -> str:
        return f"完成: 抓取 {t.success} 批，失败 {t.fail}；写入 {t.saved} 条"


__all__ = [
    "BaseAdjFactorCollectTask",
    "BaseDividendCollectTask",
    "BaseNameChangeCollectTask",
    "BaseSuspendCollectTask",
    "CapBlockTradeCollectTask",
    "CapHolderNumCollectTask",
    "CapMarginDetailCollectTask",
    "CapMoneyflowCollectTask",
    "CapTopInstCollectTask",
    "CapTopListCollectTask",
    "DailyBasicCollectTask",
    "FinReportCollectTask",
    "FinTop10FloatHoldersCollectTask",
    "FinTop10HoldersCollectTask",
]
