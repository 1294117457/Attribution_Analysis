"""采集管理应用服务（业务模块：collect-manage/）

唯一入口：submit / run_one / start_group + plans / groups

依赖通过 port 注入（DDD.md §4）：
- redis:                Redis 端口
- task_registry:        采集任务注册中心
- scheduler:            定时调度器
- session_factory:      session 工厂
- plan_repo:            采集方案/任务组仓储
- realtime_registry:    实时接口注册中心（任务组校验用）
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Coroutine, Optional, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.port.collector_port import (
    CollectParams,
)  # 仅用于类型兼容
from infrastructure.adapter.cache.redis_client import get_redis
from infrastructure.adapter.scheduler.collect import (
    BaseCollectTask,
    UnitResult,
    execute_task,
    get_collect_task_registry,
)
from infrastructure.adapter.scheduler.collect_scheduler import (
    get_collect_scheduler,
    validate_cron,
)
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.models.collect_config import (
    CollectGroupDB,
    CollectPlanDB,
)
from infrastructure.persistence.models.sys_collect_task import (
    SysCollectTaskDB,
)
from infrastructure.persistence.repositories.collect_config_repository import (
    CollectConfigRepoImpl,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# Port 接口
# ════════════════════════════════════════════════════════════════════════


class RedisPort(Protocol):
    async def hset(self, key: str, mapping: dict) -> Any: ...
    async def expire(self, key: str, seconds: int) -> Any: ...


class CollectTaskRegistryPort(Protocol):
    def get(self, task_type: str) -> Optional[BaseCollectTask]: ...
    def supported_types(self) -> list[str]: ...


class CollectSchedulerPort(Protocol):
    def sync_plan(self, task_type: str, enabled: bool, cron: Optional[str]) -> None: ...
    def sync_group(self, group_id: int, enabled: bool, cron: Optional[str]) -> None: ...
    def next_run(self, job_id: str) -> Optional[datetime]: ...


class CollectConfigRepositoryPort(Protocol):
    async def get_plan(self, task_type: str) -> Optional[CollectPlanDB]: ...
    async def list_plans(self) -> list[CollectPlanDB]: ...
    async def upsert_plan(
        self, task_type: str, *, enabled: bool, cron: Optional[str],
        params: dict, trading_day_only: bool,
    ) -> CollectPlanDB: ...
    async def touch_plan(self, task_type: str, task_id: int) -> None: ...
    async def get_group(self, group_id: int) -> Optional[CollectGroupDB]: ...
    async def list_groups(self) -> list[CollectGroupDB]: ...
    async def create_group(self, **fields) -> CollectGroupDB: ...
    async def delete_group(self, group: CollectGroupDB) -> None: ...


class RealtimeRegistryPort(Protocol):
    def get(self, name: str) -> Any: ...


class SessionFactoryPort(Protocol):
    def __call__(self) -> "AsyncContextManager[AsyncSession]": ...


# ════════════════════════════════════════════════════════════════════════
# 异常 + 数据结构
# ════════════════════════════════════════════════════════════════════════


class UnknownTaskType(ValueError):
    pass


class TaskConflict(Exception):
    """同 task_type 已有运行中的任务"""


@dataclass(frozen=True)
class SubmittedTask:
    task_id: int
    task_type: str
    total_count: int
    params: dict


# ── 后台协程托管（关闭时统一取消）──

_background: set[asyncio.Task] = set()


def spawn(coro: Coroutine) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)
    return task


async def cancel_background() -> None:
    tasks = [t for t in _background if not t.done()]
    for t in tasks:
        t.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


# ── 方案 / 任务组的对外字典 ─────────────────────────────────────────────


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def plan_to_dict(handler: BaseCollectTask, plan: Optional[CollectPlanDB]) -> dict:
    scheduler = get_collect_scheduler()
    return {
        "task_type": handler.name,
        "label": handler.label or handler.name,
        "status": handler.status,
        "configured": plan is not None,
        "enabled": plan.enabled if plan else False,
        "cron": plan.cron if plan else None,
        "params": dict(plan.params or {}) if plan else {},
        "trading_day_only": plan.trading_day_only if plan else True,
        "default_params": dict(handler.default_params),
        "last_run_at": _iso(plan.last_run_at) if plan else None,
        "last_task_id": plan.last_task_id if plan else None,
        "next_run_at": _iso(scheduler.next_run(f"plan:{handler.name}")) if scheduler else None,
        "updated_at": _iso(plan.updated_at) if plan else None,
    }


def group_to_dict(group: CollectGroupDB) -> dict:
    scheduler = get_collect_scheduler()
    return {
        "id": group.id,
        "name": group.name,
        "items": list(group.items or []),
        "enabled": group.enabled,
        "cron": group.cron,
        "trading_day_only": group.trading_day_only,
        "stop_on_fail": group.stop_on_fail,
        "last_run_at": _iso(group.last_run_at),
        "last_group_run_id": group.last_group_run_id,
        "next_run_at": _iso(scheduler.next_run(f"group:{group.id}")) if scheduler else None,
        "created_at": _iso(group.created_at),
        "updated_at": _iso(group.updated_at),
    }


def task_to_dict(t: SysCollectTaskDB) -> dict[str, Any]:
    """SysCollectTaskDB → 响应 dict（前端字段契约）"""
    return {
        "id": t.id,
        "task_type": t.task_type,
        "trigger_type": t.trigger_type,
        "params": t.params,
        "status": t.status,
        "total_count": t.total_count,
        "success_count": t.success_count,
        "fail_count": t.fail_count,
        "skip_count": t.skip_count,
        "started_at": _iso(t.started_at),
        "finished_at": _iso(t.finished_at),
        "duration_ms": t.duration_ms,
        "message": t.message,
        "group_run_id": t.group_run_id,
        "created_at": _iso(t.created_at),
    }


# ════════════════════════════════════════════════════════════════════════
# 应用服务
# ════════════════════════════════════════════════════════════════════════


class CollectManageService:
    """采集管理应用服务（依赖注入：port 化所有 infrastructure 依赖）"""

    def __init__(
        self,
        *,
        redis: RedisPort,
        task_registry: CollectTaskRegistryPort,
        scheduler: CollectSchedulerPort,
        config_repo: CollectConfigRepositoryPort,
        realtime_registry: RealtimeRegistryPort,
        session_factory: SessionFactoryPort,
    ) -> None:
        self._redis = redis
        self._task_registry = task_registry
        self._scheduler = scheduler
        self._config_repo = config_repo
        self._realtime_registry = realtime_registry
        self._session_factory = session_factory

    # ── 基础 ──────────────────────────────────────────────────────────

    def handler(self, task_type: str) -> BaseCollectTask:
        handler = self._task_registry.get(task_type)
        if handler is None:
            raise UnknownTaskType(
                f"不支持的任务类型: {task_type}，已支持: {self._task_registry.supported_types()}"
            )
        return handler

    async def resolve_params(self, task_type: str, params: Optional[dict] = None) -> dict:
        handler = self.handler(task_type)
        async with self._session_factory() as session:
            plan = await self._config_repo.get_plan(task_type)
        return {
            **handler.default_params,
            **((plan.params or {}) if plan else {}),
            **(params or {}),
        }

    # ── 后台执行 ──────────────────────────────────────────────────────

    async def prepare(
        self,
        task_type: str,
        params: Optional[dict] = None,
        trigger: str = "manual",
        *,
        group_run_id: Optional[int] = None,
        group_first: bool = False,
    ) -> SubmittedTask:
        """防重 → estimate_total → 写任务行 → 初始化 Redis 进度；不启动执行

        group_first=True 时本行的 group_run_id 取自身 id（任务组第一项）。
        """
        handler = self.handler(task_type)
        merged = await self.resolve_params(task_type, params)

        async with self._session_factory() as session:
            running = await session.execute(
                select(SysCollectTaskDB.id).where(
                    SysCollectTaskDB.task_type == task_type,
                    SysCollectTaskDB.status == "running",
                )
            )
            if running.first():
                raise TaskConflict(f"{task_type} 已有运行中的任务，请等待完成")

            total = await handler.estimate_total(merged)
            task = SysCollectTaskDB(
                task_type=task_type,
                trigger_type=trigger,
                params=merged,
                status="running",
                total_count=total,
                started_at=datetime.now(),
                group_run_id=group_run_id,
            )
            session.add(task)
            await session.flush()
            if group_first:
                task.group_run_id = task.id
            task_id = task.id
            await self._config_repo.touch_plan(task_type, task_id)
            await session.commit()

        key = f"collect:progress:{task_id}"
        await self._redis.hset(key, mapping={
            "total": str(total), "done": "0", "success": "0", "fail": "0",
            "skip": "0", "status": "running", "current": "",
        })
        await self._redis.expire(key, 86400)
        logger.info(
            "创建采集任务: id=%d, type=%s, trigger=%s, total=%d",
            task_id, task_type, trigger, total,
        )
        return SubmittedTask(
            task_id=task_id, task_type=task_type,
            total_count=total, params=merged,
        )

    async def submit(
        self, task_type: str,
        params: Optional[dict] = None, trigger: str = "manual",
    ) -> SubmittedTask:
        sub = await self.prepare(task_type, params, trigger)
        spawn(execute_task(sub.task_id, self.handler(task_type), sub.params))
        return sub

    # ── 同步单元 ──────────────────────────────────────────────────────

    async def run_one(
        self, task_type: str, unit: str, params: Optional[dict] = None,
    ) -> UnitResult:
        handler = self.handler(task_type)
        if not handler.supports_collect_one:
            raise UnknownTaskType(f"{task_type} 不支持按单元调用")
        merged = {**handler.default_params, **(params or {})}
        return await handler.collect_one(unit, merged)

    # ── 采集方案 ──────────────────────────────────────────────────────

    async def list_plans(self) -> list[dict]:
        async with self._session_factory() as session:
            plans = {p.task_type: p for p in await self._config_repo.list_plans()}
        return [
            plan_to_dict(self._task_registry.get(t), plans.get(t))
            for t in self._task_registry.supported_types()
        ]

    async def get_plan(self, task_type: str) -> dict:
        handler = self.handler(task_type)
        async with self._session_factory() as session:
            plan = await self._config_repo.get_plan(task_type)
        return plan_to_dict(handler, plan)

    async def save_plan(
        self,
        task_type: str,
        *,
        enabled: bool,
        cron: Optional[str],
        params: dict,
        trading_day_only: bool,
    ) -> dict:
        handler = self.handler(task_type)
        cron = (cron or "").strip() or None
        if cron:
            validate_cron(cron)
        if enabled and not cron:
            raise ValueError("启用定时需要填写 cron 表达式")
        if enabled and handler.status != "ready":
            raise ValueError(f"{task_type} 尚未实现，不能启用定时")

        async with self._session_factory() as session:
            plan = await self._config_repo.upsert_plan(
                task_type, enabled=enabled, cron=cron, params=params or {},
                trading_day_only=trading_day_only,
            )
            await session.commit()
            await session.refresh(plan)

        self._scheduler.sync_plan(task_type, enabled, cron)
        return plan_to_dict(handler, plan)

    # ── 任务组 ────────────────────────────────────────────────────────

    def _check_group(self, fields: dict) -> dict:
        name = (fields.get("name") or "").strip()
        if not name:
            raise ValueError("任务组名称不能为空")
        items = []
        for item in fields.get("items") or []:
            task_type = item.get("task_type")
            if self._realtime_registry.get(task_type) is not None:
                raise ValueError(f"{task_type} 是实时接口，不能加入任务组")
            handler = self.handler(task_type)
            if handler.status != "ready":
                raise ValueError(f"{task_type} 尚未实现，不能加入任务组")
            items.append({"task_type": task_type, "params": dict(item.get("params") or {})})
        if not items:
            raise ValueError("任务组至少需要一项")
        cron = (fields.get("cron") or "").strip() or None
        if cron:
            validate_cron(cron)
        enabled = bool(fields.get("enabled"))
        if enabled and not cron:
            raise ValueError("启用定时需要填写 cron 表达式")
        return {
            "name": name,
            "items": items,
            "enabled": enabled,
            "cron": cron,
            "trading_day_only": bool(fields.get("trading_day_only", True)),
            "stop_on_fail": bool(fields.get("stop_on_fail", True)),
        }

    async def list_groups(self) -> list[dict]:
        async with self._session_factory() as session:
            return [
                group_to_dict(g)
                for g in await self._config_repo.list_groups()
            ]

    async def create_group(self, fields: dict) -> dict:
        values = self._check_group(fields)
        async with self._session_factory() as session:
            group = await self._config_repo.create_group(**values)
            await session.commit()
            await session.refresh(group)
        self._sync_group(group)
        return group_to_dict(group)

    async def update_group(self, group_id: int, fields: dict) -> dict:
        values = self._check_group(fields)
        async with self._session_factory() as session:
            group = await self._config_repo.get_group(group_id)
            if group is None:
                raise ValueError(f"任务组 {group_id} 不存在")
            for k, v in values.items():
                setattr(group, k, v)
            await session.commit()
            await session.refresh(group)
        self._sync_group(group)
        return group_to_dict(group)

    async def delete_group(self, group_id: int) -> None:
        async with self._session_factory() as session:
            group = await self._config_repo.get_group(group_id)
            if group is None:
                raise ValueError(f"任务组 {group_id} 不存在")
            await self._config_repo.delete_group(group)
            await session.commit()
        self._scheduler.sync_group(group_id, False, None)

    def _sync_group(self, group: CollectGroupDB) -> None:
        self._scheduler.sync_group(group.id, group.enabled, group.cron)

    async def start_group(self, group_id: int, trigger: str = "manual") -> dict:
        async with self._session_factory() as session:
            group = await self._config_repo.get_group(group_id)
            if group is None:
                raise ValueError(f"任务组 {group_id} 不存在")
            info = group_to_dict(group)
        spawn(self.run_group(group_id, trigger))
        return info

    async def run_group(
        self, group_id: int, trigger: str = "manual",
    ) -> Optional[int]:
        """按 items 顺序串行执行；返回 group_run_id（全部跳过时为 None）"""
        async with self._session_factory() as session:
            group = await self._config_repo.get_group(group_id)
            if group is None:
                logger.warning("任务组 %d 不存在，跳过执行", group_id)
                return None
            name, items, stop_on_fail = (
                group.name, list(group.items or []), group.stop_on_fail,
            )

        group_run_id: Optional[int] = None
        logger.info("任务组 [%s] 开始: %d 项, trigger=%s", name, len(items), trigger)

        for idx, item in enumerate(items, 1):
            task_type = item.get("task_type")
            try:
                sub = await self.prepare(
                    task_type, item.get("params"), trigger,
                    group_run_id=group_run_id,
                    group_first=group_run_id is None,
                )
            except TaskConflict as e:
                logger.info("任务组 [%s] 第 %d 项跳过: %s", name, idx, e)
                continue
            except Exception as e:
                logger.error("任务组 [%s] 第 %d 项 %s 创建失败: %s", name, idx, task_type, e)
                if stop_on_fail:
                    break
                continue

            if group_run_id is None:
                group_run_id = sub.task_id
                await self._touch_group(group_id, group_run_id)

            await execute_task(sub.task_id, self.handler(task_type), sub.params)

            async with self._session_factory() as session:
                row = await session.get(SysCollectTaskDB, sub.task_id)
                status = row.status if row else "unknown"
            logger.info(
                "任务组 [%s] 第 %d/%d 项 %s 结束: %s",
                name, idx, len(items), task_type, status,
            )
            if stop_on_fail and status in ("failed", "cancelled"):
                logger.warning(
                    "任务组 [%s] 第 %d 项 %s，停止后续 %d 项",
                    name, idx, status, len(items) - idx,
                )
                break

        logger.info("任务组 [%s] 结束: group_run_id=%s", name, group_run_id)
        return group_run_id

    async def _touch_group(self, group_id: int, group_run_id: int) -> None:
        async with self._session_factory() as session:
            group = await self._config_repo.get_group(group_id)
            if group is not None:
                group.last_run_at = datetime.now()
                group.last_group_run_id = group_run_id
                await session.commit()
