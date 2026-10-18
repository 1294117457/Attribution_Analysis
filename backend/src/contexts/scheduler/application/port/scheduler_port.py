"""scheduler application port

本期（拆分）只保留旧的 ApschedulerPort 协议位置，**不实现**。
后续接入 APScheduler 时：
  - 引入 `SchedulerPort`（高层抽象，infrastructure 实现 ApschedulerAdapter）
  - 引入 `ServiceRegistry`（service_name → service 类的查找表，跨 context 用）
  - 引入 `TriggerHandler`（回调封装）

参考：`docs/backend-docs/config/DDD.md` 1.4 interface 层定义。
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

from contexts.scheduler.domain.entitys.schedule.entity import SchedulePlan

# 旧 JobHandler 兼容类型（保留）
JobHandler = Callable[[dict], Awaitable[int]]


@runtime_checkable
class ApschedulerPort(Protocol):
    """APScheduler 调度器接口（暂时不实现）"""

    def upsert(
        self,
        key: str,
        schedule: SchedulePlan,
        payload: dict[str, Any],
    ) -> None: ...

    def remove(self, key: str) -> bool: ...

    def shutdown(self) -> None: ...


__all__ = ["ApschedulerPort", "JobHandler"]
