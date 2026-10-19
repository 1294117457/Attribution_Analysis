"""SuspendTushareFetcher (Tushare suspend_d) - step7 refactor"""
from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel

from contexts.collect.application.bo import BaseSuspendBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    parse_list_date, rows, symbol_of, text, ymd,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)


class SuspendTushareFetcher(BaseFetcher):
    fetcher_type = "suspend_tushare"
    source = "tushare"
    label = "Suspend (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        td = params.get("trade_date")
        if not td:
            raise ValueError("trade_date is required")
        if not isinstance(td, date):
            td = date.fromisoformat(str(td))
        df = await self._c.query("suspend_d", trade_date=ymd(td))
        out: list[BaseSuspendBO] = []
        for r in rows(df):
            sym, t = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not sym or not t:
                continue
            out.append(BaseSuspendBO(
                symbol=sym, trade_date=t,
                # §2.1 修复：suspend_timing 是字符串（如 "09:30-10:00"），不再用 parse_list_date
                suspend_timing=text(r, "suspend_timing"),
                suspend_type=text(r, "suspend_type"),
            ))
        return out


__all__ = ["SuspendTushareFetcher"]
