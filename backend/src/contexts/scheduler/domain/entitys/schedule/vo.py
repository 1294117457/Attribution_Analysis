"""scheduler VO

调度计划 + 运行日志的值对象（按 collect_schedule / collect_run_log 重命名而来）。
"""

from __future__ import annotations

from enum import StrEnum
from typing import Optional


class TriggerType(StrEnum):
    """调度触发类型"""
    TIME = "time"           # 按时间点触发（每天 HH:MM 数组）
    INTERVAL = "interval"   # 按固定间隔触发


class ModuleName(StrEnum):
    """被调度的 service 所属 context（用于多模块调度隔离）"""
    COLLECT = "collect"
    MARKET = "market"
    USER = "user"
    CONCEPT = "concept"
    AUTH = "auth"


__all__ = ["TriggerType", "ModuleName"]
