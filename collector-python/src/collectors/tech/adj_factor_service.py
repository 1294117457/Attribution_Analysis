"""AdjFactorService：复权因子 service（按 symbol 维度的批量采集）"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.db import raw_session_factory
from collectors.base import CollectResult, RateLimited, list_all_a_symbols
from collectors.tech.AdjFactorTushareFetcher import (
    AdjFactorTushareFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)

# adj_factor 表的可写列（写库时按此过滤 BO 字段）
_ADJ_WRITABLE_COLS = {"symbol", "trade_date", "adj_factor", "data_source"}


class AdjFactorRepository:
    """adj_factor 写库（容错：表不存在则跳过）"""

    async def save_batch(self, rows: list[dict]) -> int:
        try:
            from models.adj_factor import (
                AdjFactorDB,
            )
        except ImportError:
            logger.debug("adj_factor 表未建，跳过入库")
            return 0
        if not rows:
            return 0
        # ★ ⚠️ fetcher 返回的是 pydantic BO（BaseAdjFactorBO），不是 dict！
        #   原实现写的是 `{k: v for k, v in r.items() ...} if "symbol" in r`：
        #   pydantic 对象没有 .items()、且 `"symbol" in bo` 恒为 False
        #   → clean 变成空列表 → SQLAlchemy 退化成 INSERT ... DEFAULT VALUES
        #   → 往表里插了一条 symbol=NULL 的垃圾行 → NotNullViolation → 整个任务失败。
        #   → 统一先归一化成 dict。
        clean: list[dict] = []
        for r in rows:
            if isinstance(r, dict):
                d = dict(r)
            elif hasattr(r, "model_dump"):
                d = r.model_dump()
            else:
                continue
            sym = d.get("symbol")
            if not sym:
                continue
            d["symbol"] = str(sym).zfill(6)
            d["data_source"] = d.get("data_source") or "tushare"
            clean.append({k: v for k, v in d.items()
                          if v is not None and k in _ADJ_WRITABLE_COLS})
        if not clean:
            return 0
        # ★ 单只股票全历史 ≈ 6000 行 → 分块写（防 PG 参数上限）+ 按冲突键去重
        from collectors.base import chunk_rows_for_insert, dedupe_rows

        total = 0
        async with raw_session_factory() as session:
            for chunk in chunk_rows_for_insert(
                AdjFactorDB, dedupe_rows(clean, ["symbol", "trade_date"])
            ):
                stmt = pg_insert(AdjFactorDB).values(chunk)
                update_cols = {c.name: stmt.excluded[c.name]
                               for c in AdjFactorDB.__table__.columns
                               if c.name not in ("id", "symbol", "trade_date", "created_at")}
                stmt = stmt.on_conflict_do_update(
                    index_elements=["symbol", "trade_date"],
                    set_=update_cols,
                )
                r = await session.execute(stmt)
                total += r.rowcount or 0
            await session.commit()
            return total


class AdjFactorService:
    name = "adj_factor"
    facet = "tech"
    label = "复权因子"
    description = "单只股票复权因子"
    strategy = "full"
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
