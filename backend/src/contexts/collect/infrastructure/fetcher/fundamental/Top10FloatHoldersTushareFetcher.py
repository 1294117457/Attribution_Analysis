"""Top10FloatHoldersTushareFetcher - Tushare top10_floatholders (step7 refactor)"""
from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

from contexts.collect.application.bo import FinTop10FloatHoldersBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    num, parse_list_date, rows, symbol_of, symbol_to_ts_code, text,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client
from shared.interface.validators import Symbol

logger = logging.getLogger(__name__)


class Top10FloatHoldersParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: Symbol


class Top10FloatHoldersTushareFetcher(BaseFetcher):
    fetcher_type = "top10_floatholders_tushare"
    source = "tushare"
    label = "Top 10 Float Holders (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = Top10FloatHoldersParams.model_validate(params)
        df = await self._c.query("top10_floatholders", ts_code=symbol_to_ts_code(p.symbol))
        out: list[FinTop10FloatHoldersBO] = []
        for r in rows(df):
            sym, holder = symbol_of(r), text(r, "holder_name")
            if not sym or not holder:
                continue
            out.append(FinTop10FloatHoldersBO(
                symbol=sym, holder_name=holder,
                ann_date=parse_list_date(r.get("ann_date")),
                end_date=parse_list_date(r.get("end_date")),
                hold_amount=num(r, "hold_amount"),
                hold_ratio=num(r, "hold_ratio"),
                hold_change=num(r, "hold_change"),
                holder_type=text(r, "holder_type"),
            ))
        return out


__all__ = ["Top10FloatHoldersParams", "Top10FloatHoldersTushareFetcher"]
