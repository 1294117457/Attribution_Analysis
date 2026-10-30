"""TopInstTushareFetcher - Tushare top_inst (step7 refactor)"""
from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

from collectors.schemas import CapTopInstBO
from collectors.base import BaseFetcher
from core.tushare_utils import (
    num, parse_list_date, rows, symbol_of, text, ymd,
)
from core.tushare_client import get_tushare_client
from core.validators import TradeDate

logger = logging.getLogger(__name__)


class TopInstParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: TradeDate


class TopInstTushareFetcher(BaseFetcher):
    fetcher_type = "top_inst_tushare"
    source = "tushare"
    label = "Top Institutional (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = TopInstParams.model_validate(params)
        df = await self._c.query("top_inst", trade_date=ymd(p.trade_date))
        out: list[CapTopInstBO] = []
        for r in rows(df):
            sym, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not sym or not td:
                continue
            out.append(CapTopInstBO(
                trade_date=td, symbol=sym,
                exalter=text(r, "exalter"),
                side=text(r, "side"),
                reason=text(r, "reason"),
                buy=num(r, "buy"), buy_rate=num(r, "buy_rate"),
                sell=num(r, "sell"), sell_rate=num(r, "sell_rate"),
                net_buy=num(r, "net_buy"),
            ))
        return out


__all__ = ["TopInstParams", "TopInstTushareFetcher"]
