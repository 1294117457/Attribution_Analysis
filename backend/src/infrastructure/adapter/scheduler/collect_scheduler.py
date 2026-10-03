"""采集定时调度器（APScheduler · 单进程）

job id：plan:{task_type} / group:{group_id}
触发时走 CollectAppService.submit / run_group，与手动触发共用防重。
trading_day_only 第一版只排除周六日（mkt_calendars 暂无数据）。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def validate_cron(cron: str) -> None:
    """5 段 crontab（分 时 日 月 周）；非法时抛 ValueError"""
    try:
        CronTrigger.from_crontab(cron)
    except ValueError as e:
        raise ValueError(f"cron 表达式无效: {cron}（{e}）") from e


class CollectScheduler:
    def __init__(self, timezone: str) -> None:
        self._tz = ZoneInfo(timezone)
        self._scheduler = AsyncIOScheduler(timezone=self._tz)

    # ── 生命周期 ──────────────────────────────────────────────────────

    async def start(self) -> None:
        from infrastructure.persistence.connection import AsyncSessionLocal
        from infrastructure.persistence.repositories.collect_config_repository import CollectConfigRepoImpl

        async with AsyncSessionLocal() as session:
            repo = CollectConfigRepoImpl(session)
            plans = await repo.list_plans()
            groups = await repo.list_groups()
        for p in plans:
            self.sync_plan(p.task_type, p.enabled, p.cron)
        for g in groups:
            self.sync_group(g.id, g.enabled, g.cron)
        self._scheduler.start()
        logger.info("采集调度器已启动: %d 个 job", len(self._scheduler.get_jobs()))

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("采集调度器已关闭")

    # ── job 同步 ──────────────────────────────────────────────────────

    def sync_plan(self, task_type: str, enabled: bool, cron: Optional[str]) -> None:
        self._sync(f"plan:{task_type}", enabled, cron, self._fire_plan, task_type)

    def sync_group(self, group_id: int, enabled: bool, cron: Optional[str]) -> None:
        self._sync(f"group:{group_id}", enabled, cron, self._fire_group, group_id)

    def _sync(self, job_id: str, enabled: bool, cron: Optional[str], func, arg) -> None:
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
        if not (enabled and cron):
            return
        try:
            trigger = CronTrigger.from_crontab(cron, timezone=self._tz)
        except ValueError as e:
            logger.error("job %s 的 cron 无效，未注册: %s", job_id, e)
            return
        self._scheduler.add_job(
            func, trigger, args=[arg], id=job_id,
            max_instances=1, coalesce=True, misfire_grace_time=300,
        )
        logger.info("注册采集 job: %s  cron=%s", job_id, cron)

    def next_run(self, job_id: str) -> Optional[datetime]:
        job = self._scheduler.get_job(job_id)
        return getattr(job, "next_run_time", None) if job else None

    # ── 触发 ──────────────────────────────────────────────────────────

    def _is_trading_day(self) -> bool:
        return datetime.now(self._tz).weekday() < 5

    async def _fire_plan(self, task_type: str) -> None:
        from application.service import CollectManageService, TaskConflict
        from infrastructure.config.di import get_collect_manage_service

        svc = get_collect_manage_service()
        try:
            sub = await svc.submit(task_type, None, trigger="schedule")
            logger.info("采集方案 %s 定时触发: task_id=%d", task_type, sub.task_id)
        except TaskConflict as e:
            logger.info("采集方案 %s 定时触发跳过: %s", task_type, e)
        except Exception:
            logger.exception("采集方案 %s 定时触发失败", task_type)

    async def _fire_group(self, group_id: int) -> None:
        from application.service import CollectManageService
        from infrastructure.config.di import get_collect_manage_service

        svc = get_collect_manage_service()
        if group is None or not group.enabled:
            return
        if group.trading_day_only and not self._is_trading_day():
            logger.info("任务组 %s：非交易日跳过", group.name)
            return
        try:
            # 放进托管集合，关闭时由 cancel_background 统一取消；await 使 max_instances=1 生效
            from application.service import spawn
            await spawn(svc.run_group(group_id, trigger="schedule"))
        except Exception:
            logger.exception("任务组 %d 定时执行失败", group_id)


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
