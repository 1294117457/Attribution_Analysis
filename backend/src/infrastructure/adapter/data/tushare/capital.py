"""Tushare 资金面 Adapter"""
from __future__ import annotations

from typing import Optional

from application.port.data.capital import (
    BlockTradePort,
    CapBlockTradeBO,
    CapHolderNumBO,
    CapMarginDetailBO,
    CapMoneyflowBO,
    CapTopInstBO,
    CapTopListBO,
    HolderNumberParams,
    HolderNumberPort,
    MarginDetailPort,
    MoneyflowParams,
    MoneyflowPort,
    TopInstPort,
    TopListPort,
)
from application.port.data.types import TradeDateParams
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

_MONEYFLOW_FIELDS = (
    "buy_sm_vol", "buy_sm_amount", "sell_sm_vol", "sell_sm_amount",
    "buy_md_vol", "buy_md_amount", "sell_md_vol", "sell_md_amount",
    "buy_lg_vol", "buy_lg_amount", "sell_lg_vol", "sell_lg_amount",
    "buy_elg_vol", "buy_elg_amount", "sell_elg_vol", "sell_elg_amount",
    "net_mf_vol", "net_mf_amount",
)
_MARGIN_FIELDS = ("rzye", "rqye", "rzmre", "rqyl", "rzche", "rqchl", "rqmcl", "rzrqye")
_TOP_LIST_FIELDS = (
    "close", "pct_change", "turnover_rate", "amount", "l_sell", "l_buy", "l_amount",
    "net_amount", "net_rate", "amount_rate", "float_values",
)
_TOP_INST_FIELDS = ("buy", "buy_rate", "sell", "sell_rate", "net_buy")


class TushareMoneyflowAdapter(MoneyflowPort, TushareAdapterBase):
    async def fetch(self, p: MoneyflowParams) -> list[CapMoneyflowBO]:
        df = await self._c.query("moneyflow", trade_date=ymd(p.trade_date))
        wanted = set(p.symbols or ())
        out: list[CapMoneyflowBO] = []
        for r in rows(df):
            symbol, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not symbol or not td or (wanted and symbol not in wanted):
                continue
            out.append(CapMoneyflowBO(
                symbol=symbol, trade_date=td, **{f: num(r, f) for f in _MONEYFLOW_FIELDS},
            ))
        return out


class TushareMarginDetailAdapter(MarginDetailPort, TushareAdapterBase):
    async def fetch(self, p: TradeDateParams) -> list[CapMarginDetailBO]:
        df = await self._c.query("margin_detail", trade_date=ymd(p.trade_date))
        out: list[CapMarginDetailBO] = []
        for r in rows(df):
            symbol, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not symbol or not td:
                continue
            out.append(CapMarginDetailBO(
                symbol=symbol, trade_date=td, **{f: num(r, f) for f in _MARGIN_FIELDS},
            ))
        return out


class TushareTopListAdapter(TopListPort, TushareAdapterBase):
    async def fetch(self, p: TradeDateParams) -> list[CapTopListBO]:
        df = await self._c.query("top_list", trade_date=ymd(p.trade_date))
        out: list[CapTopListBO] = []
        for r in rows(df):
            symbol, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not symbol or not td:
                continue
            out.append(CapTopListBO(
                trade_date=td, symbol=symbol, name=text(r, "name"), reason=text(r, "reason"),
                **{f: num(r, f) for f in _TOP_LIST_FIELDS},
            ))
        return out


class TushareTopInstAdapter(TopInstPort, TushareAdapterBase):
    async def fetch(self, p: TradeDateParams) -> list[CapTopInstBO]:
        df = await self._c.query("top_inst", trade_date=ymd(p.trade_date))
        out: list[CapTopInstBO] = []
        for r in rows(df):
            symbol, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not symbol or not td:
                continue
            out.append(CapTopInstBO(
                trade_date=td, symbol=symbol,
                exalter=text(r, "exalter"), side=text(r, "side"), reason=text(r, "reason"),
                **{f: num(r, f) for f in _TOP_INST_FIELDS},
            ))
        return out


class TushareBlockTradeAdapter(BlockTradePort, TushareAdapterBase):
    async def fetch(self, p: TradeDateParams) -> list[CapBlockTradeBO]:
        df = await self._c.query("block_trade", trade_date=ymd(p.trade_date))
        out: list[CapBlockTradeBO] = []
        for r in rows(df):
            symbol, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not symbol or not td:
                continue
            out.append(CapBlockTradeBO(
                trade_date=td, symbol=symbol, name=text(r, "name"),
                price=num(r, "price"), vol=num(r, "vol"), amount=num(r, "amount"),
                buyer=text(r, "buyer"), seller=text(r, "seller"),
            ))
        return out


class TushareHolderNumberAdapter(HolderNumberPort, TushareAdapterBase):
    async def fetch(self, p: HolderNumberParams) -> list[CapHolderNumBO]:
        kwargs = {"ts_code": symbol_to_ts_code(p.symbol)}
        if p.ann_date:
            kwargs["ann_date"] = ymd(p.ann_date)
        df = await self._c.query("stk_holdernumber", **kwargs)
        out: list[CapHolderNumBO] = []
        for r in rows(df):
            symbol, end_date = symbol_of(r), parse_list_date(r.get("end_date"))
            if not symbol or not end_date:
                continue
            holder_num: Optional[float] = num(r, "holder_num")
            out.append(CapHolderNumBO(
                symbol=symbol,
                ann_date=parse_list_date(r.get("ann_date")),
                end_date=end_date,
                holder_num=int(holder_num) if holder_num is not None else None,
                holder_nums=num(r, "holder_nums"),
            ))
        return out


__all__ = [
    "TushareBlockTradeAdapter",
    "TushareHolderNumberAdapter",
    "TushareMarginDetailAdapter",
    "TushareMoneyflowAdapter",
    "TushareTopInstAdapter",
    "TushareTopListAdapter",
]
