"""LimitListTushareFetcher：每日涨跌停板（Tushare limit_list_d）—— 字段对齐 §1.3

接口：Tushare pro.limit_list_d(trade_date=...)
输出字段（18 个）:
    trade_date / ts_code(sym[:6]) / industry / name
    close / pct_chg
    amount / limit_amount / float_mv / total_mv / turnover_ratio
    fd_amount / first_time / last_time
    open_times / up_stat / limit_times / limit(→limit_type)
"""
from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel, ConfigDict

from contexts.collect.application.bo import CapLimitListDBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    num, parse_list_date, rows, symbol_of, text, ymd,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client
from shared.interface.validators import TradeDate

logger = logging.getLogger(__name__)


class LimitListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: TradeDate


class LimitListTushareFetcher(BaseFetcher):
    fetcher_type = "limit_list_d_tushare"
    source = "tushare"
    label = "每日涨跌停板（Tushare）"
    description = "Tushare pro.limit_list_d 接口"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = LimitListParams.model_validate(params)
        df = await self._c.query("limit_list_d", trade_date=ymd(p.trade_date))
        out: list[CapLimitListDBO] = []
        for r in rows(df):
            sym, td = symbol_of(r), parse_list_date(r.get("trade_date"))
            limit = text(r, "limit")  # 文档字段 limit（D=跌停/U=涨停/Z=炸板）
            if not sym or not td or not limit:
                continue
            try:
                out.append(CapLimitListDBO(
                    trade_date=td,
                    symbol=sym,
                    industry=text(r, "industry"),
                    name=text(r, "name"),
                    close=num(r, "close"),
                    pct_chg=num(r, "pct_chg"),
                    amount=num(r, "amount"),
                    limit_amount=num(r, "limit_amount"),
                    float_mv=num(r, "float_mv"),
                    total_mv=num(r, "total_mv"),
                    turnover_ratio=num(r, "turnover_ratio"),
                    fd_amount=num(r, "fd_amount"),
                    first_time=text(r, "first_time"),
                    last_time=text(r, "last_time"),
                    open_times=int(num(r, "open_times") or 0) if num(r, "open_times") is not None else None,
                    up_stat=text(r, "up_stat"),
                    limit_times=int(num(r, "limit_times") or 0) if num(r, "limit_times") is not None else None,
                    limit_type=limit,
                ))
            except Exception as e:
                logger.warning("跳过无效 limit_list_d 行: %s", e)
        return out


__all__ = ["LimitListParams", "LimitListTushareFetcher"]
