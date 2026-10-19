"""HsgtTop10TushareFetcher：沪深股通十大成交股（Tushare hsgt_top10）—— 字段对齐 §1.4

接口：Tushare pro.hsgt_top10(trade_date=..., market_type=...)
输出字段（11 个）:
    trade_date / ts_code(sym[:6]) / name / market_type
    close / change(p_change)
    rank / amount / net_amount / buy / sell
"""
from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel, ConfigDict

from contexts.collect.application.bo import CapHsgtTop10BO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    num, parse_list_date, rows, symbol_of, text, ymd,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client
from shared.interface.validators import TradeDate

logger = logging.getLogger(__name__)


class HsgtTop10Params(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: TradeDate
    market_type: str | None = None   # 1=沪市 / 3=深市；不传则全市场


class HsgtTop10TushareFetcher(BaseFetcher):
    fetcher_type = "hsgt_top10_tushare"
    source = "tushare"
    label = "沪深股通十大成交股（Tushare）"
    description = "Tushare pro.hsgt_top10 接口（按股票+rank 粒度）"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = HsgtTop10Params.model_validate(params)
        kwargs: dict = {"trade_date": ymd(p.trade_date)}
        if p.market_type:
            kwargs["market_type"] = p.market_type
        df = await self._c.query("hsgt_top10", **kwargs)
        out: list[CapHsgtTop10BO] = []
        for r in rows(df):
            sym, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            mt = text(r, "market_type")
            rank = num(r, "rank")
            if not sym or not td or not mt or rank is None:
                continue
            try:
                out.append(CapHsgtTop10BO(
                    trade_date=td,
                    symbol=sym,
                    name=text(r, "name"),
                    market_type=mt,
                    rank=int(rank),
                    close=num(r, "close"),
                    p_change=num(r, "change"),               # 文档 change → p_change
                    amount=num(r, "amount"),
                    net_amount=num(r, "net_amount"),
                    buy=num(r, "buy"),
                    sell=num(r, "sell"),
                ))
            except Exception as e:
                logger.warning("跳过无效 hsgt_top10 行: %s", e)
        return out


__all__ = ["HsgtTop10Params", "HsgtTop10TushareFetcher"]
