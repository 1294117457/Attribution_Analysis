"""Schedule 仓储接口（domain 定义，infrastructure 实现）

由原 `contexts.collect.domain.entitys.collect_schedule.repository.CollectScheduleRepository`
重命名而来。
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from contexts.scheduler.domain.entitys.schedule.entity import Schedule


@runtime_checkable
class ScheduleRepository(Protocol):
    """调度计划仓储接口

    实现类：`contexts.scheduler.infrastructure.persistence.repositories.SqlScheduleRepository`
    """

    async def list_enabled(self) -> list[Schedule]: ...
    async def list_all(self) -> list[Schedule]: ...
    async def find(self, schedule_id: int) -> Optional[Schedule]: ...
    async def find_enabled(self, schedule_id: int) -> Optional[Schedule]: ...
    async def create(self, schedule: Schedule) -> Schedule: ...
    async def update(
        self, schedule_id: int, **fields
    ) -> Optional[Schedule]: ...
    async def delete(self, schedule_id: int) -> bool: ...


__all__ = ["ScheduleRepository"]
