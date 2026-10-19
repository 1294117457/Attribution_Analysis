"""DividendTushareFetcher - Tushare dividend (step7 refactor)"""
from __future__ import annotations

import logging

from pydantic import BaseModel

from contexts.collect.application.bo import BaseDividendBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    num, parse_list_date, rows, symbol_of, text,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)


class DividendTushareFetcher(BaseFetcher):
    fetcher_type = "dividend_tushare"
    source = "tushare"
    label = "Dividend (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        df = await self._c.query("dividend")
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
                # §2.8 补 Tushare dividend 文档 div_listdate / imp_ann_date
                div_listdate=parse_list_date(r.get("div_listdate")),
                imp_ann_date=parse_list_date(r.get("imp_ann_date")),
            ))
        return out


__all__ = ["DividendTushareFetcher"]
