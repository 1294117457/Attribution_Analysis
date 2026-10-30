"""DailyKlineService：日 K 线 service（按交易日整批采集 + DB upsert）

提供：
  - expand_calls(params): ★ 按交易日展开成 N 步（给 manager 用 → 可见进度）
  - collect(params): 采集日 K 线并写入 DB
  - get(...): 从 DB 读（实时查询入口，前端 RealtimePanel 用）

★ 为什么要按交易日展开：
  早期实现是「service 内部 while 循环跑完整个区间」，manager 只看得到 1 步
  → 前端进度条全程 0/1，没有任何可见进度。
  现在把天循环**搬到 manager 层**（expand_calls 钩子），
  → total = 交易日数，done 每完成一天 +1 → 前端进度条实时递增。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.db import raw_session_factory
from collectors.base import (
    CollectResult, RateLimited, chunk_rows_for_insert, dedupe_rows,
    list_all_a_symbols,
)
from collectors.tech.DailyKlineTushareFetcher import (
    DailyKlineTushareFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)

# 单条 INSERT 的最大行数（PG 参数上限 65535 / 10 列 ≈ 6500，取 2000 留足余量）
SAVE_CHUNK_SIZE = 2000


def _as_date(value) -> Optional[date]:
    """宽松地把入参转成 date（接受 date / datetime / 'YYYY-MM-DD' / None）。

    ⚠️ ``datetime`` 是 ``date`` 的子类 → isinstance(value, date) 同时覆盖两者。
    """
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


class DailyKlineService:
    name = "daily_kline"
    facet = "tech"
    label = "日 K 线"
    description = "Tushare pro.daily 日 K 线"
    strategy = "incremental"
    # ★ 仍声明 'day'（区间自理型）：因为「按 symbol 补采」这条路径需要 service 自己处理区间。
    #   同时实现 expand_calls 钩子 → 全市场路径按交易日展开成 N 步 → 获得可见进度。
    RANGE = {"start_key": "start_date", "end_date": "end_date", "granularity": "day"}
    QUERYABLE = True
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 5

    def __init__(self, fetcher: DailyKlineTushareFetcher | None = None) -> None:
        self._fetcher = fetcher or DailyKlineTushareFetcher()

    # ── ★ 区间展开钩子（manager 调用）──────────────────────────
    async def expand_calls(self, params: dict) -> Optional[list[dict]]:
        """把「全市场 + 日期区间」展开成「每个交易日一次 collect()」。

        ★ 返回 None = 沿用默认单步语义。

        展开规则：
          - 传了 symbols → **不展开**（逐只补采，区间由 service 内部处理；
            拆成 N 步反而会把同一批 symbol 重复采 N 次）
          - 只有 start_date/end_date（或都没有）→ 按交易日展开
        """
        if params.get("symbols"):
            return None

        start = _as_date(params.get("start_date"))
        end = _as_date(params.get("end_date")) or date.today()
        if start is None:
            start = end - timedelta(days=30)
        if start > end:
            return None

        # ★ 与 manager 的 _trading_days 同源（本地表 → 上游 → 自然日）
        from tasks.manager import trading_days_between

        days = await trading_days_between(start, end)
        if not days:
            return None

        base = {k: v for k, v in params.items()
                if k not in ("start_date", "end_date", "trade_date")}
        return [{**base, "trade_date": d.isoformat()} for d in days]

    async def collect(self, params: dict) -> CollectResult:
        symbols = params.get("symbols") or []
        # ★ 显式传 trade_date（manager 展开后每步都带）→ 只采这一天
        trade_date = _as_date(params.get("trade_date"))
        start_date = _as_date(params.get("start_date"))
        end_date = _as_date(params.get("end_date")) or date.today()

        if trade_date is not None:
            # ── 路径 ①：单日（manager 展开后的一步）───────────────
            return await self._collect_one_day(trade_date)

        # ── 路径 ②：按 symbol 补采（区间自理）────────────────────
        if symbols:
            if not start_date:
                start_date = end_date - timedelta(days=30)
            return await self._collect_batch(
                [str(s).zfill(6) for s in symbols], start_date, end_date,
            )

        # ── 路径 ③：全市场 + 区间（expand_calls 未能展开时的兜底）──
        if not start_date:
            start_date = end_date - timedelta(days=30)
        return await self._collect_by_date(start_date, end_date)

    async def _collect_one_day(self, td: date) -> CollectResult:
        """★ 采集单个交易日的全市场日 K 线（manager 展开后的一步）。

        每个交易日 1 次上游调用 → 限流压力极低（30 天区间只要 30 次）。
        """
        await check(self.RATE_LIMIT)
        try:
            klines = await self._fetcher.fetch_by_date(start_date=td, end_date=td)
        except RateLimited as e:
            await asyncio.sleep(e.retry_after)
            klines = await self._fetcher.fetch_by_date(start_date=td, end_date=td)
        if not klines:
            return CollectResult(
                total=1, skip=1,
                message=f"日 K 线 {td}: 上游无数据（可能非交易日）",
            )
        saved = await self._save_all(klines)
        return CollectResult(
            total=1, success=1, saved=saved,
            message=f"日 K 线 {td}: {len(klines)} 条, 写入 {saved}",
        )

    async def _collect_by_date(
        self, start_date: date, end_date: date,
    ) -> CollectResult:
        """按交易日整批采集（区间自理兜底路径，不展开成多步）。

        ⚠️ 这是**无进度刻度**的路径（manager 只看到 1 步）；
           正常情况下应由 expand_calls 钩子展开成逐日多步。
        """
        await check(self.RATE_LIMIT)
        try:
            klines = await self._fetcher.fetch_by_date(
                start_date=start_date, end_date=end_date
            )
        except RateLimited as e:
            await asyncio.sleep(e.retry_after)
            klines = await self._fetcher.fetch_by_date(
                start_date=start_date, end_date=end_date
            )
        if not klines:
            return CollectResult(
                fail=1,
                message=f"日 K 线 {start_date}~{end_date}: 上游无数据",
            )
        saved = await self._save_all(klines)
        return CollectResult(
            total=1, success=1, saved=saved,
            message=f"日 K 线 {start_date}~{end_date}: {len(klines)} 条, 写入 {saved}",
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
        return await self._save_all(klines)

    async def _save_all(self, klines) -> int:
        """批量 upsert（分块写，避免单条 SQL 参数过多超限）。

        ★ 按日期整批采集时单次可能有 5000+ 行 → 必须分块，
          否则 PG 会报 "too many arguments"。
        """
        if not klines:
            return 0
        try:
            from models.tech_kline import (
                TechKlineDailyDB,
            )
        except ImportError:
            logger.debug("tech_daily 表未建，跳过入库")
            return 0
        # TechKlineDailyDB 列名为 date（trade_date 为兼容别名，此处用 date 落库）
        rows = [
            {
                "symbol": k.symbol, "date": k.trade_date,
                "open": k.open, "high": k.high, "low": k.low, "close": k.close,
                "volume": k.volume, "amount": k.amount, "name": getattr(k, "name", "") or "",
                "change_pct": getattr(k, "change_pct", None),
            }
            for k in klines
        ]
        total = 0
        async with raw_session_factory() as session:
            # ★ 统一走 helper：分块（防 PG 参数上限）+ 按 (symbol, date) 去重
            #   （同一天上游可能返回同一 symbol 多行 → ON CONFLICT 二次命中报错）
            for chunk in chunk_rows_for_insert(
                TechKlineDailyDB, dedupe_rows(rows, ["symbol", "date"])
            ):
                stmt = pg_insert(TechKlineDailyDB).values(chunk)
                update_cols = {c.name: stmt.excluded[c.name]
                               for c in TechKlineDailyDB.__table__.columns
                               if c.name not in ("id", "symbol", "date", "created_at")}
                stmt = stmt.on_conflict_do_update(
                    index_elements=["symbol", "date"],
                    set_=update_cols,
                )
                r = await session.execute(stmt)
                total += r.rowcount or 0
            await session.commit()
            return total

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
            from models.tech_kline import (
                TechKlineDailyDB,
            )
        except ImportError:
            logger.debug("tech_kline_daily 表未建，返回空")
            return []
        async with raw_session_factory() as session:
            stmt = select(TechKlineDailyDB).order_by(TechKlineDailyDB.date.desc())
            if symbol:
                stmt = stmt.where(TechKlineDailyDB.symbol == str(symbol).zfill(6))
            if start_date:
                stmt = stmt.where(TechKlineDailyDB.date >= start_date)
            if end_date:
                stmt = stmt.where(TechKlineDailyDB.date <= end_date)
            stmt = stmt.limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "symbol": r.symbol, "trade_date": r.date.isoformat() if r.date else None,
                    "open": r.open, "high": r.high, "low": r.low, "close": r.close,
                    "volume": r.volume, "amount": r.amount,
                }
                for r in rows
            ]


__all__ = ["DailyKlineService"]
