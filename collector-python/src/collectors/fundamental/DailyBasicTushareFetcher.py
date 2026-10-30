"""DailyBasicTushareFetcher - Tushare daily_basic (step7 refactor)"""
from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

from collectors.schemas import FinDailyBasicBO
from collectors.base import BaseFetcher
from core.tushare_utils import (
    num, parse_list_date, rows, symbol_of, ymd,
)
from core.tushare_client import get_tushare_client
from core.validators import TradeDate

logger = logging.getLogger(__name__)


class DailyBasicParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: TradeDate


class DailyBasicTushareFetcher(BaseFetcher):
    fetcher_type = "daily_basic_tushare"
    source = "tushare"
    label = "Daily Basic (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = DailyBasicParams.model_validate(params)
        df = await self._c.query("daily_basic", trade_date=ymd(p.trade_date))
        out: list[FinDailyBasicBO] = []
        for r in rows(df):
            sym, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            if not sym or not td:
                continue
            out.append(FinDailyBasicBO(
                symbol=sym, trade_date=td,
                close=num(r, "close"),
                turnover_rate=num(r, "turnover_rate"),
                turnover_rate_f=num(r, "turnover_rate_f"),
                volume_ratio=num(r, "volume_ratio"),
                pe=num(r, "pe"), pe_ttm=num(r, "pe_ttm"),
                pb=num(r, "pb"),
                ps=num(r, "ps"), ps_ttm=num(r, "ps_ttm"),
                dv_ratio=num(r, "dv_ratio"), dv_ttm=num(r, "dv_ttm"),
                total_share=num(r, "total_share"),
                float_share=num(r, "float_share"),
                free_share=num(r, "free_share"),
                total_mv=num(r, "total_mv"), circ_mv=num(r, "circ_mv"),
            ))
        return out


__all__ = ["DailyBasicParams", "DailyBasicTushareFetcher"]
