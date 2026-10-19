# 采集日志进度优化 - Phase 2 重构方案（日志业务独立 + 无 AOP）

> 位置：`docs/backend-docs/dev/level2/step1采集模块优化/06采集日志进度优化/`
> 上游文档：
> - `01-采集日志进度优化方案.md`（v1，Handler 创建日志）
> - `02-采集日志进度优化落地总结.md`（v1 已落地）
> 更新日期：2026-10-19
> 状态：**待评审（暂不修改代码）**
> 阶段：Phase 2（本轮）+ Phase 2 预览（27 service 全部接入）

---

## 〇、设计原则（评审必读）

### 0.1 三条核心原则

| # | 原则 | 含义 |
|---|---|---|
| 1 | **日志 = 独立子系统** | 日志有自己的 route / service / persistence 三个层，**业务逻辑自己闭环** |
| 2 | **采集任务派发 = 独立基础设施** | 派发后台任务的逻辑放在 `infra/adapter/background/`，与 user.contexts.operation_dispatcher 对齐 |
| 3 | **日志操作全在 service 层手动调用，无 AOP** | 每个采集接口 service 注入 `CollectLogService`，在 `collect()` / `_run_collect()` 内部**手动调用**日志服务 |

### 0.2 为什么不用 AOP 装饰器了？

**v1 方案**：用 `@collect_logger` 装饰器拦截 `collect()` 的 yield，自动写日志

**v2 方案（最终）**：
- 装饰器增加了隐晦的调用链：`_run_collect()` → 装饰器 wrapper → 实际代码 → 装饰器拦截
- 日志逻辑应该**显式**出现在 service 和 TaskRunner 代码中，可读性更好
- 日志服务是 DI 注入的，service 层和 TaskRunner 层直接调，更符合依赖倒置原则

### 0.3 "同一事务"是业务语义，不是 DB 事务

```
业务期望："日志创建成功 + 任务派发成功" = 整体成功
        "日志创建失败" 或 "任务派发失败" = 整体回滚

实现方式（collect() 方法内部）：
    1. await log_service.create_pending(...)  ← 落库
    2. task_runner.dispatch(...)              ← 派发
    3. dispatch 失败 → 异常处理中调 log_service.mark_failed(...)
```

**为什么不用 DB 事务？**
- `asyncio.create_task` 不参与 DB 事务（创建后立即返回 task handle）
- 强行包在一个事务里会让 session 持有太久，阻塞 Route
- 业务一致性靠"先 create_log，再 dispatch，失败回滚日志状态"实现

### 0.4 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│  日志子系统（独立闭环）                                        │
│  ┌──────────────────┐                                       │
│  │ log_handler.py   │  GET /collect/logs/*                  │
│  │ (interface/route)│                                       │
│  └────────┬─────────┘                                       │
│           │ Depends                                         │
│           ▼                                                 │
│  ┌──────────────────────────┐                                │
│  │ collect_log_service.py   │  日志业务编排                  │
│  │ (application/service)    │                                │
│  └────────┬─────────────────┘                                │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────────────────┐                            │
│  │ collect_log_repository.py    │  日志仓储                  │
│  │ (infra/persistence)         │                            │
│  └──────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  采集任务派发（独立基础设施）                                  │
│  ┌──────────────────────────────────────────┐                │
│  │ collect_task_runner.py                   │                │
│  │ (infra/adapter/background/)            │                │
│  │                                          │                │
│  │ - dispatch(log_id, service_class, ...)  │                │
│  │ - 注入 CollectLogService                │                │
│  │ - 独立 session（get_db_context）        │                │
│  │ - 维护 task registry                    │                │
│  └──────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  采集接口 service 层（自治，手动调日志）                        │
│  ┌──────────────────────────────────────────┐                │
│  │ {facet}/{service}.py                     │                │
│  │                                          │                │
│  │ collect() ← HTTP 入口                   │                │
│  │     1. 注入日志服务                      │                │
│  │     2. create_pending()                 │                │
│  │     3. task_runner.dispatch()           │                │
│  │     4. 失败 → mark_failed()            │                │
│  │     5. return { log_id, status }       │                │
│  │                                          │                │
│  │ _run_collect() ← 后台任务调             │                │
│  │     1. log_service.mark_running()       │                │
│  │     2. 业务逻辑（yield 进度）           │                │
│  │     3. 实时 update_progress()           │                │
│  │     4. 完成后 mark_finished()          │                │
│  │     5. 异常时 mark_failed()            │                │
│  └──────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

---

## 一、目录结构与改动

### 1.1 现状 vs 目标

**现状**（v1）：

```
interface/manage/
├── collect_handler.py    # 272 行：触发 + 查询混合，handler 内直接写日志
└── ...

application/service/manage/
└── catalog_service.py    # catalog 元数据

infrastructure/aop/
└── collect_logger.py     # v1：free function collect_with_logging()

infrastructure/persistence/repositories/
└── collect_log_repository.py   # v1：纯 DB CRUD
```

**目标**（v2）：

```
interface/manage/
├── collect_handler.py     # ★ 精简：仅触发，删日志业务
├── log_handler.py         # ★ 新增：GET /collect/logs/*
└── router.py              # 改：聚合 3 个 handler

application/service/manage/
├── catalog_service.py     # 不动
└── collect_log_service.py # ★ 新增：日志业务编排

infrastructure/adapter/background/  # ★ 新增目录（与 user 对齐）
├── __init__.py
└── collect_task_runner.py # ★ 新增：后台任务派发器

infrastructure/persistence/repositories/
└── collect_log_repository.py   # 不动（接口保持）

infrastructure/aop/
└── collect_logger.py     # ★ 删除（无 AOP）
```

### 1.2 关键变化总览

| 层 | v1 | v2 |
|---|---|---|
| **Route** | collect_handler 混合触发+查询，handler 内写日志 | 拆出 log_handler；collect_handler 仅透传 |
| **Application Service** | 无独立日志 service | 新增 collect_log_service.py |
| **AOP** | @collect_logger 装饰器拦截 yield | **删除**，日志全手动调 |
| **Infra Adapter** | 无 TaskRunner | 新增 collect_task_runner.py（注入日志服务） |
| **采集接口 service** | 直接调 free function | 注入日志服务 + TaskRunner，手动调用 |

---

## 二、日志子系统

### 2.1 `CollectLogService` 设计

**文件**：`backend/src/contexts/collect/application/service/manage/collect_log_service.py`

**职责**：

| 方法 | 职责 | 调用方 |
|---|---|---|
| `create_pending()` | 创建日志（pending）+ Redis pending hash | collect() |
| `mark_running()` | 状态：pending → running | _run_collect() / TaskRunner |
| `update_progress()` | 实时进度：只写 Redis | _run_collect() |
| `mark_finished()` | 终态：success/partial_fail，写 DB + Redis | _run_collect() |
| `mark_failed()` | 异常：failed，写 DB + Redis | collect() / _run_collect() |
| `list_logs()` | DB 查最近 N 条，合并 Redis 实时进度 | log_handler |
| `get_log()` | DB 查单条，合并 Redis 实时进度 | log_handler |

**完整代码**：

```python
"""CollectLogService — 采集日志业务编排

日志子系统唯一业务入口：
    - 拥有自己的 route（log_handler.py）
    - 拥有自己的 service（本文件）
    - 拥有自己的 repo（collect_log_repository.py）
    - 拥有自己的 redis 实时进度 key

被谁调用：
    1. log_handler.py  → list_logs / get_log
    2. {facet}/{service}.py collect() → create_pending + mark_failed
    3. {facet}/{service}.py _run_collect() → mark_running / update_progress / mark_finished / mark_failed
    4. TaskRunner._run() → mark_running / update_progress / mark_finished / mark_failed
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from contexts.collect.infrastructure.persistence.repositories import (
    CollectLogRepository,
)

logger = logging.getLogger(__name__)

# Redis 实时进度 key 前缀
REDIS_KEY_PREFIX = "collect:log"
REDIS_TTL = 3600  # 1 小时


class CollectLogService:
    """采集日志业务服务（日志子系统唯一业务入口）"""

    def __init__(
        self,
        session: AsyncSession,
        redis_client,  # aioredis.Redis
    ) -> None:
        self._session = session
        self._redis = redis_client
        self._repo = CollectLogRepository(session)

    # ═══════════════════════════════════════════════════════════════
    # 写入方向
    # ═══════════════════════════════════════════════════════════════

    async def create_pending(
        self,
        service_name: str,
        facet: str,
        kind: str,
        params: dict,
        trigger_source: str = "manual",
        trigger_user: str | None = None,
    ) -> str:
        """创建采集日志（pending 状态）

        流程：
            1. 生成 log_id
            2. INSERT collect_logs（pending）
            3. HSET Redis pending hash
            4. EXPIRE Redis 1h

        Returns:
            log_id（UUID 字符串）
        """
        log_id = str(uuid.uuid4())

        # 1. 写 DB
        await self._repo.create(
            id=log_id,
            service_name=service_name,
            facet=facet,
            kind=kind,
            trigger_source=trigger_source,
            trigger_user=trigger_user,
            params=params,
        )

        # 2. 写 Redis pending
        redis_key = self._redis_key(service_name, log_id)
        await self._redis.hset(redis_key, mapping={
            "status": "pending",
            "progress": 0,
            "saved_count": 0,
            "fail_count": 0,
            "total_count": 0,
            "updated_at": datetime.now().isoformat(),
        })
        await self._redis.expire(redis_key, REDIS_TTL)

        return log_id

    async def mark_running(self, service_name: str, log_id: str) -> None:
        """状态：pending → running

        Args:
            service_name: 服务名
            log_id: 日志 ID
        """
        started_at = datetime.now()
        await self._repo.update_status(log_id, "running", started_at=started_at)

        redis_key = self._redis_key(service_name, log_id)
        await self._redis.hset(redis_key, mapping={
            "status": "running",
            "started_at": started_at.isoformat(),
            "updated_at": started_at.isoformat(),
        })

    async def update_progress(
        self,
        service_name: str,
        log_id: str,
        progress: int,
        saved_count: int,
        fail_count: int,
        total_count: int,
    ) -> None:
        """实时进度：只写 Redis（不写 DB，避免 IO 太重）

        Args:
            service_name: 服务名
            log_id: 日志 ID
            progress: 0-100
            saved_count: 已入库记录数
            fail_count: 失败记录数
            total_count: 预估总量
        """
        redis_key = self._redis_key(service_name, log_id)
        await self._redis.hset(redis_key, mapping={
            "progress": min(progress, 100),
            "saved_count": saved_count,
            "fail_count": fail_count,
            "total_count": total_count,
            "updated_at": datetime.now().isoformat(),
        })

    async def mark_finished(
        self,
        service_name: str,
        log_id: str,
        status: str,  # "success" | "partial_fail"
        saved_count: int,
        fail_count: int,
    ) -> None:
        """终态：success / partial_fail

        写 DB 终态 + Redis 终态

        Args:
            service_name: 服务名
            log_id: 日志 ID
            status: "success" | "partial_fail"
            saved_count: 已入库记录数
            fail_count: 失败记录数
        """
        finished_at = datetime.now()
        await self._repo.finish(
            log_id, status, saved_count, fail_count,
            progress=100, finished_at=finished_at,
        )

        redis_key = self._redis_key(service_name, log_id)
        await self._redis.hset(redis_key, mapping={
            "status": status,
            "progress": 100,
            "saved_count": saved_count,
            "fail_count": fail_count,
            "updated_at": finished_at.isoformat(),
        })

    async def mark_failed(
        self,
        service_name: str,
        log_id: str,
        error: str,
        saved_count: int = 0,
        fail_count: int = 0,
    ) -> None:
        """异常：failed（用于派发失败 / 采集异常）

        写 DB failed + Redis failed

        Args:
            service_name: 服务名
            log_id: 日志 ID
            error: 错误信息
            saved_count: 已入库记录数
            fail_count: 失败记录数
        """
        finished_at = datetime.now()
        await self._repo.finish(
            log_id, "failed", saved_count, fail_count,
            error=error[:500], finished_at=finished_at,
        )

        redis_key = self._redis_key(service_name, log_id)
        await self._redis.hset(redis_key, mapping={
            "status": "failed",
            "error": error[:500],
            "updated_at": finished_at.isoformat(),
        })

    # ═══════════════════════════════════════════════════════════════
    # 读取方向
    # ═══════════════════════════════════════════════════════════════

    async def list_logs(
        self,
        service_name: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """查询最近 limit 条日志（合并 Redis 实时进度）"""
        logs = await self._repo.list_recent(service_name, limit=limit)
        for log in logs:
            await self._merge_redis_progress(service_name, log)
        return logs

    async def get_log(
        self,
        service_name: str,
        log_id: str,
    ) -> dict[str, Any] | None:
        """查询单条日志（合并 Redis 实时进度）"""
        log = await self._repo.get_by_id(log_id)
        if log is None:
            return None
        await self._merge_redis_progress(service_name, log)
        return log

    # ═══════════════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════════════

    async def _merge_redis_progress(
        self,
        service_name: str,
        log: dict[str, Any],
    ) -> None:
        """DB 数据 + Redis 实时进度合并（仅 pending/running 状态）"""
        if log.get("status") not in ("pending", "running"):
            return

        redis_key = self._redis_key(service_name, log["id"])
        data = await self._redis.hgetall(redis_key)
        if not data:
            return

        for src, dst in [
            ("status", "status"),
            ("progress", "progress"),
            ("saved_count", "saved_count"),
            ("fail_count", "fail_count"),
            ("total_count", "total_count"),
            ("error", "error_message"),
        ]:
            if src in data:
                if dst in ("progress", "saved_count", "fail_count", "total_count"):
                    log[dst] = int(data[src])
                else:
                    log[dst] = data[src]

    @staticmethod
    def _redis_key(service_name: str, log_id: str) -> str:
        return f"{REDIS_KEY_PREFIX}:{service_name}:{log_id}"


__all__ = ["CollectLogService"]
```

### 2.2 DI 工厂

**文件**：`backend/src/contexts/collect/infrastructure/di/log_service.py`

```python
"""CollectLogService DI 工厂"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.di.db_session import get_db
from shared.infrastructure.di.redis_session import get_redis
from contexts.collect.application.service.manage import CollectLogService


async def get_collect_log_service(
    session: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> CollectLogService:
    """注入 CollectLogService 依赖

    使用场景：
        1. log_handler.py 注入：用于查询
        2. TaskRunner 注入：用于 mark_running / update_progress / mark_finished
        3. 采集接口 service 注入：用于 create_pending / mark_failed
    """
    return CollectLogService(session=session, redis_client=redis)


__all__ = ["get_collect_log_service"]
```

### 2.3 `manage/__init__.py` 导出

```python
"""manage — collect 管理面 service 集合"""
from contexts.collect.application.service.manage.catalog_service import CatalogService
from contexts.collect.application.service.manage.collect_log_service import CollectLogService

__all__ = ["CatalogService", "CollectLogService"]
```

---

## 三、TaskRunner（独立基础设施）

### 3.1 `CollectTaskRunner` 设计

**文件**：`backend/src/contexts/collect/infrastructure/adapter/background/collect_task_runner.py`

**关键设计**：
- 注入 `CollectLogService`（不是直接操作 repo/redis）
- 不持有父请求的 session（参考 `user.contexts.operation_dispatcher`）
- 任务内部 `async with get_db_context()` 创建独立 session
- 进程内 task registry（单例）

**完整代码**：

```python
"""CollectTaskRunner — 后台采集任务派发器

设计要点（参考 user.contexts.infrastructure.adapter.background.operation_dispatcher）：
    - 不持有父请求的 session！后台任务必须自己创建独立 session
    - 维护进程内 task registry（log_id → asyncio.Task）
    - 派发即返回（fire-and-forget）
    - 单例模式（lifespan 内常驻）
    - 注入 CollectLogService，手动调 mark_running / update_progress / mark_finished / mark_failed

对应 user.contexts.operation_dispatcher 的范式。
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService


class CollectTaskRunner:
    """采集后台任务派发器（单例）"""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}  # log_id → Task

    def dispatch(
        self,
        log_id: str,
        service_name: str,
        service_class: type,  # DailyKlineService 等，不是实例
        facet: str,
        kind: str,
        params: dict,
    ) -> None:
        """派发后台任务（立即返回）

        Args:
            log_id: 日志 ID（已由 collect() 创建）
            service_name: 服务名（与 META.name 一致）
            service_class: service 的 class（每次创建新实例）
            facet: 大类
            kind: 采集类型
            params: 采集参数
        """
        task = asyncio.create_task(
            self._run(log_id, service_name, service_class, facet, kind, params)
        )
        self._tasks[log_id] = task
        logger.info(
            "派发采集任务: log_id=%s, service=%s/%s",
            log_id, facet, service_name,
        )

        # 完成后自动清理 registry
        task.add_done_callback(lambda t: self._tasks.pop(log_id, None))

    async def _run(
        self,
        log_id: str,
        service_name: str,
        service_class: type,
        facet: str,
        kind: str,
        params: dict,
    ) -> None:
        """后台任务执行入口

        流程：
            1. 独立 session（get_db_context）
            2. 注入 CollectLogService
            3. 调 service._run_collect()
            4. 手动更新日志：mark_running → update_progress → mark_finished/mark_failed
        """
        from shared.infrastructure.di.db_session import get_db_context
        from shared.infrastructure.di.redis_session import get_redis
        from contexts.collect.application.service.manage import CollectLogService

        # ★ 独立 session（不持父请求的）
        async with get_db_context() as session:
            # ★ 注入 CollectLogService（同一 session）
            redis = await get_redis()
            log_service = CollectLogService(session=session, redis_client=redis)

            try:
                # 实例化 service（注入独立 session）
                svc = service_class(session=session)

                # ★ 1. 标记 running
                await log_service.mark_running(service_name, log_id)

                # ★ 2. 执行采集（generator 模式）
                saved_total = 0
                fail_total = 0
                total = 0

                async for batch in svc._run_collect(
                    params=params,
                    session=session,
                    log_id=log_id,
                    facet=facet,
                    kind=kind,
                ):
                    saved = batch.get("saved", 0)
                    fail = batch.get("fail", 0)
                    total = batch.get("total", total)
                    saved_total += saved
                    fail_total += fail

                    # 计算进度
                    progress = (
                        min(100, int((saved_total + fail_total) / total * 100))
                        if total > 0 else 0
                    )

                    # ★ 3. 实时更新进度（只写 Redis）
                    await log_service.update_progress(
                        service_name=service_name,
                        log_id=log_id,
                        progress=progress,
                        saved_count=saved_total,
                        fail_count=fail_total,
                        total_count=total,
                    )

                # ★ 4. 终态
                if fail_total == 0:
                    status = "success"
                elif saved_total == 0:
                    status = "failed"
                else:
                    status = "partial_fail"

                await log_service.mark_finished(
                    service_name=service_name,
                    log_id=log_id,
                    status=status,
                    saved_count=saved_total,
                    fail_count=fail_total,
                )

            except Exception as e:
                logger.exception(
                    "采集任务失败: log_id=%s, service=%s, err=%r",
                    log_id, service_name, e,
                )
                # ★ 5. 异常：写 failed
                await log_service.mark_failed(
                    service_name=service_name,
                    log_id=log_id,
                    error=str(e),
                    saved_count=saved_total,
                    fail_count=fail_total,
                )

    def is_running(self, log_id: str) -> bool:
        """查询任务是否在跑"""
        task = self._tasks.get(log_id)
        return task is not None and not task.done()

    async def cancel(self, log_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(log_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True


# ── 单例 ────────────────────────────────────────────────────────────

_runner_instance: "CollectTaskRunner | None" = None


def get_collect_task_runner() -> "CollectTaskRunner":
    """获取全局 Runner 单例（lifespan 内常驻）"""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = CollectTaskRunner()
    return _runner_instance


__all__ = ["CollectTaskRunner", "get_collect_task_runner"]
```

### 3.2 DI 工厂

**文件**：`backend/src/contexts/collect/infrastructure/di/runner.py`

```python
"""CollectTaskRunner DI 工厂"""
from contexts.collect.infrastructure.adapter.background import get_collect_task_runner

__all__ = ["get_collect_task_runner"]
```

> TaskRunner 是单例，不需要 FastAPI Depends，直接 `get_collect_task_runner()` 即可。

### 3.3 `infrastructure/adapter/background/__init__.py`

```python
from contexts.collect.infrastructure.adapter.background.collect_task_runner import (
    CollectTaskRunner,
    get_collect_task_runner,
)

__all__ = ["CollectTaskRunner", "get_collect_task_runner"]
```

---

## 四、采集接口 service 层（自治）

### 4.1 `collect()` 与 `_run_collect()` 的分工

每个采集接口 service（如 `DailyKlineService`）有两个入口：

| 方法 | 调用方 | 职责 |
|---|---|---|
| `collect(params)` | Route 层 | 编排：创建日志 + 派发任务，返回 `{ log_id, status }` |
| `_run_collect(params, session, log_id, facet, kind)` | TaskRunner | 执行：实际采集，yield 进度 |

### 4.2 `collect_handler.py`（精简版）

**文件**：`backend/src/contexts/collect/interface/manage/collect_handler.py`

```python
"""collect_handler — 触发采集端点（Route 层零业务）

提供：
    POST /collect/{facet}/{service_name}

设计说明：
    - Route 层不持有 session
    - Route 层不处理业务逻辑
    - 通过 service 工厂注册表找到 service 实例
    - service.collect() 内部完成：create_log + dispatch_task
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from shared.interface import _response as R
from contexts.collect.infrastructure.di.collect_service_factory import get_service_by_name

router = APIRouter(prefix="/collect", tags=["采集-触发"])


@router.post(
    "/{facet}/{service_name}",
    summary="触发采集",
)
async def trigger_collect(
    facet: str,
    service_name: str,
    body: dict,
) -> dict[str, Any]:
    """触发采集 - Route 层纯入口"""
    factory = get_service_by_name(service_name)
    if factory is None:
        raise HTTPException(404, f"service {service_name!r} 不存在")

    # factory() 内部 Depends 注入 session/log_service/task_runner
    svc = await factory()

    # service.collect() 内部：create_pending + dispatch + 失败回滚
    result = await svc.collect(body.get("params", {}))

    return R.ok({
        **result,
        "service_name": service_name,
        "facet": facet,
        "message": "采集任务已创建，请通过 /collect/logs/{service_name} 轮询进度",
    })


__all__ = ["router"]
```

### 4.3 `DailyKlineService` 完整改造示例

**文件**：`backend/src/contexts/collect/application/service/tech/daily_kline_service.py`

```python
"""DailyKlineService：日 K 线 service（v2）

v2 改造（2026-10-19）：
    - 注入 CollectLogService + CollectTaskRunner
    - collect()：编排入口（创建日志 + 派发任务）
    - _run_collect()：执行入口（实际采集，yield 进度）
    - 日志全手动调，无 AOP 装饰器
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING, AsyncGenerator, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert

from contexts.collect.application.service.base import (
    ServiceKind, ServiceMeta, list_all_a_symbols,
)
from contexts.collect.infrastructure.cache.rate_limit import check
from contexts.collect.infrastructure.fetcher.tech.DailyKlineTushareFetcher import (
    DailyKlineTushareFetcher,
)
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService
    from contexts.collect.infrastructure.adapter.background import CollectTaskRunner

logger = logging.getLogger(__name__)


class DailyKlineService:
    META = ServiceMeta(
        name="daily_kline", facet="tech", sub_facet="kline_daily",
        label="日 K 线", description="Tushare pro.daily 日 K 线",
        kind=ServiceKind.INCREMENTAL,
        param_schema=[
            {"key": "symbols", "ui": "symbols_list", "label": "股票代码",
             "required": False, "placeholder": "每行一只：000001\n000002",
             "help": "留空表示全量采集"},
            {"key": "start_date", "ui": "date_str", "label": "开始日期",
             "required": False, "placeholder": "2024-01-01",
             "help": "留空默认回溯 30 天"},
            {"key": "end_date", "ui": "date_str", "label": "结束日期",
             "required": False, "placeholder": "2024-12-31",
             "help": "留空默认今天"},
        ],
        rate_limit=("tushare", 200, 60),
        concurrency=5,
    )

    def __init__(
        self,
        session: AsyncSession,
        log_service: "CollectLogService",
        task_runner: "CollectTaskRunner",
        fetcher: DailyKlineTushareFetcher | None = None,
    ) -> None:
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        self._fetcher = fetcher or DailyKlineTushareFetcher()

    # ═══════════════════════════════════════════════════════════════
    # 入口 A：HTTP 触发（Route 层调）
    # ═══════════════════════════════════════════════════════════════

    async def collect(
        self,
        params: dict,
    ) -> dict:
        """HTTP 触发入口：编排（不执行实际采集）

        流程：
            1. 注入日志服务
            2. create_pending() ← 创建日志（落库 + Redis）
            3. task_runner.dispatch() ← 派发后台任务
            4. dispatch 失败 → mark_failed() ← 回滚日志
            5. return { log_id, status }

        Returns:
            { log_id, status }
        """
        # 1. 创建日志（同一事务：create_pending + dispatch）
        log_id = await self._log_service.create_pending(
            service_name=self.META.name,
            facet=self.META.facet,
            kind=self.META.kind.value,
            params=params,
            trigger_source="manual",
        )

        # 2. 派发后台任务
        try:
            self._task_runner.dispatch(
                log_id=log_id,
                service_name=self.META.name,
                service_class=type(self),  # 传递 class，Runner 内实例化
                facet=self.META.facet,
                kind=self.META.kind.value,
                params=params,
            )
        except Exception as e:
            # 派发失败 → 回滚日志状态
            logger.exception(f"派发采集任务失败: {e}")
            await self._log_service.mark_failed(
                service_name=self.META.name,
                log_id=log_id,
                error=f"派发失败: {e}",
            )
            raise

        return {"log_id": log_id, "status": "pending"}

    # ═══════════════════════════════════════════════════════════════
    # 入口 B：后台执行（TaskRunner 调）
    # ═══════════════════════════════════════════════════════════════

    async def _run_collect(
        self,
        params: dict,
        session: AsyncSession,
        log_id: str,
        *,
        facet: str = "",
        kind: str = "incremental",
    ) -> AsyncGenerator[dict, None]:
        """后台任务执行入口：实际采集

        注意：日志更新全在 TaskRunner._run() 内调 self._log_service
        （本方法只 yield 进度，不直接写日志）

        Yields:
            每批结果 { saved, fail, total }
        """
        symbols = params.get("symbols") or []
        start_date = params.get("start_date")
        end_date = params.get("end_date") or date.today().isoformat()

        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        # 全量模式
        if not symbols:
            symbols = await self._list_all_symbols()
            if not symbols:
                yield {"saved": 0, "fail": 1, "total": 0}
                return

        if not start_date:
            start_date = end_date - timedelta(days=30)

        symbols = [str(s).zfill(6) for s in symbols]
        total = len(symbols)
        sem = asyncio.Semaphore(self.META.concurrency)

        async def one(symbol: str) -> dict:
            async with sem:
                saved = await self._collect_one(symbol, start_date, end_date)
                return {"saved": saved, "fail": 0, "total": total}

        # ★ 使用 as_completed 边完成边 yield
        tasks = [asyncio.create_task(one(s)) for s in symbols]
        for coro in asyncio.as_completed(tasks):
            yield await coro

    # ═══════════════════════════════════════════════════════════════
    # 内部方法（业务逻辑，不涉及日志）
    # ═══════════════════════════════════════════════════════════════

    async def _list_all_symbols(self) -> list[str]:
        return await list_all_a_symbols()

    async def _collect_one(
        self, symbol: str, start_date: date, end_date: date,
    ) -> int:
        """采集单只股票的日 K 线"""
        await check(self.META.rate_limit)
        for attempt in range(3):
            try:
                klines = await self._fetcher.fetch(
                    symbol=symbol, start_date=start_date, end_date=end_date
                )
                if not klines:
                    return 0
                return await self._save(symbol, klines)
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(1)
                else:
                    raise
        return 0

    async def _save(self, symbol: str, klines) -> int:
        """保存 K 线数据到 DB"""
        if not klines:
            return 0
        try:
            from contexts.market.infrastructure.persistence.models.tech_kline import (
                TechKlineDailyDB,
            )
        except ImportError:
            logger.debug("tech_kline_daily 表未建，跳过入库")
            return 0

        rows = [
            {
                "symbol": k.symbol, "trade_date": k.trade_date,
                "open": k.open, "high": k.high, "low": k.low, "close": k.close,
                "volume": k.volume, "amount": k.amount,
            }
            for k in klines
        ]
        stmt = pg_insert(TechKlineDailyDB).values(rows)
        update_cols = {c.name: stmt.excluded[c.name]
                       for c in TechKlineDailyDB.__table__.columns
                       if c.name not in ("id", "symbol", "trade_date", "created_at")}
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "trade_date"],
            set_=update_cols,
        )
        r = await self._session.execute(stmt)
        return r.rowcount or 0

    # ── 实时查询（不动）─────────────────────────────
    async def get(
        self,
        symbol: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
    ) -> list[dict]:
        """实时查询日 K 线（从 DB 读，不发 tushare 请求）"""
        try:
            from sqlalchemy import select
            from contexts.market.infrastructure.persistence.models.tech_kline import (
                TechKlineDailyDB,
            )
        except ImportError:
            logger.debug("tech_kline_daily 表未建，返回空")
            return []
        stmt = select(TechKlineDailyDB).order_by(TechKlineDailyDB.trade_date.desc())
        if symbol:
            stmt = stmt.where(TechKlineDailyDB.symbol == str(symbol).zfill(6))
        if start_date:
            stmt = stmt.where(TechKlineDailyDB.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(TechKlineDailyDB.trade_date <= end_date)
        stmt = stmt.limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "symbol": r.symbol, "trade_date": r.trade_date.isoformat() if r.trade_date else None,
                "open": r.open, "high": r.high, "low": r.low, "close": r.close,
                "volume": r.volume, "amount": r.amount,
            }
            for r in rows
        ]


__all__ = ["DailyKlineService"]
```

### 4.4 `collect_service_factory.py`（service 工厂注册表）

**文件**：`backend/src/contexts/collect/infrastructure/di/collect_service_factory.py`

```python
"""service 工厂注册表

为 Route 层提供统一的 service 实例化入口。
每个 factory 内部 Depends 注入 session / log_service / task_runner。
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.di.db_session import get_db
from shared.infrastructure.di.redis_session import get_redis
from contexts.collect.application.service.manage import CollectLogService
from contexts.collect.infrastructure.adapter.background import get_collect_task_runner

# ═══════════════════════════════════════════════════════════════
# 28 个 service factory
# ═══════════════════════════════════════════════════════════════

async def get_daily_kline_service(
    session: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> "DailyKlineService":
    from contexts.collect.application.service.tech.daily_kline_service import DailyKlineService
    from contexts.collect.application.service.manage import CollectLogService
    from contexts.collect.infrastructure.adapter.background import get_collect_task_runner

    log_service = CollectLogService(session=session, redis_client=redis)
    task_runner = get_collect_task_runner()
    return DailyKlineService(session=session, log_service=log_service, task_runner=task_runner)


async def get_adj_factor_service(
    session: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> "AdjFactorService":
    from contexts.collect.application.service.tech.adj_factor_service import AdjFactorService
    from contexts.collect.application.service.manage import CollectLogService
    from contexts.collect.infrastructure.adapter.background import get_collect_task_runner

    log_service = CollectLogService(session=session, redis_client=redis)
    task_runner = get_collect_task_runner()
    return AdjFactorService(session=session, log_service=log_service, task_runner=task_runner)


# ... 其他 26 个 service 同理 ...


# ═══════════════════════════════════════════════════════════════
# 注册表
# ═══════════════════════════════════════════════════════════════

SERVICE_FACTORIES: dict[str, Callable[..., Awaitable[Any]]] = {
    "daily_kline": get_daily_kline_service,
    "adj_factor": get_adj_factor_service,
    # ... 其他 26 个 ...
}


def get_service_by_name(service_name: str) -> Callable[..., Awaitable[Any]] | None:
    """按 service_name 查找 factory"""
    return SERVICE_FACTORIES.get(service_name)


__all__ = [
    "SERVICE_FACTORIES",
    "get_service_by_name",
    "get_daily_kline_service",
    "get_adj_factor_service",
    # ... 其他 factory ...
]
```

> **注**：实际代码中 28 个 factory 会很长，可以按 facet 分组放在不同文件，但注册表 `SERVICE_FACTORIES` 保持在一个地方。

### 4.5 DI 工厂的 `__init__.py`

```python
"""di — collect 模块依赖注入工厂"""
from contexts.collect.infrastructure.di.log_service import get_collect_log_service
from contexts.collect.infrastructure.di.collect_service_factory import get_service_by_name

__all__ = ["get_collect_log_service", "get_service_by_name"]
```

---

## 五、日志查询端点

### 5.1 `log_handler.py`

```python
"""log_handler — 采集日志查询端点

提供：
    GET /collect/logs/{service_name}            日志列表
    GET /collect/logs/{service_name}/{log_id}   单条日志详情

设计说明：
    - Route 层不持有 session
    - 实时进度由 CollectLogService 内部合并（DB + Redis）
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from shared.interface import _response as R
from contexts.collect.application.service.manage import CollectLogService
from contexts.collect.infrastructure.di.log_service import get_collect_log_service

router = APIRouter(prefix="/collect/logs", tags=["采集-日志查询"])


@router.get(
    "/{service_name}",
    summary="查询某 service 的最近采集日志",
)
async def list_logs(
    service_name: str,
    limit: int = 10,
    log_service: CollectLogService = Depends(get_collect_log_service),
) -> dict[str, Any]:
    """查询最近 limit 条日志（DB + Redis 实时进度合并）"""
    items = await log_service.list_logs(service_name=service_name, limit=limit)
    return R.ok({"items": items})


@router.get(
    "/{service_name}/{log_id}",
    summary="查询单条采集日志详情",
)
async def get_log(
    service_name: str,
    log_id: str,
    log_service: CollectLogService = Depends(get_collect_log_service),
) -> dict[str, Any]:
    """查询单条日志（DB + Redis 实时进度合并）"""
    log = await log_service.get_log(log_id=log_id, service_name=service_name)
    if log is None:
        raise HTTPException(status_code=404, detail=f"日志 {log_id!r} 不存在")
    return R.ok(log)


__all__ = ["router"]
```

### 5.2 `router.py`

```python
"""manage/router — 管理面所有 handler 的总装（APIRouter 聚合）"""
from fastapi import APIRouter

from contexts.collect.interface.manage.catalog_handler import router as catalog_router
from contexts.collect.interface.manage.collect_handler import router as collect_router
from contexts.collect.interface.manage.log_handler import router as log_router

manage_router = APIRouter()

# 注册顺序：log_router 在前，避免 /collect/logs 与 /collect/{facet} 冲突
manage_router.include_router(log_router)
manage_router.include_router(collect_router)
manage_router.include_router(catalog_router)

__all__ = ["manage_router"]
```

---

## 六、完整调用链

### 6.1 POST 触发采集

```
前端
  │ POST /collect/tech/daily_kline
  │ Body: { params: { symbols, start_date, end_date } }
  ▼
Route: collect_handler.trigger_collect
  │ - 找 service factory（注册表）
  │ - factory() → 内部 Depends 注入 session/log_service/task_runner
  │ - svc.collect(params)
  ▼
Service: DailyKlineService.collect
  │ 1. log_service.create_pending(...)   ← 落库
  │ 2. task_runner.dispatch(...)        ← 派发
  │ 3. dispatch 失败 → log_service.mark_failed(...)
  │ 4. return { log_id, status: "pending" }
  ▼
Route: return R.ok({ log_id, status, message })
  ▼
前端：拿到 log_id → 加入轮询列表
```

### 6.2 后台执行（TaskRunner + Service）

```
TaskRunner._run (asyncio.Task)
  │ 独立 session: get_db_context()
  │ 注入 CollectLogService（同一 session）
  │
  │ svc = DailyKlineService(session, log_service, task_runner)
  │ async for batch in svc._run_collect(params, session, log_id, facet, kind):
  │     pass
  ▼
Service: _run_collect
  │ - 执行业务逻辑
  │ - yield { saved, fail, total }
  ▼
TaskRunner._run 内部：
  │ 1. await log_service.mark_running(...)    ← 开始
  │ 2. for batch in _run_collect(...):
  │       await log_service.update_progress(...) ← 实时
  │ 3. await log_service.mark_finished(...)   ← 终态
  │ 4. except: await log_service.mark_failed(...) ← 异常
  ▼
TaskRunner: task.done() → 从 registry 清理
```

### 6.3 GET 查询日志

```
前端
  │ GET /collect/logs/daily_kline?limit=10
  ▼
Route: log_handler.list_logs
  │ - 注入 CollectLogService
  │ - await log_service.list_logs(...)
  ▼
Service: CollectLogService.list_logs
  │ 1. repo.list_recent()    ← DB
  │ 2. 合并 Redis 实时进度（pending/running）
  │ 3. return items
  ▼
Route: return R.ok({ items })
```

### 6.4 事务边界

| 事务 | 触发点 | session 来源 | 内容 |
|---|---|---|---|
| 事务 A | Route | Depends(get_db) | `log_service.create_pending` 内部 `repo.create` |
| 事务 B | 后台 | get_db_context() | `log_service.mark_running` 内部 `repo.update_status` |
| 事务 C | 后台 | get_db_context() | `log_service.mark_finished` 内部 `repo.finish` |
| 事务 D | Route | Depends(get_db) | `log_service.list_logs` 内部 `repo.list_recent` |
| Redis 写 | 同步 | 全局单例 | pending 初始化 / 实时进度 / 终态 |

---

## 七、文件清单

### 7.1 新增文件

| 文件 | 职责 |
|---|---|
| `interface/manage/log_handler.py` | GET /collect/logs/* 端点 |
| `application/service/manage/collect_log_service.py` | 日志业务编排 |
| `infrastructure/adapter/background/__init__.py` | 导出 |
| `infrastructure/adapter/background/collect_task_runner.py` | 后台任务派发器 |
| `infrastructure/di/log_service.py` | CollectLogService DI 工厂 |
| `infrastructure/di/collect_service_factory.py` | 28 个 service 工厂注册表 |
| **合计** | **~700 行** |

### 7.2 修改文件

| 文件 | 改动 |
|---|---|
| `interface/manage/collect_handler.py` | 272 → 35 行（Route 层零业务） |
| `interface/manage/router.py` | 聚合 3 个 handler |
| `application/service/manage/__init__.py` | 导出 CollectLogService |
| `application/service/tech/daily_kline_service.py` | collect() + _run_collect() 拆分 |
| `infrastructure/di/collect_service.py` | 28 个 factory 加 log_service/task_runner 注入 |
| `infrastructure/aop/collect_logger.py` | **删除**（无 AOP） |
| `infrastructure/persistence/repositories/collect_log_repository.py` | 不动 |
| `infrastructure/persistence/models/collect_log.py` | 不动 |

### 7.3 数据库

- 表名 `collect_logs` 保持不变
- 表结构保持不变

---

## 八、迁移步骤

### Step 1：基础设施（1 PR）

1. 新增 `infrastructure/adapter/background/collect_task_runner.py`
2. 新增 `infrastructure/di/log_service.py`
3. 新增 `infrastructure/di/collect_service_factory.py`
4. **不动其他文件**

跑通：`get_collect_task_runner()` 能拿到单例。

### Step 2：日志子系统（1 PR）

1. 新增 `application/service/manage/collect_log_service.py`
2. 更新 `application/service/manage/__init__.py`
3. 新增 `interface/manage/log_handler.py`
4. 改造 `interface/manage/router.py`
5. 改造 `interface/manage/collect_handler.py`（Route 层零业务）

### Step 3：daily_kline 改造（1 PR）

1. 改造 `application/service/tech/daily_kline_service.py`
   - `collect()`：编排入口
   - `_run_collect()`：执行入口
2. 跑通：手动触发采集，看日志表 + Redis

### Step 4：27 service 接入（多个 PR）

按 `tech → capital → fundamental → news` 顺序，每批 5 个。

### Step 5：旧路由退役（1 PR）

删除 `interface/route/{facet}/__init__.py` 的 `@router.post(...)` 装饰。

### Step 6：DTO 整理（Phase 3）

重写 DTO，同步前端。

---

## 九、27 service 改造模板

**改造前**（v1）：

```python
class AdjFactorService:
    name = "adj_factor"
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 5

    async def collect(self, params: dict) -> CollectResult:
        sem = asyncio.Semaphore(self.CONCURRENCY)
        results = await asyncio.gather(*[one(s) for s in symbols], return_exceptions=True)
        return CollectResult(...)
```

**改造后**（v2）：

```python
class AdjFactorService:
    META = ServiceMeta(name="adj_factor", facet="tech", ...)

    def __init__(self, session, log_service, task_runner, ...):
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        ...

    async def collect(self, params: dict) -> dict:
        """编排入口"""
        log_id = await self._log_service.create_pending(
            service_name=self.META.name,
            facet=self.META.facet,
            kind=self.META.kind.value,
            params=params,
        )
        try:
            self._task_runner.dispatch(
                log_id=log_id,
                service_name=self.META.name,
                service_class=type(self),
                facet=self.META.facet,
                kind=self.META.kind.value,
                params=params,
            )
        except Exception as e:
            await self._log_service.mark_failed(self.META.name, log_id, str(e))
            raise
        return {"log_id": log_id, "status": "pending"}

    async def _run_collect(self, params, session, log_id, *, facet, kind) -> AsyncGenerator:
        """执行入口"""
        symbols = params.get("symbols") or []
        sem = asyncio.Semaphore(self.META.concurrency)
        tasks = [asyncio.create_task(one(s)) for s in symbols]
        for coro in asyncio.as_completed(tasks):
            yield await coro
```

---

## 十、相关文档

| 文档 | 关系 |
|---|---|
| `01-采集日志进度优化方案.md` | v1（handler 创建日志，本轮返工） |
| `02-采集日志进度优化落地总结.md` | v1 落地 |
| `../../config/depend管理.md` | 核心规则 |
| `../../contexts/user/infrastructure/adapter/background/operation_dispatcher.py` | Runner 范式参考 |

---

## 十一、评审检查清单

- [ ] **日志独立子系统**：`log_handler.py` / `collect_log_service.py` / `collect_log_repository.py` 三层闭环
- [ ] **TaskRunner 独立基础设施**：`infra/adapter/background/collect_task_runner.py` 注入日志服务
- [ ] **无 AOP**：删除 `@collect_logger`，日志全手动调
- [ ] **collect() / _run_collect() 分工**：编排入口 + 执行入口
- [ ] **同事务 = 业务语义**：create_pending + dispatch 串行，失败 mark_failed
- [ ] **Route 层零业务**：只调 `svc.collect()`，不持 session
- [ ] **工厂注册表**：`collect_service_factory.py` 解决 Route 层找 service 问题
- [ ] **路径兼容**：v1 URL 仍 work
- [ ] **日志表名不变**：`collect_logs` 保持
