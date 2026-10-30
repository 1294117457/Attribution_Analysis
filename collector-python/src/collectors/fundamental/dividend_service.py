"""DividendService：分红送股 service（按 symbol 维度批量）"""
from __future__ import annotations

import asyncio
import logging

from collectors.base import (
    CollectResult, RateLimited, list_all_a_symbols, upsert_rows,
)
from collectors.fundamental.DividendTushareFetcher import (
    DividendTushareFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)


class DividendService:
    name = "dividend"
    facet = "fundamental"
    label = "分红送股"
    strategy = "full"
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 5

    def __init__(self, fetcher: DividendTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or DividendTushareFetcher()

    async def collect(self, params: dict) -> CollectResult:
        symbols = params.get("symbols") or []
        if not symbols:
            symbols = await list_all_a_symbols()
            if not symbols:
                return CollectResult(
                    fail=1,
                    message="symbols 为空，且 stock_basic 暂无数据（请先采集 stock_basic）",
                )
        symbols = [str(s).zfill(6) for s in symbols]
        sem = asyncio.Semaphore(self.CONCURRENCY)

        async def one(s: str) -> tuple[int, list]:
            async with sem:
                await check(self.RATE_LIMIT)
                for attempt in range(3):
                    try:
                        bos = await self._fetcher.fetch(symbol=s)
                        return len(bos), bos
                    except RateLimited as e:
                        if attempt < 2:
                            import asyncio as _a
                            await _a.sleep(e.retry_after)
                        else:
                            raise
                return 0, []

        results = await asyncio.gather(*[one(s) for s in symbols], return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, tuple))
        fail = sum(1 for r in results if isinstance(r, BaseException))
        all_bos = [bo for r in results if isinstance(r, tuple) for bo in r[1]]
        saved = await self._save(all_bos)
        return CollectResult(
            total=len(symbols), success=success, fail=fail, saved=saved,
            message=f"分红送股: 共 {len(symbols)} 只, 成功 {success}, 失败 {fail}, 写入 {saved}",
        )

    async def _save(self, bos: list) -> int:
        """落库：按 (symbol, end_date, div_proc) 幂等 upsert。

        ⚠️ 分红是历史事件，保留全部，不做覆盖清理。
        """
        if not bos:
            return 0
        try:
            from models.base_dividend import (
                BaseDividendDB,
            )
        except ImportError:
            logger.debug("fundamental_dividend 表未建，跳过入库")
            return 0
        rows = [
            {
                "symbol": bo.symbol, "end_date": bo.end_date, "ann_date": bo.ann_date,
                "record_date": bo.record_date, "ex_date": bo.ex_date, "pay_date": bo.pay_date,
                "div_proc": bo.div_proc, "stk_div": bo.stk_div,
                "stk_bo_rate": bo.stk_bo_rate, "stk_co_rate": bo.stk_co_rate,
                "cash_div": bo.cash_div, "cash_div_tax": bo.cash_div_tax,
                "data_source": "tushare",
            }
            for bo in bos
        ]
        return await upsert_rows(
            BaseDividendDB, rows, ["symbol", "end_date", "div_proc"],
            immutable_cols=["symbol", "end_date", "div_proc"],
        )


__all__ = ["DividendService"]
