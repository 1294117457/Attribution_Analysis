"""SqlRunLogRepository（SQL/ORM 实现）

实现 domain 协议 `RunLogRepository`（Protocol）：
  - create 接受 domain 聚合根，return id
  - finish_success / finish_failed 接受统计 VO + duration
  - list_recent / find 返回 domain 聚合根（**不**泄漏 ORM）

domain 层接口在 `contexts.scheduler.domain.entitys.run_log.repository`。

由原 `SqlCollectRunLogRepository` 迁移重命名而来。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.scheduler.domain.entitys.run_log.entity import RunLog
from contexts.scheduler.domain.entitys.run_log.vo import (
    RunStatus,
    TriggerSource,
)
from contexts.scheduler.infrastructure.persistence.models.run_log import RunLogDB

logger = logging.getLogger(__name__)


# ── ORM → domain 转换 ────────────────────────────────────────

def _to_domain(o: RunLogDB) -> RunLog:
    return RunLog(
        id=o.id,
        schedule_id=o.schedule_id,
        module="collect",   # 本期：旧数据全默认 collect（DB 暂无 module 字段）
        service_name=o.service_name,
        trigger=TriggerSource(o.trigger_type),
        params=dict(o.params or {}),
        started_at=o.started_at,
        finished_at=o.finished_at,
        duration_ms=o.duration_ms,
        status=RunStatus(o.status),
        stats={
            "total": o.total_count,
            "success": o.success_count,
            "fail": o.fail_count,
            "skip": o.skip_count,
            "saved": o.saved_count,
        },
        message=o.message or "",
        error=o.error or "",
        created_at=o.created_at,
    )


# ── 仓储实现 ──────────────────────────────────────────────────

class SqlRunLogRepository:
    """SQL/ORM 实现的运行日志仓储"""

    async def create(self, log: RunLog) -> int:
        """插入新 run（domain 聚合根 → ORM），返回 run_log.id"""
        async with db_session_factory() as session:
            obj = RunLogDB(
                schedule_id=log.schedule_id,
                service_name=log.service_name,
                trigger_type=log.trigger.value,
                params=log.params,
                started_at=log.started_at,
                status=RunStatus.RUNNING.value,
            )
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return obj.id

    async def find(self, log_id: int) -> Optional[RunLog]:
        async with db_session_factory() as session:
            obj = await session.get(RunLogDB, log_id)
            return _to_domain(obj) if obj else None

    async def finish_success(
        self, log_id: int, *,
        total: int, success: int, fail: int, skip: int, saved: int,
        message: str, duration_ms: int,
    ) -> None:
        async with db_session_factory() as session:
            obj = await session.get(RunLogDB, log_id)
            if obj is None:
                return
            obj.finished_at = datetime.now()
            obj.duration_ms = duration_ms
            obj.status = RunStatus.SUCCESS.value
            obj.total_count = total
            obj.success_count = success
            obj.fail_count = fail
            obj.skip_count = skip
            obj.saved_count = saved
            obj.message = message
            await session.commit()

    async def finish_failed(
        self, log_id: int, *, error: str, duration_ms: int,
    ) -> None:
        async with db_session_factory() as session:
            obj = await session.get(RunLogDB, log_id)
            if obj is None:
                return
            obj.finished_at = datetime.now()
            obj.duration_ms = duration_ms
            obj.status = RunStatus.FAILED.value
            obj.error = error
            await session.commit()

    async def list_recent(
        self,
        *,
        service_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RunLog]:
        async with db_session_factory() as session:
            stmt = select(RunLogDB).order_by(RunLogDB.started_at.desc())
            if service_name:
                stmt = stmt.where(RunLogDB.service_name == service_name)
            if status:
                stmt = stmt.where(RunLogDB.status == status)
            stmt = stmt.offset(offset).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return [_to_domain(o) for o in rows]

    async def count(
        self,
        *,
        service_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """按过滤条件统计 run_log 行数（不分页）"""
        async with db_session_factory() as session:
            stmt = select(func.count(RunLogDB.id))
            if service_name:
                stmt = stmt.where(RunLogDB.service_name == service_name)
            if status:
                stmt = stmt.where(RunLogDB.status == status)
            return int((await session.execute(stmt)).scalar_one() or 0)


__all__ = ["SqlRunLogRepository"]
