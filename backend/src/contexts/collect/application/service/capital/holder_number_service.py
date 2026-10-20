"""HolderNumberService：股东户数 service

走 repo：HolderNumberRepository
多 symbol 采集：走 asyncio.Semaphore 限并发 + as_completed 边完成边 yield 进度。

Phase 2 重构（2026-10-19）：
    - 注入 CollectLogService + CollectTaskRunner
    - collect() 改为编排入口：创建日志 + 派发任务（不执行实际采集）
    - _run_collect() 为执行入口：实际采集，yield 进度（TaskRunner 消费）
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, AsyncGenerator

from contexts.collect.application.service.base import (
    RateLimited,
    ServiceKind,
    ServiceMeta,
    list_all_a_symbols,
)
from contexts.collect.infrastructure.fetcher.capital.HolderNumberTushareFetcher import (
    HolderNumberTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import HolderNumberRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService
    from contexts.collect.infrastructure.adapter.background import CollectTaskRunner

logger = logging.getLogger(__name__)


class HolderNumberService:

    META = ServiceMeta(
        name='holder_number',
        facet='capital',
        label='股东户数',
        description='全 A 股股东户数（Tushare holder_number）',
        kind=ServiceKind.INCREMENTAL,
        rate_limit=("tushare", 200, 60),
        concurrency=1,  # ★ step8: AsyncSession 非并发安全，收敛为 1（见 08 方案 §5.7）
    )

    def __init__(
        self,
        session: AsyncSession,
        log_service: "CollectLogService",
        task_runner: "CollectTaskRunner",
        fetcher: HolderNumberTushareFetcher | None = None,
        repo: HolderNumberRepository | None = None,
    ) -> None:
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        self._fetcher = fetcher or HolderNumberTushareFetcher()
        self._repo = repo or HolderNumberRepository()

    # ═══════════════════════════════════════════════════════════════
    # 入口 A：HTTP 触发（Route 层调）
    # ═══════════════════════════════════════════════════════════════

    async def collect(self, params: dict) -> dict:
        """HTTP 触发入口：编排（不执行实际采集）"""
        log_id = await self._log_service.create_pending(
            service_name=self.META.name,
            facet=self.META.facet,
            kind=self.META.kind.value,
            params=params,
            trigger_source="manual",
        )
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
        self, params: dict,
    ) -> AsyncGenerator[dict, None]:
        """后台任务执行入口：实际采集，yield 进度（每 symbol 一批）"""
        symbols = params.get("symbols") or []
        if not symbols:
            symbols = await list_all_a_symbols()
            if not symbols:
                yield {
                    "saved": 0, "fail": 1, "total": 0,
                    "message": "symbols 为空，且 stock_basic 暂无数据（请先采集 stock_basic）",
                }
                return
        symbols = [str(s).zfill(6) for s in symbols]
        total = len(symbols)
        sem = asyncio.Semaphore(self.META.concurrency)

        async def _one(s: str) -> int:
            async with sem:
                await check(self.META.rate_limit)
                for attempt in range(3):
                    try:
                        bos = await self._fetcher.fetch(symbol=s)
                        return await self._repo.save(bos, self._session)
                    except RateLimited as e:
                        if attempt < 2:
                            await asyncio.sleep(e.retry_after)
                        else:
                            raise
                return 0

        async def _one_safe(s: str) -> dict:
            try:
                saved = await _one(s)
                return {"saved": saved, "fail": 0, "total": total}
            except Exception as e:
                logger.warning("采集 %s 失败: %s", s, e)
                return {"saved": 0, "fail": 1, "total": total, "message": str(e)}

        tasks = [asyncio.create_task(_one_safe(s)) for s in symbols]
        for coro in asyncio.as_completed(tasks):
            yield await coro


__all__ = ["HolderNumberService"]
