"""TopListService：龙虎榜每日明细 service（按 trade_date）"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.db import raw_session_factory
from collectors.base import CollectResult, RateLimited, replace_rows_for_date
from collectors.capital.TopListTushareFetcher import (
    TopListTushareFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)


class TopListService:
    name = "top_list"
    facet = "capital"
    label = "龙虎榜每日明细"
    strategy = "incremental"
    RANGE = {"start_key": "start_date", "end_key": "end_date", "granularity": "trade_day"}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: TopListTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or TopListTushareFetcher()

    async def collect(self, params: dict) -> CollectResult:
        td = params.get("trade_date")
        if not td:
            td = date.today()  # 全量模式：默认今天
        if not isinstance(td, date):
            td = date.fromisoformat(str(td))
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                bos = await self._fetcher.fetch(trade_date=td)
                saved = await self._save(td, bos)
                return CollectResult(
                    total=1, success=1, saved=saved,
                    message=f"龙虎榜 {td}: {len(bos)} 条, 写入 {saved}",
                )
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    raise
        return CollectResult(fail=1, message="重试耗尽")

    async def _save(self, td: date, bos: list) -> int:
        if not bos:
            return 0
        try:
            from models.cap_top_list import (
                CapTopListDB,
            )
        except ImportError:
            logger.debug("cap_top_list 表未建，跳过入库")
            return 0
        rows = [
            {
                "trade_date": bo.trade_date, "symbol": bo.symbol,
                "name": bo.name, "close": bo.close, "pct_change": bo.pct_change,
                "turnover_rate": bo.turnover_rate, "amount": bo.amount,
                "l_buy": bo.l_buy, "l_sell": bo.l_sell, "l_amount": bo.l_amount,
                "net_amount": bo.net_amount, "net_rate": bo.net_rate,
                "amount_rate": bo.amount_rate, "float_values": bo.float_values,
                "reason": bo.reason,
            }
            for bo in bos
        ]
        # ★ 自动分块（防 PG 参数上限）+ 按冲突键去重（防 ON CONFLICT 二次命中）
        return await replace_rows_for_date(
            CapTopListDB, rows, "trade_date", td,
            conflict_cols=['trade_date', 'symbol', 'reason'],
        )


__all__ = ["TopListService"]
