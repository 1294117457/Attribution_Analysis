"""AdjFactorService：复权因子 service（按 symbol 维度的批量采集）"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.collect.application.service.base import CollectResult, RateLimited, list_all_a_symbols
from contexts.collect.infrastructure.fetcher.tech.AdjFactorTushareFetcher import (
    AdjFactorTushareFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class AdjFactorRepository:
    """adj_factor 写库（容错：表不存在则跳过）"""

    async def save_batch(self, rows: list[dict]) -> int:
        try:
            from contexts.collect.infrastructure.persistence.models.adj_factor import (
                AdjFactorDB,
            )
        except ImportError:
            logger.debug("adj_factor 表未建，跳过入库")
            return 0
        if not rows:
            return 0
        clean = [{k: v for k, v in r.items() if v is not None} for r in rows if "symbol" in r]
        async with db_session_factory() as session:
            stmt = pg_insert(AdjFactorDB).values(clean)
            update_cols = {c.name: stmt.excluded[c.name] for c in AdjFactorDB.__table__.columns
                           if c.name not in ("id", "symbol", "trade_date", "created_at")}
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "trade_date"],
                set_=update_cols,
            )
            r = await session.execute(stmt)
            await session.commit()
            return r.rowcount or 0


class AdjFactorService:
    name = "adj_factor"
    facet = "tech"
    sub_facet = "adj"
    label = "复权因子"
    description = "单只股票复权因子"
    DEFAULT_PARAMS = {"symbols": []}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 5

    def __init__(self, fetcher: AdjFactorTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or AdjFactorTushareFetcher()
        self._repo = AdjFactorRepository()

    async def collect(self, params: dict) -> CollectResult:
        symbols = params.get("symbols") or []
        if not symbols:
            symbols = await self._list_all_symbols()
            if not symbols:
                return CollectResult(
                    fail=1,
                    message="symbols 为空，且 stock_basic 暂无数据（请先采集 stock_basic）",
                )
        symbols = [str(s).zfill(6) for s in symbols]
        sem = asyncio.Semaphore(self.CONCURRENCY)

        async def one(symbol: str) -> int:
            async with sem:
                await check(self.RATE_LIMIT)
                for attempt in range(3):
                    try:
                        rows = await self._fetcher.fetch(symbol=symbol)
                        return await self._repo.save_batch(rows)
                    except RateLimited as e:
                        if attempt < 2:
                            import asyncio as _a
                            await _a.sleep(e.retry_after)
                        else:
                            raise
                return 0

        results = await asyncio.gather(*[one(s) for s in symbols], return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, int) and r >= 0)
        saved = sum(r for r in results if isinstance(r, int))
        fail = sum(1 for r in results if isinstance(r, BaseException))
        return CollectResult(
            total=len(symbols), success=success, fail=fail, saved=saved,
            message=f"复权因子: 共 {len(symbols)} 只, 成功 {success}, 写入 {saved}",
        )

    async def _list_all_symbols(self) -> list[str]:
        return await list_all_a_symbols()


__all__ = ["AdjFactorService"]
