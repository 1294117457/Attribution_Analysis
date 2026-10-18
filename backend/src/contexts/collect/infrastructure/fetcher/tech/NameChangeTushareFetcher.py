"""NameChangeTushareFetcher - Tushare namechange (step7 refactor)"""
from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel

from contexts.collect.application.bo import BaseNameChangeBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    num, parse_list_date, rows, symbol_of, text,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)


class NameChangeTushareFetcher(BaseFetcher):
    fetcher_type = "name_change_tushare"
    source = "tushare"
    label = "Name Change (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        df = await self._c.query("namechange")
        out: list[BaseNameChangeBO] = []
        for r in rows(df):
            sym, start = symbol_of(r), parse_list_date(r.get("start_date"))
            if not sym or not start:
                continue
            out.append(BaseNameChangeBO(
                symbol=sym, name=text(r, "name") or "",
                start_date=start,
                end_date=parse_list_date(r.get("end_date")),
                ann_date=parse_list_date(r.get("ann_date")),
                change_reason=text(r, "change_reason"),
            ))
        return out


__all__ = ["NameChangeTushareFetcher"]
