"""MoneyflowHsgtTushareFetcher：沪深港通资金流向（Tushare moneyflow_hsgt）"""
from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel, ConfigDict

from collectors.schemas import CapMoneyflowHsgtBO
from collectors.base import BaseFetcher
from core.tushare_utils import num, parse_list_date, rows, ymd
from core.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)


class MoneyflowHsgtParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: date


class MoneyflowHsgtTushareFetcher(BaseFetcher):
    """沪深港通资金流向（北向 / 南向）

    ★ 上游真实列（2025-10-29 实测）：
      trade_date, ggt_ss, ggt_sz, hgt, sgt, north_money, south_money
      —— **一行 = 一个交易日的资金流汇总**，上游**没有** symbol / rank / buy / sell
    ❌ 原实现读 exchange / buy_amount / sell_amount → 上游**不存在**；
       service 又取 hgt/sgt/north_money/south_money（且对 dict 用 getattr）
       → 字段、类型、来源三处互相打架，整批写入失败。已统一为官方列。
    ⚠️ 单位：上游数值为**百万元**。
    """

    fetcher_type = "moneyflow_hsgt_tushare"
    source = "tushare"
    label = "沪深港通资金流向（Tushare）"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = MoneyflowHsgtParams.model_validate(params)
        df = await self._c.query("moneyflow_hsgt", trade_date=ymd(p.trade_date))
        out: list[CapMoneyflowHsgtBO] = []
        for r in rows(df):
            td = parse_list_date(r.get("trade_date"))
            if not td:
                continue
            out.append(CapMoneyflowHsgtBO(
                trade_date=td,
                ggt_ss=num(r, "ggt_ss"),
                ggt_sz=num(r, "ggt_sz"),
                hgt=num(r, "hgt"),
                sgt=num(r, "sgt"),
                north_money=num(r, "north_money"),
                south_money=num(r, "south_money"),
            ))
        return out


__all__ = ["MoneyflowHsgtParams", "MoneyflowHsgtTushareFetcher"]
