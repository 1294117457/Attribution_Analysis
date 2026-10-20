"""AdjFactorService：复权因子 service（按 symbol 维度的批量采集）

Phase 2 重构（2026-10-19）：
    - 注入 CollectLogService + CollectTaskRunner
    - collect() 改为编排入口：创建日志 + 派发任务（不执行实际采集）
    - _run_collect() 为执行入口：实际采集，yield 进度（TaskRunner 消费）
    - 无 AOP 装饰器，日志全手动调

走 repo：AdjFactorRepository（已抽离）
session 由 DI 工厂注入，透传给 repo.save()。
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from contexts.collect.application.service.base import (
    RateLimited,
    ServiceKind,
    ServiceMeta,
    list_all_a_symbols,
)
from contexts.collect.infrastructure.cache.rate_limit import check
from contexts.collect.infrastructure.fetcher.tech.AdjFactorTushareFetcher import (
    AdjFactorTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import AdjFactorRepository

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService
    from contexts.collect.infrastructure.adapter.background import CollectTaskRunner

logger = logging.getLogger(__name__)


class AdjFactorService:

    META = ServiceMeta(
        name='adj_factor',
        facet='tech',
        label='复权因子',
        description='单只股票复权因子（Tushare adj_factor）',
        kind=ServiceKind.INCREMENTAL,
        rate_limit=("tushare", 200, 60),
        concurrency=1,  # ★ step8: AsyncSession 非并发安全，收敛为 1（见 08 方案 §5.7）
    )

    def __init__(
        self,
        session: AsyncSession,
        log_service: "CollectLogService",
        task_runner: "CollectTaskRunner",
        fetcher: AdjFactorTushareFetcher | None = None,
        repo: AdjFactorRepository | None = None,
    ) -> None:
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        self._fetcher = fetcher or AdjFactorTushareFetcher()
        self._repo = repo or AdjFactorRepository()

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
        # 1. 创建日志
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
                params=params,
            )
        except Exception as e:
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
    ) -> AsyncGenerator[dict, None]:
        """后台任务执行入口：实际采集，yield 进度

        facet/kind 不再由 Runner 传入 —— service 自身从 self.META 派生。
        session 直接用 self._session（Runner 已通过 service_class(session=...) 注入）。

        Yields:
            每批结果 { saved, fail, total }
        """
        symbols = params.get("symbols") or []
        if not symbols:
            symbols = await self._list_all_symbols()
            if not symbols:
                yield {
                    "saved": 0,
                    "fail": 1,
                    "total": 0,
                    "skip": 0,
                    "message": "symbols 为空，且 stock_basic 暂无数据（请先采集 stock_basic）",
                }
                return

        symbols = [str(s).zfill(6) for s in symbols]
        total = len(symbols)
        sem = asyncio.Semaphore(self.META.concurrency)

        async def one(symbol: str) -> dict:
            async with sem:
                await check(self.META.rate_limit)
                for attempt in range(3):
                    try:
                        bos = await self._fetcher.fetch(symbol=symbol)
                        saved = await self._repo.save(bos, self._session)
                        return {"saved": saved, "fail": 0, "total": total}
                    except RateLimited as e:
                        if attempt < 2:
                            await asyncio.sleep(e.retry_after)
                        else:
                            raise
                return {"saved": 0, "fail": 1, "total": total}

        # ★ 使用 as_completed 边完成边 yield
        tasks = [asyncio.create_task(one(s)) for s in symbols]
        for coro in asyncio.as_completed(tasks):
            yield await coro

    # ═══════════════════════════════════════════════════════════════
    # 内部方法（业务逻辑，不涉及日志）
    # ═══════════════════════════════════════════════════════════════

    async def _list_all_symbols(self) -> list[str]:
        return await list_all_a_symbols()


__all__ = ["AdjFactorService"]