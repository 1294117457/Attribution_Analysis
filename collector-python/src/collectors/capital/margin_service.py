"""MarginService：融资融券明细 service（按 trade_date 一次性）"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.db import raw_session_factory
from collectors.base import CollectResult, RateLimited, replace_rows_for_date
from collectors.capital.MarginDetailTushareFetcher import (
    MarginDetailTushareFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)


class MarginService:
    name = "margin"
    facet = "capital"
    label = "融资融券明细"
    strategy = "incremental"
    RANGE = {"start_key": "start_date", "end_key": "end_date", "granularity": "trade_day"}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: MarginDetailTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or MarginDetailTushareFetcher()

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
                    message=f"融资融券 {td}: {len(bos)} 条, 写入 {saved}",
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
            from models.cap_margin_detail import (
                CapMarginDetailDB,
            )
        except ImportError:
            logger.debug("cap_margin_detail 表未建，跳过入库")
            return 0
        rows = [
            {
                "symbol": bo.symbol, "trade_date": bo.trade_date,
                "rzye": bo.rzye, "rqye": bo.rqye, "rzmre": bo.rzmre, "rqyl": bo.rqyl,
                "rzche": bo.rzche, "rqchl": bo.rqchl, "rqmcl": bo.rqmcl, "rzrqye": bo.rzrqye,
            }
            for bo in bos
        ]
        # ★ 全市场单日 ≈ 5400 行 × 10 列 = 54,000 参数 → 超 PG 32767 上限 → 自动分块
        return await replace_rows_for_date(
            CapMarginDetailDB, rows, "trade_date", td,
            conflict_cols=["symbol", "trade_date"],
        )


__all__ = ["MarginService"]
