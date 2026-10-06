"""采集管理应用服务（业务模块：collect-manage/）

唯一入口：submit / run_one / run_plan + plans / fetchers

依赖通过 port 注入（DDD.md §4）：
- redis:                Redis 端口
- task_registry:        采集任务注册中心
- scheduler:            定时调度器
- session_factory:      session 工厂
- config_repo:          采集配置仓储（方案 / 方案项 / 接口元数据）
- realtime_registry:    实时接口注册中心（方案项校验用）
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Coroutine, Optional, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.adapter.scheduler.collect import (
    BaseCollectTask,
    UnitResult,
    execute_task,
)
from infrastructure.adapter.scheduler.collect_scheduler import (
    get_collect_scheduler,
    normalize_times,
    validate_schedule,
)
from infrastructure.persistence.models.collect_config import (
    CollectFetcherDB,
    CollectPlanDB,
    CollectPlanItemDB,
)
from infrastructure.persistence.models.sys_collect_task import (
    SysCollectTaskDB,
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
    def sync_plan(
        self,
        plan_id: int,
        enabled: bool,
        schedule_type: Optional[str],
        times: Optional[list[str]] = None,
        interval_seconds: Optional[int] = None,
    ) -> None: ...
    def next_run(self, prefix: str) -> Optional[datetime]: ...


class CollectConfigRepositoryPort(Protocol):
    # 采集接口元数据
    async def list_fetchers(self, session: AsyncSession) -> list[CollectFetcherDB]: ...
    async def get_fetcher(
        self, task_type: str, session: AsyncSession,
    ) -> Optional[CollectFetcherDB]: ...
    # 采集方案
    async def list_plans(self, session: AsyncSession) -> list[CollectPlanDB]: ...
    async def get_plan(self, plan_id: int, session: AsyncSession) -> Optional[CollectPlanDB]: ...
    async def create_plan(self, session: AsyncSession, **fields) -> CollectPlanDB: ...
    async def update_plan(
        self, session: AsyncSession, plan: CollectPlanDB, **fields,
    ) -> CollectPlanDB: ...
    async def delete_plan(self, session: AsyncSession, plan: CollectPlanDB) -> None: ...
    async def touch_plan(self, session: AsyncSession, plan_id: int, task_id: int) -> None: ...
    # 采集方案项
    async def list_plan_items(
        self, session: AsyncSession, plan_id: int,
    ) -> list[CollectPlanItemDB]: ...
    async def list_all_plan_items(
        self, session: AsyncSession, plan_id: int,
    ) -> list[CollectPlanItemDB]: ...
    async def replace_plan_items(
        self, session: AsyncSession, plan_id: int, items: list[dict],
    ) -> None: ...


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


class PlanNotFound(ValueError):
    """采集方案不存在"""


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


# ── 方案 / 采集接口 的对外字典 ─────────────────────────────────────────


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def fetcher_to_dict(f: CollectFetcherDB) -> dict:
    return {
        "task_type": f.task_type,
        "label": f.label or f.task_type,
        "facet": f.facet,
        "sub_facet": f.sub_facet,
        "description": f.description,
        "kind": f.kind,
        "status": f.status,
        "default_params": dict(f.default_params or {}),
        "supports_run_one": f.supports_run_one,
        "sort_order": f.sort_order,
    }


def plan_to_dict(
    plan: CollectPlanDB,
    items: list[CollectPlanItemDB],
    labels: Optional[dict[str, str]] = None,
) -> dict:
    """labels: task_type → label，由调用方从 fetchers/handler 补充"""
    labels = labels or {}
    scheduler = get_collect_scheduler()
    return {
        "id": plan.id,
        "name": plan.name,
        "enabled": plan.enabled,
        "schedule_type": plan.schedule_type,
        "times": list(plan.times or []),
        "interval_seconds": plan.interval_seconds,
        "stop_on_fail": plan.stop_on_fail,
        "items": [
            {
                "id": it.id,
                "task_type": it.task_type,
                "label": labels.get(it.task_type, it.task_type),
                "params": dict(it.params or {}),
                "enabled": it.enabled,
                "sort_order": it.sort_order,
            }
            for it in items
        ],
        "last_run_at": _iso(plan.last_run_at),
        "last_task_id": plan.last_task_id,
        "next_run_at": _iso(scheduler.next_run(f"plan:{plan.id}")) if scheduler else None,
        "created_at": _iso(plan.created_at),
        "updated_at": _iso(plan.updated_at),
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
        "plan_run_id": t.plan_run_id,
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

    # ── 调度器（未启用时为 None，全部操作降级为 no-op）──────────────────

    def _sync_scheduler(
        self,
        plan_id: int,
        enabled: bool,
        schedule_type: Optional[str],
        times: Optional[list[str]] = None,
        interval_seconds: Optional[int] = None,
    ) -> None:
        """同步定时 job；调度器未启用（COLLECT_SCHEDULER_ENABLED=false）时静默跳过

        这样手动触发方案在无调度器环境下依然可用。
        """
        if self._scheduler is None:
            return
        self._scheduler.sync_plan(
            plan_id, enabled, schedule_type, times, interval_seconds,
        )

    # ── 基础 ────────────────────────────────────────────────────────────

    def handler(self, task_type: str) -> BaseCollectTask:
        handler = self._task_registry.get(task_type)
        if handler is None:
            raise UnknownTaskType(
                f"不支持的任务类型: {task_type}，已支持: {self._task_registry.supported_types()}"
            )
        return handler

    async def resolve_params(
        self,
        task_type: str,
        params: Optional[dict] = None,
        plan_item_params: Optional[dict] = None,
    ) -> dict:
        """参数合并：手动传入 > 方案项 params > default_params

        ⚠️ 不查 DB —— 方案项参数由调用方（run_plan）传入。
        """
        handler = self.handler(task_type)
        return {
            **handler.default_params,
            **(plan_item_params or {}),
            **(params or {}),
        }

    # ── 后台执行 ────────────────────────────────────────────────────────

    async def prepare(
        self,
        task_type: str,
        params: Optional[dict] = None,
        trigger: str = "manual",
        *,
        plan_item_params: Optional[dict] = None,
        plan_run_id: Optional[int] = None,
        plan_first: bool = False,
    ) -> SubmittedTask:
        """防重 → estimate_total → 写任务行 → 初始化 Redis 进度；不启动执行

        plan_first=True 时本行的 plan_run_id 取自身 id（方案执行的第一项）。
        """
        handler = self.handler(task_type)
        merged = await self.resolve_params(task_type, params, plan_item_params)

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
                plan_run_id=plan_run_id,
            )
            session.add(task)
            await session.flush()
            if plan_first:
                task.plan_run_id = task.id
            task_id = task.id
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

    # ── 同步单元 ────────────────────────────────────────────────────────

    async def run_one(
        self, task_type: str, unit: str, params: Optional[dict] = None,
    ) -> UnitResult:
        handler = self.handler(task_type)
        if not handler.supports_collect_one:
            raise UnknownTaskType(f"{task_type} 不支持按单元调用")
        merged = {**handler.default_params, **(params or {})}
        return await handler.collect_one(unit, merged)

    # ── 失败任务重跑（复用原 task_id + 原 params） ─────────────────────

    async def retry_failed(self, task_id: int) -> SubmittedTask:
        """重跑一个失败 / 已取消的任务：复制原 task 的 type+params，新开 task_id

        设计：
          - 不修改原 task 行（保留历史记录用于追溯）
          - 跳过 list_units → 直接用原 task 的 total_count 作为估计
          - 后台协程继续由 spawn 接管

        Raises:
            ValueError: 任务不存在 / 不在终态
        """
        async with self._session_factory() as session:
            orig = await session.get(SysCollectTaskDB, task_id)
            if orig is None:
                raise ValueError(f"任务 {task_id} 不存在")
            if orig.status not in ("failed", "cancelled", "success"):
                raise ValueError(
                    f"任务 {task_id} 状态为 {orig.status}，仅 failed/cancelled/success 可重跑"
                )
            orig_type = orig.task_type
            orig_params = dict(orig.params or {})
            orig_trigger = orig.trigger_type

        sub = await self.prepare(orig_type, orig_params, trigger=orig_trigger)
        spawn(execute_task(sub.task_id, self.handler(orig_type), sub.params))
        logger.info(
            "重跑任务: 原 #%d → 新 #%d (type=%s, trigger=%s)",
            task_id, sub.task_id, orig_type, orig_trigger,
        )
        return sub

    # ── 采集接口元数据 ──────────────────────────────────────────────────

    async def list_fetchers(self) -> list[dict]:
        """列出全部采集接口元数据（UI 的接口选择器数据源）"""
        async with self._session_factory() as session:
            rows = await self._config_repo.list_fetchers(session)
        return [fetcher_to_dict(f) for f in rows]

    # ── 采集方案 CRUD ───────────────────────────────────────────────────

    def _check_plan(self, fields: dict) -> dict:
        """校验 + 归一化方案表单；非法时抛 ValueError"""
        name = (fields.get("name") or "").strip()
        if not name:
            raise ValueError("方案名称不能为空")
        if len(name) > 64:
            raise ValueError("方案名称不能超过 64 个字符")

        schedule_type = fields.get("schedule_type")
        times = normalize_times(fields.get("times"))
        interval_seconds = fields.get("interval_seconds")
        validate_schedule(schedule_type, times, interval_seconds)

        enabled = bool(fields.get("enabled"))
        if enabled and not schedule_type:
            raise ValueError("启用方案需要选择触发方式")

        items = self._validate_items(fields.get("items") or [])
        if not items:
            raise ValueError("方案至少需要包含一个采集接口")
        if enabled and not any(it["enabled"] for it in items):
            raise ValueError("启用方案需要至少一个启用的采集接口")

        return {
            "name": name,
            "enabled": enabled,
            "schedule_type": schedule_type,
            "times": times,
            "interval_seconds": interval_seconds,
            "stop_on_fail": bool(fields.get("stop_on_fail", True)),
            "items": items,
        }

    def _validate_items(self, items: list[dict]) -> list[dict]:
        """校验方案项：已注册 / status=ready / 非实时接口 / 不重复"""
        seen: set[str] = set()
        out: list[dict] = []
        for it in items:
            task_type = (it.get("task_type") or "").strip()
            if not task_type:
                continue
            if task_type in seen:
                raise ValueError(f"方案内重复的采集接口: {task_type}")
            seen.add(task_type)

            if self._realtime_registry.get(task_type) is not None:
                raise ValueError(f"{task_type} 是实时接口，不能加入方案")
            handler = self.handler(task_type)           # 未注册 → UnknownTaskType
            if handler.status != "ready":
                raise ValueError(f"{task_type} 尚未实现，不能加入方案")

            out.append({
                "task_type": task_type,
                "params": dict(it.get("params") or {}),
                "enabled": bool(it.get("enabled", True)),
            })
        return out

    async def _label_map(self, task_types: list[str]) -> dict[str, str]:
        """task_type → label：优先 fetchers 表，其次代码 registry"""
        wanted = set(task_types)
        if not wanted:
            return {}
        async with self._session_factory() as session:
            rows = await self._config_repo.list_fetchers(session)
        out = {f.task_type: (f.label or f.task_type) for f in rows if f.task_type in wanted}
        for t in wanted - set(out):
            h = self._task_registry.get(t)
            if h is not None:
                out[t] = h.label or h.name
        return out

    async def list_plans(self) -> list[dict]:
        async with self._session_factory() as session:
            plans = await self._config_repo.list_plans(session)
            all_items = [
                it
                for p in plans
                for it in await self._config_repo.list_all_plan_items(session, p.id)
            ]
        labels = await self._label_map([it.task_type for it in all_items])
        items_by_plan: dict[int, list[CollectPlanItemDB]] = {}
        for it in all_items:
            items_by_plan.setdefault(it.plan_id, []).append(it)
        return [
            plan_to_dict(p, items_by_plan.get(p.id, []), labels)
            for p in plans
        ]

    async def get_plan(self, plan_id: int) -> dict:
        async with self._session_factory() as session:
            plan = await self._config_repo.get_plan(plan_id, session)
            if plan is None:
                raise PlanNotFound(f"采集方案 {plan_id} 不存在")
            items = await self._config_repo.list_all_plan_items(session, plan_id)
        labels = await self._label_map([it.task_type for it in items])
        return plan_to_dict(plan, items, labels)

    async def create_plan(self, fields: dict) -> dict:
        values = self._check_plan(fields)
        items = values.pop("items")
        async with self._session_factory() as session:
            plan = await self._config_repo.create_plan(session, **values)
            await self._config_repo.replace_plan_items(session, plan.id, items)
            await session.commit()
            await session.refresh(plan)
        self._sync_scheduler(
            plan.id, plan.enabled, plan.schedule_type, plan.times, plan.interval_seconds,
        )
        return await self.get_plan(plan.id)

    async def update_plan(self, plan_id: int, fields: dict) -> dict:
        values = self._check_plan(fields)
        items = values.pop("items")
        async with self._session_factory() as session:
            plan = await self._config_repo.get_plan(plan_id, session)
            if plan is None:
                raise PlanNotFound(f"采集方案 {plan_id} 不存在")
            await self._config_repo.update_plan(session, plan, **values)
            await self._config_repo.replace_plan_items(session, plan_id, items)
            await session.commit()
            await session.refresh(plan)
        self._sync_scheduler(
            plan.id, plan.enabled, plan.schedule_type, plan.times, plan.interval_seconds,
        )
        return await self.get_plan(plan_id)

    async def delete_plan(self, plan_id: int) -> None:
        async with self._session_factory() as session:
            plan = await self._config_repo.get_plan(plan_id, session)
            if plan is None:
                raise PlanNotFound(f"采集方案 {plan_id} 不存在")
            await self._config_repo.delete_plan(session, plan)
            await session.commit()
        # 停用所有 job
        self._sync_scheduler(plan_id, False, None, [], None)

    # ── 方案执行 ────────────────────────────────────────────────────────

    async def start_plan(self, plan_id: int, trigger: str = "manual") -> dict:
        """立即执行一次方案（后台跑，不阻塞）"""
        info = await self.get_plan(plan_id)
        if not any(it["enabled"] for it in info["items"]):
            raise ValueError("方案没有启用的采集接口")
        spawn(self.run_plan(plan_id, trigger))
        return info

    async def run_plan(self, plan_id: int, trigger: str = "manual") -> Optional[int]:
        """按 sort_order 顺序串行执行方案的所有启用项

        Returns: plan_run_id（= 第一项的 task_id）；全部跳过时为 None
        """
        async with self._session_factory() as session:
            plan = await self._config_repo.get_plan(plan_id, session)
            if plan is None:
                logger.warning("采集方案 %d 不存在，跳过执行", plan_id)
                return None
            name = plan.name
            stop_on_fail = plan.stop_on_fail
            # list_plan_items 已按 sort_order 排序并过滤 disabled
            items = await self._config_repo.list_plan_items(session, plan_id)

        plan_run_id: Optional[int] = None
        logger.info("采集方案 [%s] 开始: %d 项, trigger=%s", name, len(items), trigger)

        for idx, item in enumerate(items, 1):
            task_type = item.task_type
            try:
                sub = await self.prepare(
                    task_type, item.params, trigger,
                    plan_item_params=item.params,
                    plan_run_id=plan_run_id,
                    plan_first=plan_run_id is None,
                )
            except TaskConflict as e:
                logger.info("采集方案 [%s] 第 %d 项跳过: %s", name, idx, e)
                continue
            except Exception as e:
                logger.error("采集方案 [%s] 第 %d 项 %s 创建失败: %s", name, idx, task_type, e)
                if stop_on_fail:
                    break
                continue

            if plan_run_id is None:
                plan_run_id = sub.task_id
                await self._touch_plan(plan_id, plan_run_id)

            await execute_task(sub.task_id, self.handler(task_type), sub.params)

            async with self._session_factory() as session:
                row = await session.get(SysCollectTaskDB, sub.task_id)
                status = row.status if row else "unknown"
                ok = row.success_count if row else 0
                fail = row.fail_count if row else 0
            logger.info(
                "采集方案 [%s] 第 %d/%d 项 %s 结束: %s（成功%d 失败%d）",
                name, idx, len(items), task_type, status, ok, fail,
            )
            # ⚠️ 不能只看 status —— _decide_status 里"部分失败也算 success"，
            #   所以额外拦"零成功但有失败"的极端情况。
            if stop_on_fail and (
                status in ("failed", "cancelled") or (ok == 0 and fail > 0)
            ):
                logger.warning(
                    "采集方案 [%s] 第 %d 项 %s（成功%d 失败%d），停止后续 %d 项",
                    name, idx, status, ok, fail, len(items) - idx,
                )
                break

        logger.info("采集方案 [%s] 结束: plan_run_id=%s", name, plan_run_id)
        return plan_run_id

    async def _touch_plan(self, plan_id: int, plan_run_id: int) -> None:
        async with self._session_factory() as session:
            await self._config_repo.touch_plan(session, plan_id, plan_run_id)
            await session.commit()
