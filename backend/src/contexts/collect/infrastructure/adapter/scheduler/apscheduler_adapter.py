"""SchedulerPort 的 APScheduler 实现（单进程）

只负责注册 / 删除 job、计算下次触发、到点把 payload 交给回调；
不读仓储、不认识"方案"、不 import Service。

job id：定时模式 {key}@{HH:MM}（每个时间点一个 job），定频模式 {key}（单 job）。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from contexts.collect.application.port.scheduler_port import JobHandler
from contexts.collect.domain.vo_collect_plan.vo import Schedule

logger = logging.getLogger(__name__)

# 容错窗口：定频调小，避免积压补跑
TIME_MISFIRE_GRACE = 300
INTERVAL_MISFIRE_GRACE = 60


class ApschedulerAdapter:
    def __init__(self, timezone: str) -> None:
        self._tz = ZoneInfo(timezone)
        self._scheduler = AsyncIOScheduler(timezone=self._tz)
        self._handler: Optional[JobHandler] = None

    # ── 生命周期 ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._scheduler.start()
        logger.info("调度器已启动: %d 个 job", len(self._scheduler.get_jobs()))

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("调度器已关闭")

    # ── SchedulerPort ──────────────────────────────────────────────────

    def on_fire(self, handler: JobHandler) -> None:
        self._handler = handler

    def upsert(self, key: str, schedule: Schedule, payload: dict) -> None:
        self.remove(key)
        common = dict(args=[key, payload], replace_existing=True, max_instances=1, coalesce=True)
        if schedule.type == "time":
            for hhmm in schedule.times:
                hour, minute = (int(x) for x in hhmm.split(":"))
                self._scheduler.add_job(
                    self._fire,
                    CronTrigger(hour=hour, minute=minute, timezone=self._tz),
                    id=f"{key}@{hhmm}",
                    misfire_grace_time=TIME_MISFIRE_GRACE,
                    **common,
                )
            logger.info("注册定时: %s 定时 %s", key, list(schedule.times))
        else:
            self._scheduler.add_job(
                self._fire,
                IntervalTrigger(seconds=schedule.interval_seconds),
                id=key,
                misfire_grace_time=INTERVAL_MISFIRE_GRACE,
                **common,
            )
            logger.info("注册定时: %s 每 %ds", key, schedule.interval_seconds)

    def remove(self, key: str) -> None:
        for job in self._jobs(key):
            self._scheduler.remove_job(job.id)

    def next_run(self, key: str) -> Optional[datetime]:
        """多个 job 中最早的下次触发时间

        APScheduler 3.x 未启动时 job 上没有 next_run_time，统一用 trigger 计算。
        """
        from apscheduler.util import convert_to_datetime
        now = datetime.now(tz=self._tz)
        runs: list[datetime] = []
        for job in self._jobs(key):
            nrt = getattr(job, "next_run_time", None)
            if nrt is None and job.trigger is not None:
                base = getattr(job, "_next_run_time", None) or now
                nrt = job.trigger.get_next_fire_time(base, now)
            if nrt is not None:
                runs.append(convert_to_datetime(nrt, self._tz, "next_run_time"))
        return min(runs) if runs else None

    # ── 内部 ────────────────────────────────────────────────────────────

    def _jobs(self, key: str) -> list:
        # 必须精确到 key + "@"，否则 plan:1 会误删 plan:11@09:30
        return [
            j for j in self._scheduler.get_jobs()
            if j.id == key or j.id.startswith(key + "@")
        ]

    async def _fire(self, key: str, payload: dict) -> None:
        """到点回调；max_instances=1 保证同一 job 不重叠，回调内阻塞等待不会堆积"""
        if self._handler is None:
            logger.warning("定时 %s 到点但未注册回调，跳过", key)
            return
        try:
            await self._handler(payload)
        except Exception:
            logger.exception("定时 %s 执行失败", key)


__all__ = ["ApschedulerAdapter"]
