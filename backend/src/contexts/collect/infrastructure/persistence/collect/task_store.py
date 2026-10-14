"""采集任务行（sys_collect_tasks）的读写

配套设计文档：docs/backend-docs/dev/step5/03collect优化/02-端口与基础设施实现.md §3.2
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from contexts.collect.application.port.collect_port import CollectTaskRecord, CollectTaskStorePort
from contexts.shared.infrastructure.persistence.connection import AsyncSessionLocal
from contexts.collect.infrastructure.persistence.models.sys_collect_task import SysCollectTaskDB


class SqlCollectTaskStore(CollectTaskStorePort):
    """采集任务行读写"""

    async def has_running(self, task_type: str) -> bool:
        async with AsyncSessionLocal() as session:
            row = await session.execute(
                select(SysCollectTaskDB.id).where(
                    SysCollectTaskDB.task_type == task_type,
                    SysCollectTaskDB.status == "running",
                )
            )
            return row.first() is not None

    async def create(
        self, *, task_type: str, trigger: str, params: dict, total: int,
        plan_run_id: int | None, plan_first: bool,
    ) -> int:
        async with AsyncSessionLocal() as session:
            task = SysCollectTaskDB(
                task_type=task_type,
                trigger_type=trigger,
                params=params,
                status="running",
                total_count=total,
                started_at=datetime.now(),
                plan_run_id=plan_run_id,
            )
            session.add(task)
            await session.flush()
            if plan_first:
                task.plan_run_id = task.id
            task_id = task.id
            await session.commit()
            return task_id

    async def get(self, task_id: int) -> CollectTaskRecord | None:
        async with AsyncSessionLocal() as session:
            row = await session.get(SysCollectTaskDB, task_id)
            if row is None:
                return None
            return CollectTaskRecord(
                id=row.id,
                task_type=row.task_type,
                trigger_type=row.trigger_type,
                status=row.status,
                params=dict(row.params or {}),
                total_count=row.total_count,
                success_count=row.success_count,
                fail_count=row.fail_count,
                skip_count=row.skip_count,
            )

    async def finish(
        self, task_id: int, *, status: str, success: int, fail: int, skip: int,
        message: str, duration_ms: int | None = None, total_count: int | None = None,
    ) -> None:
        async with AsyncSessionLocal() as session:
            task = await session.get(SysCollectTaskDB, task_id)
            if task is None:
                return
            task.status = status
            task.success_count = success
            task.fail_count = fail
            task.skip_count = skip
            task.finished_at = datetime.now()
            task.duration_ms = duration_ms
            task.message = message
            if total_count is not None:
                task.total_count = total_count
            await session.commit()


__all__ = ["SqlCollectTaskStore"]
