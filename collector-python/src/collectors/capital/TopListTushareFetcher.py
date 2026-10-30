"""TopListTushareFetcher - Tushare top_list (step7 refactor)"""
from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

from collectors.schemas import CapTopListBO
from collectors.base import BaseFetcher
from core.tushare_utils import (
    num, parse_list_date, rows, symbol_of, text, ymd,
)
from core.tushare_client import get_tushare_client
from core.validators import TradeDate

logger = logging.getLogger(__name__)


class TopListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: TradeDate


class TopListTushareFetcher(BaseFetcher):
    fetcher_type = "top_list_tushare"
    source = "tushare"
    label = "Top List (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = TopListParams.model_validate(params)
        df = await self._c.query("top_list", trade_date=ymd(p.trade_date))
        out: list[CapTopListBO] = []
        for r in rows(df):
            sym, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not sym or not td:
                continue
            out.append(CapTopListBO(
                trade_date=td, symbol=sym,
                name=text(r, "name"),
                reason=text(r, "reason"),
                close=num(r, "close"), pct_change=num(r, "pct_change"),
                turnover_rate=num(r, "turnover_rate"),
                amount=num(r, "amount"),
                l_sell=num(r, "l_sell"), l_buy=num(r, "l_buy"),
                l_amount=num(r, "l_amount"),
                net_amount=num(r, "net_amount"),
                net_rate=num(r, "net_rate"),
                amount_rate=num(r, "amount_rate"),
                float_values=num(r, "float_values"),
            ))
        return out


__all__ = ["TopListParams", "TopListTushareFetcher"]
