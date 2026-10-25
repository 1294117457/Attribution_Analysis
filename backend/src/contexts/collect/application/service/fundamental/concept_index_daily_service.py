"""ConceptIndexDailyService：概念指数日 K service

Phase 2 重构（2026-10-19）：
    - 注入 CollectLogService + CollectTaskRunner
    - collect() 改为编排入口：创建日志 + 派发任务（不执行实际采集）
    - _run_collect() 为执行入口：多 index_codes 并发采集，as_completed 边完成边 yield

走 repo：ConceptIndexRepository
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from contexts.collect.application.service.base import (
    RateLimited,
    ServiceKind,
    ServiceMeta,
    list_all_concept_codes,
)
from contexts.collect.infrastructure.fetcher.fundamental.ConceptIndexDailyAdataFetcher import (
    ConceptIndexDailyAdataFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import ConceptIndexRepository

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService
    from contexts.collect.infrastructure.adapter.background import CollectTaskRunner

logger = logging.getLogger(__name__)


class ConceptIndexDailyService:
    """概念指数日 K service（INCREMENTAL：多 index_codes 并发）"""

    META = ServiceMeta(
        name="concept_index_daily",
        facet="fundamental",
        label="概念指数日 K",
        description="概念指数日 K 线（Adata concept_index_daily）",
        kind=ServiceKind.INCREMENTAL,
        concurrency=1,
    )

    def __init__(
        self,
        session: AsyncSession,
        log_service: "CollectLogService",
        task_runner: "CollectTaskRunner",
        fetcher: ConceptIndexDailyAdataFetcher | None = None,
        repo: ConceptIndexRepository | None = None,
    ) -> None:
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        self._fetcher = fetcher or ConceptIndexDailyAdataFetcher()
        self._repo = repo or ConceptIndexRepository()

    # ═══════════════════════════════════════════════════════════════
    # 入口 A：HTTP 触发（Route 层调）
    # ═══════════════════════════════════════════════════════════════

    async def collect(self, params: dict) -> dict:
        """HTTP 触发入口：编排（不执行实际采集）

        Returns:
            { log_id, status }
        """
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
        """后台任务执行入口：实际采集

        INCREMENTAL 多 index_codes 并发：as_completed 边完成边 yield。

        Yields:
            每个 concept 一条 { saved, fail, total, message }
        """
        index_codes = params.get("index_codes") or []
        if not index_codes:
            index_codes = await list_all_concept_codes()
            if not index_codes:
                yield {
                    "saved": 0,
                    "fail": 1,
                    "total": 0,
                    "message": "index_codes 为空，且 concept 暂无数据（请先采集 concept_list）",
                }
                return

        total = len(index_codes)
        sem = asyncio.Semaphore(self.META.concurrency)

        async def one(c: str) -> dict:
            async with sem:
                for attempt in range(3):
                    try:
                        bos = await self._fetcher.fetch(index_code=c)
                        saved = await self._repo.save(bos, self._session)
                        return {"saved": saved, "fail": 0, "total": total}
                    except RateLimited as e:
                        if attempt < 2:
                            import asyncio as _a
                            await _a.sleep(e.retry_after)
                        else:
                            raise
                return {"saved": 0, "fail": 0, "total": total}

        # ★ 使用 as_completed 边完成边 yield
        tasks = [asyncio.create_task(one(c)) for c in index_codes]
        for coro in asyncio.as_completed(tasks):
            try:
                yield await coro
            except Exception as e:
                yield {
                    "saved": 0,
                    "fail": 1,
                    "total": total,
                    "message": str(e),
                }


__all__ = ["ConceptIndexDailyService"]