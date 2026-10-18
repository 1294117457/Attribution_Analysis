"""AdjFactorTushareFetcher - Tushare adj_factor (step7 refactor)"""
from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel

from contexts.collect.application.bo import BaseAdjFactorBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import num, parse_list_date, rows, symbol_of
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)


class AdjFactorTushareFetcher(BaseFetcher):
    fetcher_type = "adj_factor_tushare"
    source = "tushare"
    label = "AdjFactor (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        symbol = params.get("symbol")
        kwargs = {}
        if symbol:
            kwargs["ts_code"] = symbol if "." in symbol else f"{symbol}.{'SH' if symbol.startswith(('6', '5', '9')) else 'SZ'}"
        df = await self._c.query("adj_factor", **kwargs)
        out: list[BaseAdjFactorBO] = []
        for r in rows(df):
            sym, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not sym or not td:
                continue
            out.append(BaseAdjFactorBO(
                symbol=sym, trade_date=td,
                adj_factor=float(num(r, "adj_factor") or 0.0),
            ))
        return out


__all__ = ["AdjFactorTushareFetcher"]
