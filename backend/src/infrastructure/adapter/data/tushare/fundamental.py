"""Tushare 基本面 Adapter"""
from __future__ import annotations

import logging

from application.port.data.fundamental import (
    DailyBasicPort,
    FinDailyBasicBO,
    FinIncomeParams,
    FinIncomePort,
    FinReportBO,
    FinTop10FloatHoldersBO,
    FinTop10HoldersBO,
    Top10FloatHoldersPort,
    Top10HoldersParams,
    Top10HoldersPort,
)
from application.port.data.types import TradeDateParams
from infrastructure.adapter.data.tushare.base import TushareAdapterBase
from infrastructure.adapter.data.tushare.parser import (
    INCOME_FIELDS,
    INCOME_VALUE_FIELDS,
    dedupe_income,
    num,
    parse_list_date,
    rows,
    symbol_of,
    symbol_to_ts_code,
    text,
    ymd,
)

logger = logging.getLogger(__name__)

_DAILY_BASIC_VALUE_FIELDS = (
    "close", "turnover_rate", "turnover_rate_f", "volume_ratio", "pe", "pe_ttm", "pb",
    "ps", "ps_ttm", "dv_ratio", "dv_ttm", "total_share", "float_share", "free_share",
    "total_mv", "circ_mv",
)
_DAILY_BASIC_FIELDS = ",".join(("ts_code", "trade_date", *_DAILY_BASIC_VALUE_FIELDS))


class TushareDailyBasicAdapter(DailyBasicPort, TushareAdapterBase):
    async def fetch(self, p: TradeDateParams) -> list[FinDailyBasicBO]:
        df = await self._c.query("daily_basic", trade_date=ymd(p.trade_date), fields=_DAILY_BASIC_FIELDS)
        out: list[FinDailyBasicBO] = []
        for r in rows(df):
            symbol, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not symbol or not td:
                continue
            try:
                out.append(FinDailyBasicBO(
                    symbol=symbol, trade_date=td, **{f: num(r, f) for f in _DAILY_BASIC_VALUE_FIELDS},
                ))
            except Exception as e:
                logger.warning("跳过无效 daily_basic 行: %s", e)
        return out


class TushareFinIncomeAdapter(FinIncomePort, TushareAdapterBase):
    """单只股票合并报表（report_type=1）利润表，按报告期去重"""

    async def fetch(self, p: FinIncomeParams) -> list[FinReportBO]:
        kwargs = {"ts_code": symbol_to_ts_code(p.symbol), "report_type": "1", "fields": INCOME_FIELDS}
        if p.start_date:
            kwargs["start_date"] = ymd(p.start_date)
        if p.end_date:
            kwargs["end_date"] = ymd(p.end_date)
        df = await self._c.query("income", **kwargs)
        if df.empty:
            return []
        out: list[FinReportBO] = []
        for r in rows(dedupe_income(df)):
            symbol, end_date = symbol_of(r), parse_list_date(r.get("end_date"))
            if not symbol or end_date is None:
                continue
            out.append(FinReportBO(
                symbol=symbol,
                end_date=end_date,
                ann_date=parse_list_date(r.get("ann_date")),
                report_type=text(r, "report_type"),
                comp_type=text(r, "comp_type"),
                **{f: num(r, f) for f in INCOME_VALUE_FIELDS},
            ))
        return out


def _holder_kwargs(p: Top10HoldersParams) -> dict:
    kwargs = {"ts_code": symbol_to_ts_code(p.symbol)}
    if p.period:
        kwargs["period"] = ymd(p.period)
    return kwargs


class TushareTop10HoldersAdapter(Top10HoldersPort, TushareAdapterBase):
    async def fetch(self, p: Top10HoldersParams) -> list[FinTop10HoldersBO]:
        df = await self._c.query("top10_holders", **_holder_kwargs(p))
        out: list[FinTop10HoldersBO] = []
        for r in rows(df):
            symbol, holder = symbol_of(r), text(r, "holder_name")
            if not symbol or not holder:
                continue
            out.append(FinTop10HoldersBO(
                symbol=symbol,
                ann_date=parse_list_date(r.get("ann_date")),
                end_date=parse_list_date(r.get("end_date")),
                holder_name=holder,
                hold_amount=num(r, "hold_amount"),
                hold_ratio=num(r, "hold_ratio"),
                hold_float_ratio=num(r, "hold_float_ratio"),
                hold_change=num(r, "hold_change"),
                holder_type=text(r, "holder_type"),
            ))
        return out


class TushareTop10FloatHoldersAdapter(Top10FloatHoldersPort, TushareAdapterBase):
    async def fetch(self, p: Top10HoldersParams) -> list[FinTop10FloatHoldersBO]:
        df = await self._c.query("top10_floatholders", **_holder_kwargs(p))
        out: list[FinTop10FloatHoldersBO] = []
        for r in rows(df):
            symbol, holder = symbol_of(r), text(r, "holder_name")
            if not symbol or not holder:
                continue
            out.append(FinTop10FloatHoldersBO(
                symbol=symbol,
                ann_date=parse_list_date(r.get("ann_date")),
                end_date=parse_list_date(r.get("end_date")),
                holder_name=holder,
                hold_amount=num(r, "hold_amount"),
                hold_ratio=num(r, "hold_ratio"),
                hold_change=num(r, "hold_change"),
                holder_type=text(r, "holder_type"),
            ))
        return out


__all__ = [
    "TushareDailyBasicAdapter",
    "TushareFinIncomeAdapter",
    "TushareTop10FloatHoldersAdapter",
    "TushareTop10HoldersAdapter",
]
