"""定时调度端口：应用层决定"何时跑什么"，实现方只负责"到点叫醒"

实现方：infrastructure.adapter.scheduler.apscheduler_adapter.ApschedulerAdapter
"""

from __future__ import annotations

from datetime import datetime
from typing import Awaitable, Callable, Optional, Protocol

from contexts.collect.domain.vo_collect_plan import Schedule

# 到点回调：payload 为 upsert 时传入的命令，原样传回
JobHandler = Callable[[dict], Awaitable[None]]


class SchedulerPort(Protocol):
    def on_fire(self, handler: JobHandler) -> None:
        """注册到点回调（启动期调用一次）"""

    def upsert(self, key: str, schedule: Schedule, payload: dict) -> None:
        """覆盖该 key 下的全部定时"""

    def remove(self, key: str) -> None:
        """删除该 key 下的全部定时"""

    def next_run(self, key: str) -> Optional[datetime]:
        """该 key 的下次触发时间；无定时返回 None"""


__all__ = ["JobHandler", "SchedulerPort"]
