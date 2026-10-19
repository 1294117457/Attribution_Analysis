"""DailyKlineService：日 K 线 service（按 symbol 维度批量采集 + DB upsert）

Phase 2 重构（2026-10-19）：
    - 注入 CollectLogService + CollectTaskRunner
    - collect() 改为编排入口：创建日志 + 派发任务（不执行实际采集）
    - _run_collect() 为执行入口：实际采集，yield 进度（TaskRunner 消费）
    - 无 AOP 装饰器，日志全手动调

提供：
  - collect(params): HTTP 入口，立即返回 { log_id, status }
  - _run_collect(params, session, log_id, facet, kind): 后台执行入口
  - get(...): 从 DB 读（实时查询入口，前端 RealtimePanel 用）

session 由 DI 工厂注入（get_db，写业务库 kline），不再自己 async with db_session_factory()。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING, AsyncGenerator, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.service.base import (
    ServiceKind,
    ServiceMeta,
    list_all_a_symbols,
)
from contexts.collect.infrastructure.cache.rate_limit import check
from contexts.collect.infrastructure.fetcher.tech.DailyKlineTushareFetcher import (
    DailyKlineTushareFetcher,
)
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService
    from contexts.collect.infrastructure.adapter.background import CollectTaskRunner

logger = logging.getLogger(__name__)


class DailyKlineService:
    """日 K 线采集服务"""

    META = ServiceMeta(
        name="daily_kline",
        facet="tech",
        label="日 K 线",
        description="Tushare pro.daily 日 K 线",
        kind=ServiceKind.INCREMENTAL,
    )

    def __init__(
        self,
        session: AsyncSession,
        log_service: "CollectLogService",
        task_runner: "CollectTaskRunner",
        fetcher: DailyKlineTushareFetcher | None = None,
    ) -> None:
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        self._fetcher = fetcher or DailyKlineTushareFetcher()

    # ═══════════════════════════════════════════════════════════════
    # 入口 A：HTTP 触发（Route 层调）
    # ═══════════════════════════════════════════════════════════════

    async def collect(self, params: dict) -> dict:
        """HTTP 触发入口：编排（不执行实际采集）

        流程：
            1. log_service.create_pending() ← 创建日志（落库 + Redis）
            2. task_runner.dispatch()      ← 派发后台任务
            3. dispatch 失败 → mark_failed() ← 回滚日志
            4. return { log_id, status }

        Returns:
            { log_id, status }
        """
        # 1. 创建日志（业务语义上的"同一事务"：先 create_log，再 dispatch）
        log_id = await self._log_service.create_pending(
            service_name=self.META.name,
            facet=self.META.facet,
            kind=self.META.kind.value,
            params=params,
            trigger_source="manual",
        )

        # 2. 派发后台任务
        try:
            self._task_runner.dispatch(
                log_id=log_id,
                service_name=self.META.name,
                service_class=type(self),  # 传递 class，Runner 内实例化
                facet=self.META.facet,
                kind=self.META.kind.value,
                params=params,
            )
        except Exception as e:
            # 派发失败 → 回滚日志状态
            logger.exception(f"派发采集任务失败: {e}")
            await self._log_service.mark_failed(
                service_name=self.META.name,
                log_id=log_id,
                error=f"派发失败: {e}",
            )
            raise

        return {"log_id": log_id, "status": "pending"}

    # ═══════════════════════════════════════════════════════════════
    # 入口 B：后台执行（TaskRunner 调）
    # ═══════════════════════════════════════════════════════════════

    async def _run_collect(
        self,
        params: dict,
        session: AsyncSession,
        log_id: str,
        *,
        facet: str = "",
        kind: str = "incremental",
    ) -> AsyncGenerator[dict, None]:
        """后台任务执行入口：实际采集

        注意：日志更新全在 TaskRunner._run() 内调 self._log_service
        （本方法只 yield 进度，不直接写日志）

        Yields:
            每批结果 { saved, fail, total }
        """
        symbols = params.get("symbols") or []
        start_date = params.get("start_date")
        end_date = params.get("end_date") or date.today().isoformat()

        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        # 全量模式
        if not symbols:
            symbols = await self._list_all_symbols()
            if not symbols:
                yield {"saved": 0, "fail": 1, "total": 0}
                return

        if not start_date:
            start_date = end_date - timedelta(days=30)

        symbols = [str(s).zfill(6) for s in symbols]
        total = len(symbols)
        sem = asyncio.Semaphore(self.META.concurrency)

        async def one(symbol: str) -> dict:
            async with sem:
                saved = await self._collect_one(symbol, start_date, end_date)
                return {"saved": saved, "fail": 0, "total": total}

        # ★ 使用 as_completed 边完成边 yield
        tasks = [asyncio.create_task(one(s)) for s in symbols]
        for coro in asyncio.as_completed(tasks):
            yield await coro

    # ═══════════════════════════════════════════════════════════════
    # 内部方法（业务逻辑，不涉及日志）
    # ═══════════════════════════════════════════════════════════════

    async def _list_all_symbols(self) -> list[str]:
        return await list_all_a_symbols()

    async def _collect_one(
        self, symbol: str, start_date: date, end_date: date,
    ) -> int:
        """采集单只股票的日 K 线"""
        await check(self.META.rate_limit)
        for attempt in range(3):
            try:
                klines = await self._fetcher.fetch(
                    symbol=symbol, start_date=start_date, end_date=end_date
                )
                if not klines:
                    return 0
                return await self._save(symbol, klines)
            except Exception as e:
                # RateLimited 在 check 里处理，这里只处理其他异常
                if attempt < 2:
                    await asyncio.sleep(1)
                else:
                    raise
        return 0

    async def _save(self, symbol: str, klines) -> int:
        """保存 K 线数据到 DB"""
        if not klines:
            return 0
        try:
            from contexts.market.infrastructure.persistence.models.tech_kline import (
                TechKlineDailyDB,
            )
        except ImportError:
            logger.debug("tech_kline_daily 表未建，跳过入库")
            return 0
        # ★ ORM 模型实际列名是 "date"，不是 "trade_date"。
        #   rows dict 的 key 必须和 ORM column 名严格一致，否则 SQLAlchemy 报
        #   "Unconsumed column names: trade_date"。
        rows = [
            {
                "symbol": k.symbol, "date": k.trade_date,
                "open": k.open, "high": k.high, "low": k.low, "close": k.close,
                "volume": k.volume, "amount": k.amount,
            }
            for k in klines
        ]
        stmt = pg_insert(TechKlineDailyDB).values(rows)
        # ★ 只能更新"rows 中实际存在的列"，否则 UPSERT 会把数据库里
        #   name / change_pct 覆盖成 NULL。
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in [TechKlineDailyDB.open, TechKlineDailyDB.high, TechKlineDailyDB.low,
                      TechKlineDailyDB.close, TechKlineDailyDB.volume, TechKlineDailyDB.amount]
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "date"],
            set_=update_cols,
        )
        r = await self._session.execute(stmt)
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
        stmt = select(TechKlineDailyDB).order_by(TechKlineDailyDB.date.desc())
        if symbol:
            stmt = stmt.where(TechKlineDailyDB.symbol == str(symbol).zfill(6))
        if start_date:
            stmt = stmt.where(TechKlineDailyDB.date >= start_date)
        if end_date:
            stmt = stmt.where(TechKlineDailyDB.date <= end_date)
        stmt = stmt.limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "symbol": r.symbol, "trade_date": r.date.isoformat() if r.date else None,
                "open": r.open, "high": r.high, "low": r.low, "close": r.close,
                "volume": r.volume, "amount": r.amount,
            }
            for r in rows
        ]


__all__ = ["DailyKlineService"]
