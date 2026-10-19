"""MarginDetailTushareFetcher - Tushare margin_detail (step7 refactor)"""
from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

from contexts.collect.application.bo import CapMarginDetailBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    num, parse_list_date, rows, symbol_of, text, ymd,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client
from shared.interface.validators import TradeDate

logger = logging.getLogger(__name__)


class MarginDetailParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: TradeDate


class MarginDetailTushareFetcher(BaseFetcher):
    fetcher_type = "margin_detail_tushare"
    source = "tushare"
    label = "Margin Detail (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = MarginDetailParams.model_validate(params)
        df = await self._c.query("margin_detail", trade_date=ymd(p.trade_date))
        out: list[CapMarginDetailBO] = []
        for r in rows(df):
            sym, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not sym or not td:
                continue
            out.append(CapMarginDetailBO(
                symbol=sym, trade_date=td,
                # §2.3 补 Tushare margin_detail 文档 name 字段
                name=text(r, "name"),
                rzye=num(r, "rzye"), rqye=num(r, "rqye"),
                rzmre=num(r, "rzmre"), rqyl=num(r, "rqyl"),
                rzche=num(r, "rzche"), rqchl=num(r, "rqchl"),
                rqmcl=num(r, "rqmcl"), rzrqye=num(r, "rzrqye"),
            ))
        return out


__all__ = ["MarginDetailParams", "MarginDetailTushareFetcher"]
