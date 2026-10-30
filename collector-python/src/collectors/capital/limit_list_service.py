"""LimitListService：每日涨跌停板 service（按 trade_date 一次性）"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.db import raw_session_factory
from collectors.base import (
    CollectResult, RateLimited, fetch_with_retry, replace_rows_for_date,
)
from collectors.capital.LimitListTushareFetcher import (
    LimitListTushareFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)


class LimitListService:
    name = "limit_list_d"
    facet = "capital"
    label = "每日涨跌停板"
    strategy = "incremental"
    RANGE = {"start_key": "start_date", "end_key": "end_date", "granularity": "trade_day"}
    RATE_LIMIT = ("tushare", 100, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: LimitListTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or LimitListTushareFetcher()

    async def collect(self, params: dict) -> CollectResult:
        td = params.get("trade_date")
        if not td:
            td = date.today()  # 全量模式：默认今天
        if not isinstance(td, date):
            td = date.fromisoformat(str(td))
        # ★ fetch_with_retry：限流退避重试；**权限不足记 skip 而非 fail**
        #   （limit_list_d 需要 Tushare 更高积分档位，账号无权限时不该报「采集失败」）
        ok, items, msg = await fetch_with_retry(
            lambda: self._fetcher.fetch(trade_date=td),
            rate_limit=self.RATE_LIMIT,
        )
        if not ok:
            return CollectResult(total=1, skip=1, message=msg)
        saved = await self._save(td, items)
        return CollectResult(
            total=1, success=1, saved=saved, skip=1 if not items else 0,
            message=f"涨跌停 {td}: {len(items)} 条, 写入 {saved}",
        )

    async def _save(self, td: date, bos: list) -> int:
        if not bos:
            return 0
        try:
            from models.market_limit_list import (
                MarketLimitListDB,
            )
        except ImportError:
            logger.debug("capital_limit_list_d 表未建，跳过入库")
            return 0
        rows = [
            {
                "trade_date": bo.trade_date, "symbol": bo.symbol,
                "name": bo.name, "industry": bo.industry,
                "close": bo.close, "pct_chg": bo.pct_chg, "amount": bo.amount,
                "turnover_ratio": bo.turnover_ratio,
                "float_mv": bo.float_mv, "total_mv": bo.total_mv,
                "limit_type": bo.limit_type, "limit_times": bo.limit_times,
                "open_times": bo.open_times, "up_stat": bo.up_stat,
                "limit_amount": bo.limit_amount, "fd_amount": bo.fd_amount,
                "first_time": bo.first_time, "last_time": bo.last_time,
                "data_source": "tushare",
            }
            for bo in bos
        ]
        # ★ 自动分块（防 PG 参数上限）+ 按冲突键去重（防 ON CONFLICT 二次命中）
        return await replace_rows_for_date(
            MarketLimitListDB, rows, "trade_date", td,
            conflict_cols=['trade_date', 'symbol', 'limit_type'],
        )


__all__ = ["LimitListService"]
