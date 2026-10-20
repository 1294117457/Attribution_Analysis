"""SuspendService：停复牌 service

Phase 2 重构（2026-10-19）：
    - 注入 CollectLogService + CollectTaskRunner
    - collect() 改为编排入口：创建日志 + 派发任务（不执行实际采集）
    - _run_collect() 为执行入口：实际采集，yield 进度（TaskRunner 消费）
    - 无 AOP 装饰器，日志全手动调

走 repo：SuspendRepository
session 由 DI 工厂注入，透传给 repo.save()。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import AsyncGenerator, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from contexts.collect.application.service.base import (
    RateLimited,
    ServiceKind,
    ServiceMeta,
)
from contexts.collect.infrastructure.cache.rate_limit import check
from contexts.collect.infrastructure.fetcher.tech.SuspendTushareFetcher import (
    SuspendTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import SuspendRepository

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService
    from contexts.collect.infrastructure.adapter.background import CollectTaskRunner

logger = logging.getLogger(__name__)


class SuspendService:

    META = ServiceMeta(
        name='suspend',
        facet='tech',
        label='停复牌',
        description='每日停复牌数据（Tushare suspend）',
        kind=ServiceKind.INCREMENTAL,
        rate_limit=("tushare", 200, 60),
        concurrency=1,
    )

    def __init__(
        self,
        session: AsyncSession,
        log_service: "CollectLogService",
        task_runner: "CollectTaskRunner",
        fetcher: SuspendTushareFetcher | None = None,
        repo: SuspendRepository | None = None,
    ) -> None:
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        self._fetcher = fetcher or SuspendTushareFetcher()
        self._repo = repo or SuspendRepository()

    # ═══════════════════════════════════════════════════════════════
    # 入口 A：HTTP 触发（Route 层调）
    # ═══════════════════════════════════════════════════════════════

    async def collect(self, params: dict) -> dict:
        """HTTP 触发入口：编排（不执行实际采集）

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
        """后台任务执行入口：单次按 trade_date 采集，yield 一次进度

        facet/kind 不再由 Runner 传入 —— service 自身从 self.META 派生。
        session 直接用 self._session（Runner 已通过 service_class(session=...) 注入）。

        Yields:
            单次结果 { saved, fail, total, skip, message }
        """
        td = params.get("trade_date")
        if not td:
            yield {
                "saved": 0,
                "fail": 1,
                "total": 1,
                "skip": 0,
                "message": "trade_date 必填",
            }
            return

        if not isinstance(td, date):
            td = date.fromisoformat(str(td))

        await check(self.META.rate_limit)
        for attempt in range(3):
            try:
                bos = await self._fetcher.fetch(trade_date=td)
                saved = await self._repo.save(bos, self._session)
                yield {
                    "saved": saved,
                    "fail": 0,
                    "total": 1,
                    "skip": 1 if not bos else 0,
                    "message": f"停复牌 {td}: {len(bos)} 条, 写入 {saved}",
                }
                return
            except RateLimited as e:
                if attempt < 2:
                    await asyncio.sleep(e.retry_after)
                else:
                    raise

        # 重试耗尽
        yield {
            "saved": 0,
            "fail": 1,
            "total": 1,
            "skip": 0,
            "message": "重试耗尽",
        }


__all__ = ["SuspendService"]