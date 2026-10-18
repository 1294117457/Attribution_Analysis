"""SqlScheduleRepository（SQL/ORM 实现）

实现 domain 协议 `ScheduleRepository`（Protocol）：
  - 所有方法返回 `Schedule` 聚合根（**不**泄漏 ORM）

domain 层定义的接口在 `contexts.scheduler.domain.entitys.schedule.repository`，
本类名加 `Sql` 前缀与 Protocol 区分（避免重名冲突）。

由原 `SqlCollectScheduleRepository` 迁移重命名而来。
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.scheduler.domain.entitys.schedule.entity import Schedule
from contexts.scheduler.domain.entitys.schedule.vo import ModuleName, TriggerType
from contexts.scheduler.infrastructure.persistence.models.schedule import ScheduleDB

logger = logging.getLogger(__name__)


# ── ORM → domain 转换 ────────────────────────────────────────

def _to_domain(o: ScheduleDB) -> Schedule:
    """ORM → 聚合根（只读视图；持久化仍走 ORM）"""
    return Schedule(
        id=o.id,
        service_name=o.service_name,
        module=ModuleName.COLLECT,   # 本期：旧数据全默认 collect（DB 暂无 module 字段）
        enabled=bool(o.enabled),
        trigger=TriggerType(o.trigger_type),
        times=list(o.times or []),
        interval_seconds=o.interval_seconds,
        params=dict(o.params or {}),
        concurrency=o.concurrency,
        display_name=o.display_name or "",
        description=o.description or "",
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


def _to_fields(s: Schedule) -> dict:
    """聚合根 → ORM 字段（用于 create / update）"""
    return {
        "service_name": s.service_name,
        "enabled": s.enabled,
        "trigger_type": s.trigger.value,
        "times": list(s.times or []),
        "interval_seconds": s.interval_seconds,
        "params": dict(s.params or {}),
        "concurrency": s.concurrency,
        "display_name": s.display_name or None,
        "description": s.description or None,
    }


# ── 仓储实现 ──────────────────────────────────────────────────

class SqlScheduleRepository:
    """SQL/ORM 实现的调度计划仓储（依赖注入用）"""

    async def list_enabled(self) -> list[Schedule]:
        async with db_session_factory() as session:
            rows = (await session.execute(
                select(ScheduleDB)
                .where(ScheduleDB.enabled.is_(True))
                .order_by(ScheduleDB.id)
            )).scalars().all()
            return [_to_domain(o) for o in rows]

    async def list_all(self) -> list[Schedule]:
        async with db_session_factory() as session:
            rows = (await session.execute(
                select(ScheduleDB).order_by(ScheduleDB.id)
            )).scalars().all()
            return [_to_domain(o) for o in rows]

    async def find(self, schedule_id: int) -> Optional[Schedule]:
        async with db_session_factory() as session:
            obj = await session.get(ScheduleDB, schedule_id)
            return _to_domain(obj) if obj else None

    async def find_enabled(self, schedule_id: int) -> Optional[Schedule]:
        s = await self.find(schedule_id)
        if s is None or not s.enabled:
            return None
        return s

    async def create(self, schedule: Schedule) -> Schedule:
        """按 domain 聚合根创建（用工厂 + 业务校验）"""
        schedule.validate()  # 业务规则
        async with db_session_factory() as session:
            obj = ScheduleDB(**_to_fields(schedule))
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return _to_domain(obj)

    async def update(
        self, schedule_id: int, schedule: Schedule,
    ) -> Optional[Schedule]:
        """按 domain 聚合根更新（先校验再写）"""
        schedule.validate()
        async with db_session_factory() as session:
            obj = await session.get(ScheduleDB, schedule_id)
            if obj is None:
                return None
            for k, v in _to_fields(schedule).items():
                setattr(obj, k, v)
            await session.commit()
            await session.refresh(obj)
            return _to_domain(obj)

    async def delete(self, schedule_id: int) -> bool:
        async with db_session_factory() as session:
            obj = await session.get(ScheduleDB, schedule_id)
            if obj is None:
                return False
            await session.delete(obj)
            await session.commit()
            return True


__all__ = ["SqlScheduleRepository"]
