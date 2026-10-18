"""MoneyflowTushareFetcher - Tushare moneyflow (step7 refactor)"""
from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

from contexts.collect.application.bo import CapMoneyflowBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    num, parse_list_date, rows, symbol_of, ymd,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client
from shared.interface.validators import TradeDate

logger = logging.getLogger(__name__)


class MoneyflowParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: TradeDate


class MoneyflowTushareFetcher(BaseFetcher):
    fetcher_type = "moneyflow_tushare"
    source = "tushare"
    label = "Moneyflow (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = MoneyflowParams.model_validate(params)
        df = await self._c.query("moneyflow", trade_date=ymd(p.trade_date))
        out: list[CapMoneyflowBO] = []
        for r in rows(df):
            sym, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not sym or not td:
                continue
            out.append(CapMoneyflowBO(
                symbol=sym, trade_date=td,
                buy_sm_vol=num(r, "buy_sm_vol"), buy_sm_amount=num(r, "buy_sm_amount"),
                sell_sm_vol=num(r, "sell_sm_vol"), sell_sm_amount=num(r, "sell_sm_amount"),
                buy_md_vol=num(r, "buy_md_vol"), buy_md_amount=num(r, "buy_md_amount"),
                sell_md_vol=num(r, "sell_md_vol"), sell_md_amount=num(r, "sell_md_amount"),
                buy_lg_vol=num(r, "buy_lg_vol"), buy_lg_amount=num(r, "buy_lg_amount"),
                sell_lg_vol=num(r, "sell_lg_vol"), sell_lg_amount=num(r, "sell_lg_amount"),
                buy_elg_vol=num(r, "buy_elg_vol"), buy_elg_amount=num(r, "buy_elg_amount"),
                sell_elg_vol=num(r, "sell_elg_vol"), sell_elg_amount=num(r, "sell_elg_amount"),
                net_mf_vol=num(r, "net_mf_vol"), net_mf_amount=num(r, "net_mf_amount"),
            ))
        return out


__all__ = ["MoneyflowParams", "MoneyflowTushareFetcher"]
