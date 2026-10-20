"""LimitListService：每日涨跌停板 service

走 repo：LimitListRepository
META.name 是 'limit_list_d'（与 tushare limit_list_d 接口对应）。

Phase 2 重构（2026-10-19）：
    - 注入 CollectLogService + CollectTaskRunner
    - collect() 改为编排入口：创建日志 + 派发任务（不执行实际采集）
    - _run_collect() 为执行入口：实际采集，yield 进度（TaskRunner 消费）
"""
from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING, AsyncGenerator

from contexts.collect.application.service.base import (
    ServiceKind,
    ServiceMeta,
)
from contexts.collect.infrastructure.fetcher.capital.LimitListTushareFetcher import (
    LimitListTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import LimitListRepository
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService
    from contexts.collect.infrastructure.adapter.background import CollectTaskRunner

logger = logging.getLogger(__name__)


class LimitListService:

    META = ServiceMeta(
        name='limit_list_d',
        facet='capital',
        label='每日涨跌停板',
        description='每日涨跌停板（Tushare limit_list_d）',
        kind=ServiceKind.INCREMENTAL,
        rate_limit=("tushare", 100, 60),
        concurrency=1,
    )

    def __init__(
        self,
        session: AsyncSession,
        log_service: "CollectLogService",
        task_runner: "CollectTaskRunner",
        fetcher: LimitListTushareFetcher | None = None,
        repo: LimitListRepository | None = None,
    ) -> None:
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        self._fetcher = fetcher or LimitListTushareFetcher()
        self._repo = repo or LimitListRepository()

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
        """后台任务执行入口：实际采集，yield 进度"""
        td = params.get("trade_date")
        if not td:
            td = date.today()
        if not isinstance(td, date):
            td = date.fromisoformat(str(td))
        await check(self.META.rate_limit)
        try:
            bos = await self._fetcher.fetch(trade_date=td)
            saved = await self._repo.save(bos, self._session)
            yield {
                "saved": saved,
                "fail": 0,
                "skip": 1 if not bos else 0,
                "total": 1,
                "message": f"涨跌停 {td}: {len(bos)} 条, 写入 {saved}",
            }
        except Exception as e:
            logger.exception(f"涨跌停板采集失败: trade_date={td}, err={e}")
            yield {"saved": 0, "fail": 1, "total": 1, "message": str(e)}


__all__ = ["LimitListService"]
