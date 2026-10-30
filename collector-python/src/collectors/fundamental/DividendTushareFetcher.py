"""DividendTushareFetcher - Tushare dividend (step7 refactor)"""
from __future__ import annotations

import logging

from pydantic import BaseModel

from collectors.schemas import BaseDividendBO
from collectors.base import BaseFetcher
from core.tushare_utils import (
    num, parse_list_date, rows, symbol_of, text,
)
from core.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)


class DividendTushareFetcher(BaseFetcher):
    fetcher_type = "dividend_tushare"
    source = "tushare"
    label = "Dividend (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        # ★ ★ 必须传 ts_code —— Tushare 的 pro.dividend 要求
        #   ts_code / ann_date / record_date / ex_date / imp_ann_date 至少给一个，
        #   全空会直接报「参数校验失败」。
        #   原实现 `query("dividend")` 不传任何参数 → 必然失败。
        symbol = params.get("symbol")
        kwargs: dict = {}
        if symbol:
            sym = str(symbol).zfill(6)
            kwargs["ts_code"] = (
                sym if "." in sym
                else f"{sym}.{'SH' if sym.startswith(('6', '5', '9')) else 'SZ'}"
            )
        # 全局分红（不分股票）时用 ann_date 兜底：取近一年
        if not kwargs:
            from datetime import date, timedelta
            kwargs["ann_date"] = (
                date.today() - timedelta(days=365)
            ).strftime("%Y%m%d")
        df = await self._c.query("dividend", **kwargs)
        out: list[BaseDividendBO] = []
        for r in rows(df):
            sym, ed = symbol_of(r), parse_list_date(r.get("end_date"))
            if not sym or not ed:
                continue
            out.append(BaseDividendBO(
                symbol=sym, end_date=ed,
                ann_date=parse_list_date(r.get("ann_date")),
                record_date=parse_list_date(r.get("record_date")),
                ex_date=parse_list_date(r.get("ex_date")),
                pay_date=parse_list_date(r.get("pay_date")),
                div_proc=text(r, "div_proc"),
                stk_div=num(r, "stk_div"),
                stk_bo_rate=num(r, "stk_bo_rate"),
                stk_co_rate=num(r, "stk_co_rate"),
                cash_div=num(r, "cash_div"),
                cash_div_tax=num(r, "cash_div_tax"),
            ))
        return out


__all__ = ["DividendTushareFetcher"]
