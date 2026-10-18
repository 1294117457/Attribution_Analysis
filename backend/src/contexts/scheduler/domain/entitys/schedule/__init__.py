"""schedule 聚合根（占位骨架）

本期（拆分）只导出 VO / 实体 / 仓储协议。
后续接入 APScheduler 时再补 `application/service/`、`interface/route/`、`run_log/` 等。
"""
from contexts.scheduler.domain.entitys.schedule.entity import Schedule, SchedulePlan
from contexts.scheduler.domain.entitys.schedule.repository import ScheduleRepository
from contexts.scheduler.domain.entitys.schedule.vo import ModuleName, TriggerType

__all__ = [
    "ModuleName",
    "Schedule",
    "SchedulePlan",
    "ScheduleRepository",
    "TriggerType",
]
