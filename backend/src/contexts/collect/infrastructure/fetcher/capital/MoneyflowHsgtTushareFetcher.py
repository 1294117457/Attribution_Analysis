"""MoneyflowHsgtTushareFetcher：沪深港通资金流向（Tushare moneyflow_hsgt）—— 字段对齐 §1.2

接口：Tushare pro.moneyflow_hsgt(trade_date=..., market_type=...)
注意：文档为"按股票"粒度，不是"按交易所"聚合（原版语义错，已重写）

输出字段（12 个）:
    trade_date / ts_code(sym[:6]) / name / market_type
    close / change(p_change) / pct_chg / rank
    amount / net_amount / buy / sell
"""
from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel, ConfigDict

from contexts.collect.application.bo import CapMoneyflowHsgtBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    num, parse_list_date, rows, symbol_of, text, ymd,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client
from shared.interface.validators import TradeDate

logger = logging.getLogger(__name__)


class MoneyflowHsgtParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: TradeDate
    market_type: str | None = None   # 1=沪市 / 3=深市；不传则全市场


class MoneyflowHsgtTushareFetcher(BaseFetcher):
    fetcher_type = "moneyflow_hsgt_tushare"
    source = "tushare"
    label = "沪深港通资金流向（Tushare）"
    description = "Tushare pro.moneyflow_hsgt 接口（按股票粒度）"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = MoneyflowHsgtParams.model_validate(params)
        kwargs: dict = {"trade_date": ymd(p.trade_date)}
        if p.market_type:
            kwargs["market_type"] = p.market_type
        df = await self._c.query("moneyflow_hsgt", **kwargs)
        out: list[CapMoneyflowHsgtBO] = []
        for r in rows(df):
            sym, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            mt = text(r, "market_type")
            if not sym or not td or not mt:
                continue
            try:
                out.append(CapMoneyflowHsgtBO(
                    trade_date=td,
                    symbol=sym,
                    name=text(r, "name"),
                    market_type=mt,
                    close=num(r, "close"),
                    p_change=num(r, "change"),               # 文档 change → p_change
                    pct_change=num(r, "pct_chg"),
                    rank=int(num(r, "rank") or 0) if num(r, "rank") is not None else None,
                    amount=num(r, "amount"),
                    net_amount=num(r, "net_amount"),
                    buy=num(r, "buy"),
                    sell=num(r, "sell"),
                ))
            except Exception as e:
                logger.warning("跳过无效 moneyflow_hsgt 行: %s", e)
        return out


__all__ = ["MoneyflowHsgtParams", "MoneyflowHsgtTushareFetcher"]
