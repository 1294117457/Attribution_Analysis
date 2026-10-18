"""Schedule 聚合根

1 行 = 1 个 service 的调度计划。
由 ScheduleRunner 从 DB 读出后构造；ApplicationService 编排调度时使用。

本文件由原 `contexts.collect.domain.entitys.collect_schedule.entity.CollectSchedule`
迁移重命名而来：
  - CollectSchedule        → Schedule
  - 默认 module=collect     （向后兼容旧数据，全部默认属于 collect）
  - 业务规则不变

业务规则：
  - service_name 必须存在（注册表内）
  - trigger=time: times 非空，interval_seconds 为 None
  - trigger=interval: interval_seconds >= 30
  - concurrency 默认 5
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from shared.domain.base import AggregateRoot

from contexts.scheduler.domain.entitys.schedule.vo import ModuleName, TriggerType


# 旧 CollectSchedule.vo.SchedulePlan 的等价实现（保留原约束）
class SchedulePlan:
    """一次调度计划的可执行形式（由 entity.from_db 构造）

    业务规则：
      - trigger=time: times 非空 + interval_seconds 必为 None
      - trigger=interval: interval_seconds >= 30
    """

    __slots__ = ("trigger", "times", "interval_seconds", "display_name")

    def __init__(
        self,
        *,
        trigger: TriggerType,
        times: list[str] | None = None,
        interval_seconds: Optional[int] = None,
        display_name: str = "",
    ) -> None:
        if trigger == TriggerType.TIME:
            if not times:
                raise ValueError("trigger=time 时 times 不可为空")
            if interval_seconds is not None:
                raise ValueError("trigger=time 时不允许 interval_seconds")
        elif trigger == TriggerType.INTERVAL:
            if interval_seconds is None or interval_seconds < 30:
                raise ValueError("trigger=interval 时 interval_seconds 必填且 >= 30")
            if times:
                raise ValueError("trigger=interval 时不允许 times")
        else:
            raise ValueError(f"未知 trigger: {trigger}")
        self.trigger = trigger
        self.times = list(times or [])
        self.interval_seconds = interval_seconds
        self.display_name = display_name

    def __repr__(self) -> str:
        if self.trigger == TriggerType.TIME:
            return f"SchedulePlan(time, times={self.times})"
        return f"SchedulePlan(interval, seconds={self.interval_seconds})"


@dataclass
class Schedule(AggregateRoot):
    """调度计划聚合根（跨 context 通用）"""

    id: int
    service_name: str
    module: ModuleName
    enabled: bool
    trigger: TriggerType
    times: list[str]
    interval_seconds: Optional[int]
    params: dict
    concurrency: int
    display_name: str = ""
    description: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)
        if isinstance(self.module, str):
            self.module = ModuleName(self.module)
        if isinstance(self.trigger, str):
            self.trigger = TriggerType(self.trigger)

    # ── 业务规则 ──────────────────────────────────────────

    def validate(self) -> None:
        """业务规则校验（构造时自动调用）"""
        if not self.service_name:
            raise ValueError("service_name 必填")
        if self.concurrency < 1:
            raise ValueError("concurrency 必须 >= 1")
        # times/interval 互斥规则由 SchedulePlan 兜底
        SchedulePlan(
            trigger=self.trigger,
            times=self.times,
            interval_seconds=self.interval_seconds,
        )

    # ── 派生属性 ──────────────────────────────────────────

    @property
    def plan(self) -> SchedulePlan:
        """可执行形式（给 ScheduleRunner / APScheduler）"""
        return SchedulePlan(
            trigger=self.trigger,
            times=self.times,
            interval_seconds=self.interval_seconds,
            display_name=self.display_name,
        )

    @property
    def is_time_triggered(self) -> bool:
        return self.trigger == TriggerType.TIME

    @property
    def is_interval_triggered(self) -> bool:
        return self.trigger == TriggerType.INTERVAL

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    # ── 工厂方法 ──────────────────────────────────────────

    @classmethod
    def create(
        cls,
        *,
        service_name: str,
        trigger: str | TriggerType,
        module: str | ModuleName = ModuleName.COLLECT,
        times: Optional[list[str]] = None,
        interval_seconds: Optional[int] = None,
        params: Optional[dict] = None,
        concurrency: int = 5,
        enabled: bool = True,
        display_name: str = "",
        description: str = "",
    ) -> "Schedule":
        """工厂方法：创建调度计划（默认 module=collect，保持向后兼容）"""
        sched = cls(
            id=0,
            service_name=service_name,
            module=ModuleName(module) if isinstance(module, str) else module,
            enabled=enabled,
            trigger=TriggerType(trigger) if isinstance(trigger, str) else trigger,
            times=list(times or []),
            interval_seconds=interval_seconds,
            params=dict(params or {}),
            concurrency=concurrency,
            display_name=display_name,
            description=description,
        )
        sched.validate()
        return sched


__all__ = ["Schedule", "SchedulePlan"]
