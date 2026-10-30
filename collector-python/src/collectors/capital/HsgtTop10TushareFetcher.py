"""HsgtTop10TushareFetcher：沪深股通每日十大成交股（Tushare hsgt_top10）"""
from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel, ConfigDict

from collectors.schemas import CapHsgtTop10BO
from collectors.base import BaseFetcher
from core.tushare_utils import int_, num, parse_list_date, rows, symbol_of, text, ymd
from core.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)


class HsgtTop10Params(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: date


class HsgtTop10TushareFetcher(BaseFetcher):
    """沪深股通每日十大成交股

    ★ 上游真实列（2025-10-29 实测）：
      trade_date, ts_code, name, close, change, rank, market_type,
      amount, net_amount, buy, sell
    ❌ 原实现读 holding_days / share_ratio / hold_amount → 上游**不存在**，
       三个字段永远 None → 表写出来是空的。已改为官方列。
    """

    fetcher_type = "hsgt_top10_tushare"
    source = "tushare"
    label = "沪深股通十大成交股（Tushare）"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = HsgtTop10Params.model_validate(params)
        df = await self._c.query("hsgt_top10", trade_date=ymd(p.trade_date))
        out: list[CapHsgtTop10BO] = []
        for r in rows(df):
            sym = symbol_of(r)
            td = parse_list_date(r.get("trade_date"))
            if not sym or not td:
                continue
            market_type = text(r, "market_type")
            rank = int_(r, "rank")
            if market_type is None or rank is None:
                # rank / market_type 是远端表的 NOT NULL 列，缺了就跳过
                continue
            out.append(CapHsgtTop10BO(
                trade_date=td,
                symbol=sym,
                name=text(r, "name"),
                market_type=market_type,
                rank=rank,
                close=num(r, "close"),
                change=num(r, "change"),
                amount=num(r, "amount"),
                net_amount=num(r, "net_amount"),
                buy=num(r, "buy"),
                sell=num(r, "sell"),
            ))
        return out


__all__ = ["HsgtTop10Params", "HsgtTop10TushareFetcher"]
