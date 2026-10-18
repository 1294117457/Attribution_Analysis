"""run_log 聚合根（占位骨架）

本期（拆分）只导出 VO / 实体 / 仓储协议。
后续接入 APScheduler 时再补 application service（start/finish_success/finish_failed）。
"""
from contexts.scheduler.domain.entitys.run_log.entity import RunLog
from contexts.scheduler.domain.entitys.run_log.repository import RunLogRepository
from contexts.scheduler.domain.entitys.run_log.vo import (
    RunStats,
    RunStatus,
    TriggerSource,
)

__all__ = [
    "RunLog",
    "RunLogRepository",
    "RunStats",
    "RunStatus",
    "TriggerSource",
]
