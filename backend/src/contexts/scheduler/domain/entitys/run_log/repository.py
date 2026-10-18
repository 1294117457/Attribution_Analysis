"""RunLog 仓储接口（domain 定义，infrastructure 实现）

由原 `contexts.collect.domain.entitys.collect_run_log.repository.CollectRunLogRepository`
重命名而来。
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from contexts.scheduler.domain.entitys.run_log.entity import RunLog


@runtime_checkable
class RunLogRepository(Protocol):
    """运行日志仓储接口

    实现类：`contexts.scheduler.infrastructure.persistence.repositories.SqlRunLogRepository`

    设计：append-only（除 status/finished_at/duration_ms/stats/message/error 字段外不可改）
    """

    async def create(self, log: RunLog) -> int:
        """插入新 run；返回 run_log.id"""
        ...

    async def find(self, log_id: int) -> Optional[RunLog]: ...

    async def finish_success(
        self, log_id: int, *,
        total: int, success: int, fail: int, skip: int, saved: int,
        message: str, duration_ms: int,
    ) -> None: ...

    async def finish_failed(
        self, log_id: int, *, error: str, duration_ms: int,
    ) -> None: ...

    async def list_recent(
        self,
        *,
        service_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RunLog]: ...

    async def count(
        self,
        *,
        service_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int: ...


__all__ = ["RunLogRepository"]
