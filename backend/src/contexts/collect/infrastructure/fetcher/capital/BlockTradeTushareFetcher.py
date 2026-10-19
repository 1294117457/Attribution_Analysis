"""BlockTradeTushareFetcher - Tushare block_trade (step7 refactor)"""
from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

from contexts.collect.application.bo import CapBlockTradeBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    num, parse_list_date, rows, symbol_of, text, ymd,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client
from shared.interface.validators import TradeDate

logger = logging.getLogger(__name__)


# §2.2 修复：把局部 class TradeDateParams 提到模块顶层（与其他 fetcher 一致）
class BlockTradeParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: TradeDate


class BlockTradeTushareFetcher(BaseFetcher):
    fetcher_type = "block_trade_tushare"
    source = "tushare"
    label = "Block Trade (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = BlockTradeParams.model_validate(params)
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
__all__ = ["BlockTradeParams", "BlockTradeTushareFetcher"]
