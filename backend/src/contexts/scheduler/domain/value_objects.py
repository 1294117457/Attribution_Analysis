"""scheduler domain value objects

当前只暴露 TriggerType / ModuleName；SchedulePlan 在 entity 内定义。
保留此文件作为后续扩展（Plan/Stats 独立成 VO）的占位。
"""
from contexts.scheduler.domain.entitys.schedule.vo import ModuleName, TriggerType

__all__ = ["ModuleName", "TriggerType"]
