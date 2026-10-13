"""采集方案（目前只有定时配置值对象；实体与仓储接口沿用 ORM，见 step5/02 07 §9）"""

from domain.entitys.collect_plan.vo import (
    MAX_TIMES_PER_DAY,
    MIN_INTERVAL_SECONDS,
    InvalidSchedule,
    Schedule,
    normalize_times,
)

__all__ = [
    "InvalidSchedule",
    "MAX_TIMES_PER_DAY",
    "MIN_INTERVAL_SECONDS",
    "Schedule",
    "normalize_times",
]
