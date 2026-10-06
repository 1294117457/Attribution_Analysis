"""采集定时调度器（APScheduler · 单进程）

job id：plan:{plan_id} / plan:{plan_id}@{HH:MM}
触发时走 CollectManageService.run_plan，与手动触发共用防重与执行流水线。
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


# 定频下限：低于 30 秒会导致任务永远跑不完（每轮触发都 TaskConflict），
# 且极易打爆数据源配额。
MIN_INTERVAL_SECONDS = 30

# 严格 HH:MM（24 小时制、分钟精度、必须补零）
_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

_MAX_TIMES_PER_DAY = 24


def normalize_times(times: Optional[list[str]]) -> list[str]:
    """去重 + 按 HH:MM 升序；非法格式在此处静默丢弃（校验由 validate_schedule 负责）"""
    if not times:
        return []
    valid = {str(t).strip() for t in times if _TIME_RE.match(str(t).strip())}
    return sorted(valid)


def validate_schedule(
    schedule_type: Optional[str],
    times: Optional[list[str]],
    interval_seconds: Optional[int],
) -> None:
    """校验触发配置；非法时抛 ValueError

    - schedule_type 必须是 None / 'time' / 'interval'
    - 'time'：times 至少 1 个、最多 24 个，格式严格 HH:MM
    - 'interval'：interval_seconds 必须 ≥ MIN_INTERVAL_SECONDS
    """
    if schedule_type not in (None, "time", "interval"):
        raise ValueError(f"触发方式无效: {schedule_type}")

    if schedule_type == "time":
        tl = list(times or [])
        if not tl:
            raise ValueError("启用每日定时需要至少一个触发时间")
        if len(tl) > _MAX_TIMES_PER_DAY:
            raise ValueError(f"触发时间最多 {_MAX_TIMES_PER_DAY} 个，当前 {len(tl)} 个")
        for t in tl:
            if not _TIME_RE.match(str(t)):
                raise ValueError(f"时间格式无效: {t!r}（应为 HH:MM，如 09:30）")

    if schedule_type == "interval":
        if interval_seconds is None:
            raise ValueError("启用固定频率需要设置间隔")
        if interval_seconds < MIN_INTERVAL_SECONDS:
            raise ValueError(f"采集间隔不能小于 {MIN_INTERVAL_SECONDS} 秒")


class CollectScheduler:
    def __init__(self, timezone: str) -> None:
        self._tz = ZoneInfo(timezone)
        self._scheduler = AsyncIOScheduler(timezone=self._tz)

    # ── 生命周期 ────────────────────────────────────────────────────────

    async def start(self) -> None:
        from infrastructure.persistence.connection import AsyncSessionLocal
        from infrastructure.persistence.repositories.collect_config_repository import (
            CollectConfigRepoImpl,
        )

        async with AsyncSessionLocal() as session:
            repo = CollectConfigRepoImpl()
            plans = await repo.list_plans(session)
        for p in plans:
            self.sync_plan(p.id, p.enabled, p.schedule_type, p.times, p.interval_seconds)
        self._scheduler.start()
        logger.info("采集调度器已启动: %d 个 job", len(self._scheduler.get_jobs()))

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("采集调度器已关闭")

    # ── job 同步 ────────────────────────────────────────────────────────

    def sync_plan(
        self,
        plan_id: int,
        enabled: bool,
        schedule_type: Optional[str],
        times: Optional[list[str]] = None,
        interval_seconds: Optional[int] = None,
    ) -> None:
        """按方案配置同步 APScheduler job

        job id 约定：
          定时模式： plan:{plan_id}@{HH:MM}   （每个时间点一个独立 job）
          定频模式： plan:{plan_id}           （单 job）
        """
        prefix = f"plan:{plan_id}"
        self._remove_prefix(prefix)          # 必须先清掉该方案的所有旧 job

        if not (enabled and schedule_type):
            return

        if schedule_type == "time":
            for hhmm in normalize_times(times):
                hour, minute = (int(x) for x in hhmm.split(":"))
                self._scheduler.add_job(
                    self._fire_plan,
                    CronTrigger(hour=hour, minute=minute, timezone=self._tz),
                    args=[plan_id],
                    id=f"{prefix}@{hhmm}",
                    replace_existing=True,
                    max_instances=1,
                    coalesce=True,
                    misfire_grace_time=300,
                )
            logger.info("注册采集 job: plan=%d  定时 %s", plan_id, normalize_times(times))
            return

        if schedule_type == "interval":
            if not interval_seconds or interval_seconds < MIN_INTERVAL_SECONDS:
                logger.error(
                    "plan=%d 间隔 %s 无效（下限 %d），未注册",
                    plan_id, interval_seconds, MIN_INTERVAL_SECONDS,
                )
                return
            self._scheduler.add_job(
                self._fire_plan,
                IntervalTrigger(seconds=interval_seconds),
                args=[plan_id],
                id=prefix,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=60,      # 定频容错窗口调小，避免积压补跑
            )
            logger.info("注册采集 job: plan=%d  每 %ds", plan_id, interval_seconds)

    def _remove_prefix(self, prefix: str) -> None:
        """删除该前缀下的所有 job（含 @HH:MM 后缀的多个子 job）

        ⚠️ 必须精确到 prefix + "@"，否则 plan:1 会误删 plan:11@09:30。
        """
        for job in self._scheduler.get_jobs():
            if job.id == prefix or job.id.startswith(prefix + "@"):
                self._scheduler.remove_job(job.id)

    def next_run(self, prefix: str) -> Optional[datetime]:
        """该方案的下次触发时间 = 多个 job 中最早的那个

        ⚠️ APScheduler 3.x 只有在 scheduler 启动后才会把 trigger 编译到
           job._next_run_time；未启动时是空。统一通过 get_next_fire_time 计算。
        """
        from apscheduler.util import convert_to_datetime
        now = datetime.now(tz=self._tz)
        runs: list[datetime] = []
        for job in self._scheduler.get_jobs():
            if not (job.id == prefix or job.id.startswith(prefix + "@")):
                continue
            nrt = getattr(job, "next_run_time", None)
            if nrt is None and job.trigger is not None:
                base = getattr(job, "_next_run_time", None) or now
                nrt = job.trigger.get_next_fire_time(base, now)
            if nrt is not None:
                runs.append(convert_to_datetime(nrt, self._tz, "next_run_time"))
        return min(runs) if runs else None

    # ── 触发 ────────────────────────────────────────────────────────────

    async def _fire_plan(self, plan_id: int) -> None:
        """定时触发：执行整个方案（按 sort_order 顺序跑各方案项）

        ⚠️ 这里 await run_plan 是有意的：job 的 max_instances=1 保证同一方案
           不会重叠执行，阻塞等待不会导致 job 堆积。
        """
        from application.service import CollectManageService
        from infrastructure.config.di import get_collect_manage_service

        svc: CollectManageService = get_collect_manage_service()
        try:
            run_id = await svc.run_plan(plan_id, trigger="schedule")
            logger.info("采集方案 %d 定时触发完成: plan_run_id=%s", plan_id, run_id)
        except Exception:
            logger.exception("采集方案 %d 定时触发失败", plan_id)


_scheduler: Optional[CollectScheduler] = None


def get_collect_scheduler() -> Optional[CollectScheduler]:
    """未启用（COLLECT_SCHEDULER_ENABLED=false）或未启动时返回 None"""
    return _scheduler


async def start_collect_scheduler(timezone: str) -> CollectScheduler:
    global _scheduler
    _scheduler = CollectScheduler(timezone)
    await _scheduler.start()
    return _scheduler


def stop_collect_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None


__all__ = [
    "MIN_INTERVAL_SECONDS",
    "CollectScheduler",
    "get_collect_scheduler",
    "normalize_times",
    "start_collect_scheduler",
    "stop_collect_scheduler",
    "validate_schedule",
]
