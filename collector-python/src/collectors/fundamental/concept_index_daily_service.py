"""ConceptIndexDailyService：概念指数日 K service（按 index_code 维度批量）"""
from __future__ import annotations

import asyncio
import logging

from collectors.base import (
    CollectResult, RateLimited, list_all_concept_codes, upsert_rows,
)
from collectors.fundamental.ConceptIndexDailyAdataFetcher import (
    ConceptIndexDailyAdataFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)


class ConceptIndexDailyService:
    name = "concept_index_daily"
    facet = "fundamental"
    label = "概念指数日 K"
    strategy = "full"
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: ConceptIndexDailyAdataFetcher | None = None) -> None:
        self._fetcher = fetcher or ConceptIndexDailyAdataFetcher()

    async def collect(self, params: dict) -> CollectResult:
        index_codes = params.get("index_codes") or []
        if not index_codes:
            index_codes = await list_all_concept_codes()
            if not index_codes:
                return CollectResult(
                    fail=1,
                    message="index_codes 为空，且 concept 暂无数据（请先采集 concept_list）",
                )
        sem = asyncio.Semaphore(self.CONCURRENCY)

        async def one(c: str) -> tuple[int, list]:
            async with sem:
                await check(self.RATE_LIMIT)
                for attempt in range(3):
                    try:
                        items = await self._fetcher.fetch(index_code=c)
                        return len(items), items
                    except RateLimited as e:
                        if attempt < 2:
                            import asyncio as _a
                            await _a.sleep(e.retry_after)
                        else:
                            raise
                return 0, []

        results = await asyncio.gather(*[one(c) for c in index_codes], return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, tuple))
        fail = sum(1 for r in results if isinstance(r, BaseException))
        all_items = [it for r in results if isinstance(r, tuple) for it in r[1]]
        saved = await self._save(all_items)
        return CollectResult(
            total=len(index_codes), success=success, fail=fail, saved=saved,
            message=f"概念指数日 K: 共 {len(index_codes)} 个概念, 成功 {success}, 写入 {saved}",
        )

    async def _save(self, items: list) -> int:
        """落库：按 (index_code, trade_date) 幂等 upsert。"""
        if not items:
            return 0
        try:
            from models.concept_compat import (
                ConceptIndexTHDB,
            )
        except ImportError:
            logger.debug("fundamental_concept_index 表未建，跳过入库")
            return 0
        from datetime import date

        rows = [
            {
                "index_code": it["index_code"],
                "concept_name": it.get("concept_name") or "",
                "trade_date": date.fromisoformat(it["trade_date"])
                if isinstance(it["trade_date"], str) else it["trade_date"],
                "open": it.get("open") or 0.0,
                "high": it.get("high") or 0.0,
                "low": it.get("low") or 0.0,
                "close": it.get("close") or 0.0,
                "volume": it.get("volume") or 0,
                "amount": it.get("amount") or 0.0,
                "change": it.get("change"),
                "change_pct": it.get("change_pct"),
            }
            for it in items
        ]
        return await upsert_rows(
            ConceptIndexTHDB, rows, ["index_code", "trade_date"],
            immutable_cols=["index_code", "trade_date"],
        )


__all__ = ["ConceptIndexDailyService"]
