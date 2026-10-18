"""HolderNumberTushareFetcher - Tushare stk_holdernumber (step7 refactor)"""
from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

from contexts.collect.application.bo import CapHolderNumBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    num, parse_list_date, rows, symbol_of, symbol_to_ts_code,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client
from shared.interface.validators import Symbol

logger = logging.getLogger(__name__)


class HolderNumberParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: Symbol


class HolderNumberTushareFetcher(BaseFetcher):
    fetcher_type = "holder_number_tushare"
    source = "tushare"
    label = "Holder Number (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = HolderNumberParams.model_validate(params)
        df = await self._c.query("stk_holdernumber", ts_code=symbol_to_ts_code(p.symbol))
        out: list[CapHolderNumBO] = []
        for r in rows(df):
            sym, ed = symbol_of(r), parse_list_date(r.get("end_date"))
            if not sym or not ed:
                continue
            out.append(CapHolderNumBO(
                symbol=sym,
                ann_date=parse_list_date(r.get("ann_date")),
                end_date=ed,
                holder_num=int(num(r, "holder_num") or 0) if num(r, "holder_num") else None,
            ))
        return out


__all__ = ["HolderNumberParams", "HolderNumberTushareFetcher"]
