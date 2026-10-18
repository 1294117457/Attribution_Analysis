"""RunLog 聚合根

1 行 = 1 次 service.collect() 执行。
状态机：running → success / failed / cancelled
只追加（除 status/finished_at/duration_ms/counts 字段外不可改）。

本文件由原 `contexts.collect.domain.entitys.collect_run_log.entity.CollectRunLog`
迁移重命名而来：
  - CollectRunLog → RunLog
  - 业务规则不变

业务规则：
  - status=running 时 finished_at 必为 None
  - status=success/failed/cancelled 时 finished_at 必非空
  - 不可从 success 跳到 failed（终态）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from shared.domain.base import AggregateRoot

from contexts.scheduler.domain.entitys.run_log.vo import (
    RunStats,
    RunStatus,
    TriggerSource,
)


@dataclass
class RunLog(AggregateRoot):
    """调度运行日志聚合根（跨 context 通用）"""

    id: int
    schedule_id: Optional[int]
    module: str          # 记录所属 context（'collect' / 'market' / ...）
    service_name: str
    trigger: TriggerSource
    params: dict
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    status: RunStatus = RunStatus.RUNNING
    stats: RunStats = field(default_factory=RunStats.empty)
    message: str = ""
    error: str = ""
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)
        if isinstance(self.trigger, str):
            self.trigger = TriggerSource(self.trigger)
        if isinstance(self.status, str):
            self.status = RunStatus(self.status)
        if isinstance(self.stats, dict):
            self.stats = RunStats(**self.stats)

    # ── 状态机 ────────────────────────────────────────────

    _FINAL: frozenset = frozenset({RunStatus.SUCCESS, RunStatus.FAILED, RunStatus.CANCELLED})

    def finish_success(
        self, *,
        total: int, success: int, fail: int, skip: int, saved: int,
        message: str = "",
    ) -> None:
        """标记为成功（仅 running 可调）"""
        if self.status in self._FINAL:
            raise ValueError(f"已处于终态 {self.status}，不能再 finish_success")
        now = datetime.now()
        self.finished_at = now
        self.duration_ms = int((now - self.started_at).total_seconds() * 1000)
        self.status = RunStatus.SUCCESS
        self.stats = RunStats(
            total=total, success=success, fail=fail, skip=skip, saved=saved,
        )
        self.message = message
        self.error = ""

    def finish_failed(self, *, error: str) -> None:
        """标记为失败（仅 running 可调）"""
        if self.status in self._FINAL:
            raise ValueError(f"已处于终态 {self.status}，不能再 finish_failed")
        now = datetime.now()
        self.finished_at = now
        self.duration_ms = int((now - self.started_at).total_seconds() * 1000)
        self.status = RunStatus.FAILED
        self.error = error

    def finish_cancelled(self) -> None:
        """标记为取消（仅 running 可调）"""
        if self.status in self._FINAL:
            raise ValueError(f"已处于终态 {self.status}，不能再 finish_cancelled")
        now = datetime.now()
        self.finished_at = now
        self.duration_ms = int((now - self.started_at).total_seconds() * 1000)
        self.status = RunStatus.CANCELLED

    @property
    def is_final(self) -> bool:
        return self.status in self._FINAL

    @property
    def is_running(self) -> bool:
        return self.status == RunStatus.RUNNING

    # ── 工厂方法 ──────────────────────────────────────────

    @classmethod
    def start(
        cls,
        *,
        service_name: str,
        trigger: str | TriggerSource,
        params: dict,
        module: str = "collect",
        schedule_id: Optional[int] = None,
        started_at: Optional[datetime] = None,
    ) -> "RunLog":
        """工厂：开始一次 run（status=running，finished_at=None）"""
        return cls(
            id=0,
            schedule_id=schedule_id,
            module=module,
            service_name=service_name,
            trigger=trigger,
            params=params,
            started_at=started_at or datetime.now(),
        )


__all__ = ["RunLog"]
