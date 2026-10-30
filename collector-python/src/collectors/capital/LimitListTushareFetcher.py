"""LimitListTushareFetcher：每日涨跌停板（Tushare limit_list_d）"""
from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel, ConfigDict

from collectors.schemas import CapLimitListBO
from collectors.base import BaseFetcher
from core.tushare_utils import int_, num, parse_list_date, rows, symbol_of, text, ymd
from core.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)


class LimitListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: date


class LimitListTushareFetcher(BaseFetcher):
    """每日涨跌停板

    ★ 上游官方列（对齐 collector-python/docs/data/tushare.md「涨跌停列表（新）」）：
      trade_date, ts_code, industry, name, close, pct_chg, amount, limit_amount,
      float_mv, total_mv, turnover_ratio, fd_amount, first_time, last_time,
      open_times, up_stat, limit_times, limit
    ❌ 原实现读 pct_change / close / first_limit_time / board_count /
       board_strength / reason —— 除 close 外**全部上游不存在**；
       且用 row["xxx"] 直接索引 → 缺列抛 KeyError 被 except 吞掉 → 整行静默丢失。
       已全部改为官方列 + 安全取值。
    ⚠️ 当前 TUSHARE_TOKEN **无该接口权限**（2025-10-29 实测：
       「您没有接口(limit_list_d)访问权限」），需账号开通积分权限。
    """

    fetcher_type = "limit_list_d_tushare"
    source = "tushare"
    label = "每日涨跌停板（Tushare）"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = LimitListParams.model_validate(params)
        df = await self._c.query("limit_list_d", trade_date=ymd(p.trade_date))
        out: list[CapLimitListBO] = []
        for r in rows(df):
            sym = symbol_of(r)
            td = parse_list_date(r.get("trade_date"))
            if not sym or not td:
                continue
            limit_type = text(r, "limit")
            if not limit_type:
                # limit 是远端表的 NOT NULL 列（U涨停 / D跌停 / Z炸板）
                logger.warning("跳过 limit_list_d 无涨跌停类型的行: %s", sym)
                continue
            out.append(CapLimitListBO(
                trade_date=td,
                symbol=sym,
                name=text(r, "name"),
                industry=text(r, "industry"),
                close=num(r, "close"),
                pct_chg=num(r, "pct_chg"),
                amount=num(r, "amount"),
                turnover_ratio=num(r, "turnover_ratio"),
                float_mv=num(r, "float_mv"),
                total_mv=num(r, "total_mv"),
                limit_type=limit_type,
                limit_times=int_(r, "limit_times"),
                open_times=int_(r, "open_times"),
                up_stat=text(r, "up_stat"),
                limit_amount=num(r, "limit_amount"),
                fd_amount=num(r, "fd_amount"),
                first_time=text(r, "first_time"),
                last_time=text(r, "last_time"),
            ))
        return out


__all__ = ["LimitListParams", "LimitListTushareFetcher"]
