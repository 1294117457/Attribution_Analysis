"""BlockTradeTushareFetcher - Tushare block_trade (step7 refactor)"""
from __future__ import annotations

import logging

from pydantic import BaseModel

from collectors.schemas import CapBlockTradeBO
from collectors.base import BaseFetcher
from core.tushare_utils import (
    num, parse_list_date, rows, symbol_of, text, ymd,
)
from core.tushare_client import get_tushare_client
from core.validators import TradeDate

logger = logging.getLogger(__name__)


class BlockTradeTushareFetcher(BaseFetcher):
    fetcher_type = "block_trade_tushare"
    source = "tushare"
    label = "Block Trade (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        from pydantic import BaseModel as _BM, ConfigDict

        class TradeDateParams(_BM):
            model_config = ConfigDict(extra="forbid")
            trade_date: TradeDate

        p = TradeDateParams.model_validate(params)
        df = await self._c.query("block_trade", trade_date=ymd(p.trade_date))
        out: list[CapBlockTradeBO] = []
        for r in rows(df):
            sym, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not sym or not td:
                continue
            out.append(CapBlockTradeBO(
                trade_date=td, symbol=sym,
                name=text(r, "name"),
                price=num(r, "price"), vol=num(r, "vol"), amount=num(r, "amount"),
                buyer=text(r, "buyer"), seller=text(r, "seller"),
            ))
        return out


__all__ = ["BlockTradeTushareFetcher"]
