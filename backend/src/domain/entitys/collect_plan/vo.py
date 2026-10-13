"""采集方案值对象：定时配置 + 定时规则

纯 dataclass，零外部依赖；APScheduler 等实现细节在 infrastructure/adapter/scheduler/。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from domain.base import DomainError, ValueObject

# 定频下限：低于 30 秒会导致任务永远跑不完（每轮触发都 TaskConflict），且极易打爆数据源配额
MIN_INTERVAL_SECONDS = 30
MAX_TIMES_PER_DAY = 24
SCHEDULE_TYPES = ("time", "interval")

# 严格 HH:MM（24 小时制、分钟精度、必须补零）
_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class InvalidSchedule(DomainError, ValueError):
    """定时配置非法（继承 ValueError，调用方现有的 except ValueError 无需改动）"""

    def __init__(self, message: str):
        super().__init__(message, code="INVALID_SCHEDULE")


def normalize_times(times: Optional[Iterable[str]]) -> list[str]:
    """去重 + 按 HH:MM 升序；非法格式静默丢弃"""
    if not times:
        return []
    return sorted({str(t).strip() for t in times if _TIME_RE.match(str(t).strip())})


@dataclass(frozen=True)
class Schedule(ValueObject):
    """方案定时配置

    - type="time"：每天在 times 的各个时间点触发（1–24 个，HH:MM，去重升序）
    - type="interval"：每 interval_seconds 秒触发一次（≥ MIN_INTERVAL_SECONDS）
    """

    type: str
    times: tuple[str, ...] = ()
    interval_seconds: Optional[int] = None

    def __post_init__(self) -> None:
        if self.type not in SCHEDULE_TYPES:
            raise InvalidSchedule(f"触发方式无效: {self.type}")

        if self.type == "time":
            for t in self.times:
                if not _TIME_RE.match(str(t)):
                    raise InvalidSchedule(f"时间格式无效: {t!r}（应为 HH:MM，如 09:30）")
            times = tuple(sorted(set(self.times)))
            if not times:
                raise InvalidSchedule("启用每日定时需要至少一个触发时间")
            if len(times) > MAX_TIMES_PER_DAY:
                raise InvalidSchedule(f"触发时间最多 {MAX_TIMES_PER_DAY} 个，当前 {len(times)} 个")
            object.__setattr__(self, "times", times)
            object.__setattr__(self, "interval_seconds", None)
            return

        if self.interval_seconds is None:
            raise InvalidSchedule("启用固定频率需要设置间隔")
        if self.interval_seconds < MIN_INTERVAL_SECONDS:
            raise InvalidSchedule(f"采集间隔不能小于 {MIN_INTERVAL_SECONDS} 秒")
        object.__setattr__(self, "times", ())

    @classmethod
    def from_form(
        cls,
        schedule_type: Optional[str],
        times: Optional[Iterable[str]],
        interval_seconds: Optional[int],
    ) -> Optional["Schedule"]:
        """表单 → VO；schedule_type 为 None 返回 None（不定时）。非法 HH:MM 先静默丢弃再校验"""
        if schedule_type is None:
            return None
        return cls(
            type=schedule_type,
            times=tuple(normalize_times(times)),
            interval_seconds=interval_seconds,
        )

    def _get_values(self) -> tuple:
        return (self.type, self.times, self.interval_seconds)


__all__ = [
    "InvalidSchedule",
    "MAX_TIMES_PER_DAY",
    "MIN_INTERVAL_SECONDS",
    "Schedule",
    "normalize_times",
]
