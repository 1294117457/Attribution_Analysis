"""ConceptListService：概念清单 service

Phase 2 重构（2026-10-19）：
    - 注入 CollectLogService + CollectTaskRunner
    - collect() 改为编排入口：创建日志 + 派发任务（不执行实际采集）
    - _run_collect() 为执行入口：单次 yield（FULL_REFRESH，无参）

走 repo：ConceptRepository
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from contexts.collect.application.service.base import (
    RateLimited,
    ServiceKind,
    ServiceMeta,
)
from contexts.collect.infrastructure.fetcher.fundamental.ConceptListAdataFetcher import (
    ConceptListAdataFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import ConceptRepository

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService
    from contexts.collect.infrastructure.adapter.background import CollectTaskRunner

logger = logging.getLogger(__name__)


class ConceptListService:
    """概念清单 service（FULL_REFRESH：无参）"""

    META = ServiceMeta(
        name="concept_list",
        facet="fundamental",
        label="概念清单",
        description="全概念清单（Adata concept_list；全量覆盖）",
        kind=ServiceKind.FULL_REFRESH,
        concurrency=1,
    )

    def __init__(
        self,
        session: AsyncSession,
        log_service: "CollectLogService",
        task_runner: "CollectTaskRunner",
        fetcher: ConceptListAdataFetcher | None = None,
        repo: ConceptRepository | None = None,
    ) -> None:
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        self._fetcher = fetcher or ConceptListAdataFetcher()
        self._repo = repo or ConceptRepository()

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

        FULL_REFRESH 单次采集：yield 一次结果。

        Yields:
            { saved, fail, total, message }
        """
        for attempt in range(3):
            try:
                bos = await self._fetcher.fetch()
                saved = await self._repo.save(bos, self._session)
                yield {
                    "saved": saved,
                    "fail": 0,
                    "total": 1,
                    "message": f"概念清单: {len(bos)} 条, 写入 {saved}",
                }
                return
            except RateLimited as e:
                if attempt < 2:
                    import asyncio as _a
                    await _a.sleep(e.retry_after)
                else:
                    yield {
                        "saved": 0,
                        "fail": 1,
                        "total": 1,
                        "message": f"重试耗尽: {e}",
                    }
                    return
        # 走到这里说明没 yield
        yield {
            "saved": 0,
            "fail": 1,
            "total": 1,
            "message": "重试耗尽",
        }


__all__ = ["ConceptListService"]