"""NewsService：新闻 service

Phase 3 重构（2026-10-19）：统一 TaskRunner 派发协议
  - collect() 改为编排入口：建日志 + 派发后台任务，立即返回 { log_id, status }
  - _run_collect() 实际采集 + yield 进度（TaskRunner 消费）
  - 无 AOP 装饰器，日志全手动调
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
from contexts.collect.infrastructure.fetcher.news.NewsTushareFetcher import (
    NewsTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import NewsArticleRepository

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService
    from contexts.collect.infrastructure.adapter.background import CollectTaskRunner

logger = logging.getLogger(__name__)


class NewsService:

    META = ServiceMeta(
        name='news',
        facet='news',
        label='新闻快讯',
        description='Tushare 新闻快讯',
        kind=ServiceKind.INCREMENTAL,
        concurrency=1,
    )

    def __init__(
        self,
        session: AsyncSession,
        log_service: "CollectLogService",
        task_runner: "CollectTaskRunner",
        fetcher: NewsTushareFetcher | None = None,
        repo: NewsArticleRepository | None = None,
    ) -> None:
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        self._fetcher = fetcher or NewsTushareFetcher()
        self._repo = repo or NewsArticleRepository()

    # ═══════════════════════════════════════════════════════════════
    # 入口 A：HTTP 触发（Route 层调）
    # ═══════════════════════════════════════════════════════════════

    async def collect(self, params: dict) -> dict:
        """HTTP 触发入口：编排（不执行实际采集）

        Returns:
            {"log_id": "...", "status": "pending"}
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
        self,
        params: dict,
    ) -> AsyncGenerator[dict, None]:
        """后台任务执行入口：实际采集，yield 进度

        facet/kind 不再由 Runner 传入 —— service 自身从 self.META 派生。
        """
        minutes = int(params.get("minutes", 30))
        try:
            for attempt in range(3):
                try:
                    items = await self._fetcher.fetch(minutes=minutes)
                    saved = await self._repo.save_dicts(items, self._session)
                    yield {
                        "saved": saved,
                        "fail": 0 if items else 1,
                        "total": 1,
                        "skip": 1 if not items else 0,
                        "message": f"新闻: {len(items)} 条, 写入 {saved}",
                    }
                    return
                except RateLimited as e:
                    if attempt < 2:
                        import asyncio as _a
                        await _a.sleep(e.retry_after)
                    else:
                        raise
            yield {
                "saved": 0, "fail": 1, "total": 1, "skip": 0,
                "message": "重试耗尽",
            }
        except Exception as e:
            logger.exception("news collect 失败: %r", e)
            yield {
                "saved": 0, "fail": 1, "total": 1, "skip": 0,
                "message": f"采集失败: {e}",
            }


__all__ = ["NewsService"]