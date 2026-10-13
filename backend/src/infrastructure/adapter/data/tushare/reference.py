"""Tushare 基础资料 Adapter"""
from __future__ import annotations

import logging

from application.port.data.base import SourceUnavailable
from application.port.data.reference import (
    AdjFactorPort,
    BaseAdjFactorBO,
    BaseDividendBO,
    BaseNameChangeBO,
    BaseSuspendBO,
    DividendPort,
    NameChangeParams,
    NameChangePort,
    StockBasicParams,
    StockBasicPort,
    StockInfoBO,
    SuspendPort,
)
from application.port.data.types import SymbolParams, TradeDateParams
from infrastructure.adapter.data.tushare.base import TushareAdapterBase
from infrastructure.adapter.data.tushare.parser import (
    num,
    parse_list_date,
    rows,
    symbol_of,
    symbol_to_ts_code,
    text,
    ymd,
)

logger = logging.getLogger(__name__)

_STOCK_BASIC_FIELDS = (
    "ts_code,symbol,name,area,industry,market,exchange,list_date,delist_date,"
    "list_status,is_hs,act_name,act_ent_type"
)
_EXCHANGES = ("SSE", "SZSE", "BSE")
_DIVIDEND_VALUE_FIELDS = ("stk_div", "stk_bo_rate", "stk_co_rate", "cash_div", "cash_div_tax")


class TushareStockBasicAdapter(StockBasicPort, TushareAdapterBase):
    """按交易所分批拉取；单个交易所失败跳过（与原实现一致），全部失败才报错"""

    async def fetch(self, p: StockBasicParams) -> list[StockInfoBO]:
        out: list[StockInfoBO] = []
        errors: list[str] = []
        for ex in _EXCHANGES:
            try:
                df = await self._c.query(
                    "stock_basic", exchange=ex, list_status=p.list_status.value, fields=_STOCK_BASIC_FIELDS,
                )
            except SourceUnavailable as e:
                logger.warning("拉取 %s stock_basic 失败: %r", ex, e)
                errors.append(f"{ex}: {e}")
                continue
            for r in rows(df):
                symbol = text(r, "symbol")
                if not symbol:
                    continue
                try:
                    out.append(StockInfoBO(
                        symbol=symbol.zfill(6),
                        ts_code=text(r, "ts_code"),
                        name=text(r, "name") or "",
                        area=text(r, "area"),
                        industry=text(r, "industry"),
                        market=text(r, "market"),
                        exchange=text(r, "exchange"),
                        list_date=parse_list_date(r.get("list_date")),
                        delist_date=parse_list_date(r.get("delist_date")),
                        list_status=text(r, "list_status") or "L",
                        is_hs=text(r, "is_hs") or "N",
                        act_name=text(r, "act_name"),
                        act_ent_type=text(r, "act_ent_type"),
                    ))
                except Exception as e:
                    logger.warning("跳过无效行: %s", e)
        if len(errors) == len(_EXCHANGES):
            raise SourceUnavailable("stock_basic 全部交易所失败: " + "; ".join(errors))
        return out


class TushareAdjFactorAdapter(AdjFactorPort, TushareAdapterBase):
    async def fetch(self, p: SymbolParams) -> list[BaseAdjFactorBO]:
        df = await self._c.query("adj_factor", ts_code=symbol_to_ts_code(p.symbol))
        out: list[BaseAdjFactorBO] = []
        for r in rows(df):
            symbol, td, af = symbol_of(r), parse_list_date(r.get("trade_date")), num(r, "adj_factor")
            if not symbol or not td or af is None:
                continue
            out.append(BaseAdjFactorBO(symbol=symbol, trade_date=td, adj_factor=af))
        return out


class TushareSuspendAdapter(SuspendPort, TushareAdapterBase):
    async def fetch(self, p: TradeDateParams) -> list[BaseSuspendBO]:
        df = await self._c.query("suspend_d", trade_date=ymd(p.trade_date))
        out: list[BaseSuspendBO] = []
        for r in rows(df):
            symbol, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not symbol or not td:
                continue
            out.append(BaseSuspendBO(
                symbol=symbol,
                trade_date=td,
                suspend_timing=parse_list_date(r.get("suspend_timing")),
                suspend_type=text(r, "suspend_type"),
            ))
        return out


class TushareNameChangeAdapter(NameChangePort, TushareAdapterBase):
    async def fetch(self, p: NameChangeParams) -> list[BaseNameChangeBO]:
        kwargs = {"ts_code": symbol_to_ts_code(p.symbol)} if p.symbol else {}
        df = await self._c.query("namechange", **kwargs)
        out: list[BaseNameChangeBO] = []
        for r in rows(df):
            symbol, start, name = symbol_of(r), parse_list_date(r.get("start_date")), text(r, "name")
            if not symbol or not start or not name:
                continue
            out.append(BaseNameChangeBO(
                symbol=symbol,
                name=name,
                start_date=start,
                end_date=parse_list_date(r.get("end_date")),
                ann_date=parse_list_date(r.get("ann_date")),
                change_reason=text(r, "change_reason"),
            ))
        return out


class TushareDividendAdapter(DividendPort, TushareAdapterBase):
    async def fetch(self, p: SymbolParams) -> list[BaseDividendBO]:
        df = await self._c.query("dividend", ts_code=symbol_to_ts_code(p.symbol))
        out: list[BaseDividendBO] = []
        for r in rows(df):
            symbol, end_date = symbol_of(r), parse_list_date(r.get("end_date"))
            if not symbol or not end_date:
                continue
            out.append(BaseDividendBO(
                symbol=symbol,
                end_date=end_date,
                ann_date=parse_list_date(r.get("ann_date")),
                record_date=parse_list_date(r.get("record_date")),
                ex_date=parse_list_date(r.get("ex_date")),
                pay_date=parse_list_date(r.get("pay_date")),
                div_proc=text(r, "div_proc"),
                **{f: num(r, f) for f in _DIVIDEND_VALUE_FIELDS},
            ))
        return out


__all__ = [
    "TushareAdjFactorAdapter",
    "TushareDividendAdapter",
    "TushareNameChangeAdapter",
    "TushareStockBasicAdapter",
    "TushareSuspendAdapter",
]
