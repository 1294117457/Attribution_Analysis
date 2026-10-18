"""scheduler VO

当前只放 RunLog 相关的值对象；Schedule 相关的 VO 在 schedule.vo 模块。
"""
from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    """运行状态"""
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerSource(StrEnum):
    """触发来源"""
    SCHEDULE = "schedule"   # APScheduler 到点
    API = "api"             # HTTP 手动触发
    MANUAL = "manual"       # 内部手工调用


class RunStats:
    """运行计数（不可变）"""

    __slots__ = ("total", "success", "fail", "skip", "saved")

    def __init__(
        self, *, total: int = 0, success: int = 0, fail: int = 0,
        skip: int = 0, saved: int = 0,
    ) -> None:
        if any(n < 0 for n in (total, success, fail, skip, saved)):
            raise ValueError("统计计数不能为负")
        if success + fail + skip > total + 1:  # 容差 1
            raise ValueError(f"success+fail+skip({success+fail+skip}) > total({total})")
        self.total = total
        self.success = success
        self.fail = fail
        self.skip = skip
        self.saved = saved

    @classmethod
    def empty(cls) -> "RunStats":
        return cls()

    def __repr__(self) -> str:
        return (
            f"RunStats(total={self.total} success={self.success} "
            f"fail={self.fail} skip={self.skip} saved={self.saved})"
        )


__all__ = [
    "RunStatus",
    "TriggerSource",
    "RunStats",
]
