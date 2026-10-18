"""DailyKlineService：日 K 线 service（按 symbol 维度批量采集 + DB upsert）

提供：
  - collect(params): 批量拉取日 K 线并写入 DB（按 symbol 维度并发）
  - get(...): 从 DB 读（实时查询入口，前端 RealtimePanel 用）
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.collect.application.service.base import CollectResult, RateLimited, list_all_a_symbols
from contexts.collect.infrastructure.fetcher.tech.DailyKlineTushareFetcher import (
    DailyKlineTushareFetcher,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


class DailyKlineService:
    name = "daily_kline"
    facet = "tech"
    sub_facet = "kline_daily"
    label = "日 K 线"
    description = "Tushare pro.daily 日 K 线"
    DEFAULT_PARAMS = {"symbols": [], "start_date": None, "end_date": None}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 5

    def __init__(self, fetcher: DailyKlineTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or DailyKlineTushareFetcher()

    async def collect(self, params: dict) -> CollectResult:
        symbols = params.get("symbols") or []
        start_date = params.get("start_date")
        end_date = params.get("end_date") or date.today().isoformat()
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)
        # 全量模式：symbols 为空 → 拉全 A（list_status=L，按 stock_basic）
        if not symbols:
            symbols = await self._list_all_symbols()
            if not symbols:
                return CollectResult(
                    fail=1,
                    message="symbols 为空，且 stock_basic 暂无数据（请先采集 stock_basic）",
                )
        if not start_date:
            start_date = end_date - timedelta(days=30)
        return await self._collect_batch(
            [str(s).zfill(6) for s in symbols], start_date, end_date,
        )

    async def _list_all_symbols(self) -> list[str]:
        return await list_all_a_symbols()

    async def _collect_batch(
        self, symbols: list[str], start_date: date, end_date: date,
    ) -> CollectResult:
        sem = asyncio.Semaphore(self.CONCURRENCY)

        async def one(symbol: str) -> int:
            async with sem:
                return await self._collect_one(symbol, start_date, end_date)

        results = await asyncio.gather(*[one(s) for s in symbols], return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, int) and r > 0)
        saved = sum(r for r in results if isinstance(r, int))
        fail = sum(1 for r in results if isinstance(r, BaseException))
        return CollectResult(
            total=len(symbols), success=success, fail=fail, saved=saved,
            message=f"日 K 线: 总 {len(symbols)} 只, 成功 {success}, 失败 {fail}, 写入 {saved}",
        )

    async def _collect_one(
        self, symbol: str, start_date: date, end_date: date,
    ) -> int:
        await check(self.RATE_LIMIT)
        for attempt in range(3):
            try:
                klines = await self._fetcher.fetch(
                    symbol=symbol, start_date=start_date, end_date=end_date
                )
                if not klines:
                    return 0
                return await self._save(symbol, klines)
            except RateLimited as e:
                if attempt < 2:
                    await asyncio.sleep(e.retry_after)
                else:
                    raise
        return 0

    async def _save(self, symbol: str, klines) -> int:
        if not klines:
            return 0
        try:
            from contexts.market.infrastructure.persistence.models.tech_kline import (
                TechKlineDailyDB,
            )
        except ImportError:
            logger.debug("tech_kline_daily 表未建，跳过入库")
            return 0
        rows = [
            {
                "symbol": k.symbol, "trade_date": k.trade_date,
                "open": k.open, "high": k.high, "low": k.low, "close": k.close,
                "volume": k.volume, "amount": k.amount,
            }
            for k in klines
        ]
        async with db_session_factory() as session:
            stmt = pg_insert(TechKlineDailyDB).values(rows)
            update_cols = {c.name: stmt.excluded[c.name]
                           for c in TechKlineDailyDB.__table__.columns
                           if c.name not in ("id", "symbol", "trade_date", "created_at")}
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "trade_date"],
                set_=update_cols,
            )
            r = await session.execute(stmt)
            await session.commit()
            return r.rowcount or 0

    # ── 实时查询：从 DB 读（前端"试查"用）─────────────────────
    async def get(
        self,
        symbol: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
    ) -> list[dict]:
        """实时查询日 K 线（从 DB 读，不发 tushare 请求）"""
        try:
            from sqlalchemy import select
            from contexts.market.infrastructure.persistence.models.tech_kline import (
                TechKlineDailyDB,
            )
        except ImportError:
            logger.debug("tech_kline_daily 表未建，返回空")
            return []
        async with db_session_factory() as session:
            stmt = select(TechKlineDailyDB).order_by(TechKlineDailyDB.trade_date.desc())
            if symbol:
                stmt = stmt.where(TechKlineDailyDB.symbol == str(symbol).zfill(6))
            if start_date:
                stmt = stmt.where(TechKlineDailyDB.trade_date >= start_date)
            if end_date:
                stmt = stmt.where(TechKlineDailyDB.trade_date <= end_date)
            stmt = stmt.limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "symbol": r.symbol, "trade_date": r.trade_date.isoformat() if r.trade_date else None,
                    "open": r.open, "high": r.high, "low": r.low, "close": r.close,
                    "volume": r.volume, "amount": r.amount,
                }
                for r in rows
            ]


__all__ = ["DailyKlineService"]
