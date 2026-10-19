# Phase 2 采集日志进度优化 - 完整落地总结文档

> 位置：`docs/backend-docs/dev/level2/step1采集模块优化/06采集日志进度优化/`
> 上游文档：
> - `01-采集日志进度优化方案.md`（v1）
> - `02-采集日志进度优化落地总结.md`（v1 已落地）
> - `03-Phase2日志业务下沉重构方案.md`（本轮方案）
> 更新日期：2026-10-19
> 状态：**待评审（暂不修改代码）**

---

## 一、总体概述

### 1.1 核心目标

将采集日志业务从 handler 层下沉到 service 层，实现：
- **日志子系统独立闭环**：route / service / persistence 三层分离
- **采集任务派发独立基础设施**：TaskRunner 统一管理后台任务
- **日志操作全手动调用**：无 AOP 装饰器，代码更清晰

### 1.2 架构图

```
┌──────────────────────────────────────────────────────────────────┐
│                           前端                                     │
│   触发采集 → 轮询进度 → 展示结果                                   │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Route 层（interface）                          │
│  ┌────────────────────┐  ┌────────────────────┐                   │
│  │ collect_handler.py │  │   log_handler.py  │                   │
│  │  POST 触发采集     │  │  GET 查询日志     │                   │
│  └────────────────────┘  └────────────────────┘                   │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Service 层（application）                        │
│  ┌──────────────────────────────┐  ┌────────────────────────────┐ │
│  │  采集接口 Service             │  │  CollectLogService        │ │
│  │  DailyKlineService 等        │  │  日志业务编排              │ │
│  │  - collect() 编排入口         │  │  - create_pending()       │ │
│  │  - _run_collect() 执行入口   │  │  - mark_running()        │ │
│  └──────────────────────────────┘  │  - update_progress()      │ │
│                                    │  - mark_finished()       │ │
│                                    │  - mark_failed()         │ │
│                                    │  - list_logs() / get_log│ │
│                                    └────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────────────┐  ┌─────────────────────────────┐
│     Infra 层（TaskRunner）       │  │  Infra 层（Persistence）   │
│  infra/adapter/background/      │  │  collect_log_repository.py  │
│  collect_task_runner.py          │  │  collect_log.py (ORM)     │
│  - dispatch() 派发任务          │  └─────────────────────────────┘
│  - 独立 session                 │
│  - task registry                │
└─────────────────────────────────┘
```

### 1.3 关键设计决策

| 决策 | 方案 | 原因 |
|---|---|---|
| 日志独立子系统 | route / service / persistence 三层分离 | 符合 DDD 分层架构 |
| TaskRunner 独立基础设施 | `infra/adapter/background/` | 与 user.contexts.operation_dispatcher 对齐 |
| 无 AOP 装饰器 | 日志全手动调用 | 代码更清晰，无隐晦调用链 |
| collect() 拆分 | 编排入口 + 执行入口 | HTTP 入口不阻塞，立即返回 |
| 同事务 = 业务语义 | 先 create_log，再 dispatch，失败回滚 | DB 事务无法包含 asyncio.create_task |

---

## 二、数据库设计（SQLAlchemy ORM）

### 2.1 ORM 模型

**文件**：`backend/src/contexts/collect/infrastructure/persistence/models/collect_log.py`

```python
"""CollectLog ORM — 采集日志表

对应表: collect_logs
设计说明：
    - 主键 id 使用 UUID（log_id），由 CollectLogService.create_pending() 生成
    - status 状态机: pending → running → success/partial_fail/failed/skipped
    - updated_at 由数据库触发器自动维护
    - v2：表结构不变，与 v1 兼容
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import Base


class CollectLogDB(Base):
    """采集日志 ORM"""
    __tablename__ = "collect_logs"
    
    # 主键
    id: Mapped[str] = mapped_column(UUID(), primary_key=True)  # log_id，UUID
    
    # 采集服务标识
    service_name: Mapped[str] = mapped_column(String(128), nullable=False)
    facet: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    
    # 触发信息
    trigger_source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    trigger_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # 采集参数
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    # 状态机
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    
    # 数量统计
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # 元信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    
    __table_args__ = (
        Index("idx_collect_logs_service_name", "service_name"),
        Index("idx_collect_logs_status", "status"),
        Index("idx_collect_logs_started_at", started_at.desc()),
        Index("idx_collect_logs_service_time", "service_name", started_at.desc()),
    )
    
    def __repr__(self) -> str:
        return f"<CollectLog {self.id} {self.service_name} {self.status}>"


__all__ = ["CollectLogDB"]
```

### 2.2 表结构（SQL 等效）

```sql
CREATE TABLE public.collect_logs (
    id              UUID PRIMARY KEY,
    service_name    VARCHAR(128) NOT NULL,
    facet           VARCHAR(64) NOT NULL,
    kind            VARCHAR(32) NOT NULL,
    trigger_source  VARCHAR(32) NOT NULL DEFAULT 'manual',
    trigger_user    VARCHAR(64),
    params          JSONB NOT NULL DEFAULT '{}',
    status          VARCHAR(32) NOT NULL DEFAULT 'pending',
    total_count     INTEGER DEFAULT 0,
    saved_count     INTEGER DEFAULT 0,
    fail_count      INTEGER DEFAULT 0,
    progress        INTEGER DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_collect_logs_service_name ON public.collect_logs(service_name);
CREATE INDEX idx_collect_logs_status ON public.collect_logs(status);
CREATE INDEX idx_collect_logs_started_at ON public.collect_logs(started_at DESC);
CREATE INDEX idx_collect_logs_service_time ON public.collect_logs(service_name, started_at DESC);
```

### 2.3 Redis Key 设计

```
Key:   collect:log:{service_name}:{log_id}
Type:  Hash
TTL:   3600 秒（1小时）

Field 设计：
  - status: pending/running/success/partial_fail/failed
  - progress: 0-100
  - saved_count: 已入库记录数
  - fail_count: 失败记录数
  - total_count: 预估总量
  - error: 错误信息
  - started_at: ISO 格式时间
  - updated_at: ISO 格式时间
```

---

## 三、后端设计

### 3.1 新增文件清单

| 文件 | 行数 | 职责 |
|---|---|---|
| `interface/manage/log_handler.py` | ~70 | GET /collect/logs/* 端点 |
| `application/service/manage/collect_log_service.py` | ~280 | 日志业务编排 |
| `infrastructure/adapter/background/__init__.py` | ~10 | 导出 |
| `infrastructure/adapter/background/collect_task_runner.py` | ~200 | 后台任务派发器 |
| `infrastructure/di/log_service.py` | ~30 | CollectLogService DI 工厂 |
| `infrastructure/di/collect_service_factory.py` | ~300 | 28 个 service 工厂注册表 |
| **合计** | **~890 行** | |

### 3.2 修改文件清单

| 文件 | 改动 |
|---|---|
| `interface/manage/collect_handler.py` | 272 → 40 行（Route 层零业务） |
| `interface/manage/router.py` | 聚合 3 个 handler（log_handler 在前） |
| `application/service/manage/__init__.py` | 导出 CollectLogService |
| `application/service/tech/daily_kline_service.py` | collect() + _run_collect() 拆分 |
| `infrastructure/aop/collect_logger.py` | **删除**（无 AOP） |
| `infrastructure/di/collect_service.py` | 28 个 factory 加 log_service/task_runner 注入 |
| `infrastructure/persistence/repositories/collect_log_repository.py` | 不动 |
| `infrastructure/persistence/models/collect_log.py` | 不动 |

### 3.3 核心代码

#### 3.3.1 CollectLogService（日志业务编排）

**文件**：`backend/src/contexts/collect/application/service/manage/collect_log_service.py`

```python
"""CollectLogService — 采集日志业务编排

日志子系统唯一业务入口：
    - 拥有自己的 route（log_handler.py）
    - 拥有自己的 service（本文件）
    - 拥有自己的 repo（collect_log_repository.py）

被谁调用：
    1. log_handler.py  → list_logs / get_log
    2. 采集接口 service collect() → create_pending + mark_failed
    3. TaskRunner._run() → mark_running / update_progress / mark_finished / mark_failed
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

REDIS_KEY_PREFIX = "collect:log"
REDIS_TTL = 3600


class CollectLogService:
    """采集日志业务服务"""

    def __init__(
        self,
        session: AsyncSession,
        redis_client,  # aioredis.Redis
    ) -> None:
        self._session = session
        self._redis = redis_client
        self._repo = CollectLogRepository(session)

    async def create_pending(
        self,
        service_name: str,
        facet: str,
        kind: str,
        params: dict,
        trigger_source: str = "manual",
        trigger_user: str | None = None,
    ) -> str:
        """创建采集日志（pending 状态）"""
        log_id = str(uuid.uuid4())

        await self._repo.create(
            id=log_id,
            service_name=service_name,
            facet=facet,
            kind=kind,
            trigger_source=trigger_source,
            trigger_user=trigger_user,
            params=params,
        )

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
        """状态：pending → running"""
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
        """实时进度：只写 Redis"""
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
        status: str,
        saved_count: int,
        fail_count: int,
    ) -> None:
        """终态：success / partial_fail"""
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
        """异常：failed"""
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
        """查询单条日志"""
        log = await self._repo.get_by_id(log_id)
        if log is None:
            return None
        await self._merge_redis_progress(service_name, log)
        return log

    async def _merge_redis_progress(
        self,
        service_name: str,
        log: dict[str, Any],
    ) -> None:
        """DB 数据 + Redis 实时进度合并"""
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

#### 3.3.2 CollectTaskRunner（后台任务派发器）

**文件**：`backend/src/contexts/collect/infrastructure/adapter/background/collect_task_runner.py`

```python
"""CollectTaskRunner — 后台采集任务派发器

设计要点：
    - 不持有父请求的 session！后台任务必须自己创建独立 session
    - 维护进程内 task registry（log_id → asyncio.Task）
    - 派发即返回（fire-and-forget）
    - 单例模式（lifespan 内常驻）
    - 注入 CollectLogService，手动调日志服务

参考：user.contexts.infrastructure.adapter.background.operation_dispatcher
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)


class CollectTaskRunner:
    """采集后台任务派发器（单例）"""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}

    def dispatch(
        self,
        log_id: str,
        service_name: str,
        service_class: type,
        facet: str,
        kind: str,
        params: dict,
    ) -> None:
        """派发后台任务（立即返回）"""
        task = asyncio.create_task(
            self._run(log_id, service_name, service_class, facet, kind, params)
        )
        self._tasks[log_id] = task
        logger.info("派发采集任务: log_id=%s, service=%s/%s", log_id, facet, service_name)
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
        """后台任务执行入口"""
        from shared.infrastructure.di.db_session import get_db_context
        from shared.infrastructure.di.redis_session import get_redis
        from contexts.collect.application.service.manage import CollectLogService

        async with get_db_context() as session:
            redis = await get_redis()
            log_service = CollectLogService(session=session, redis_client=redis)

            try:
                svc = service_class(session=session)

                # 1. 标记 running
                await log_service.mark_running(service_name, log_id)

                # 2. 执行采集
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

                    progress = (
                        min(100, int((saved_total + fail_total) / total * 100))
                        if total > 0 else 0
                    )

                    # 3. 实时更新进度
                    await log_service.update_progress(
                        service_name=service_name,
                        log_id=log_id,
                        progress=progress,
                        saved_count=saved_total,
                        fail_count=fail_total,
                        total_count=total,
                    )

                # 4. 终态
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
                logger.exception("采集任务失败: log_id=%s, service=%s", log_id, service_name)
                await log_service.mark_failed(
                    service_name=service_name,
                    log_id=log_id,
                    error=str(e),
                    saved_count=saved_total,
                    fail_count=fail_total,
                )

    def is_running(self, log_id: str) -> bool:
        task = self._tasks.get(log_id)
        return task is not None and not task.done()

    async def cancel(self, log_id: str) -> bool:
        task = self._tasks.get(log_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True


_runner_instance: "CollectTaskRunner | None" = None


def get_collect_task_runner() -> "CollectTaskRunner":
    """获取全局 Runner 单例"""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = CollectTaskRunner()
    return _runner_instance


__all__ = ["CollectTaskRunner", "get_collect_task_runner"]
```

#### 3.3.3 日志查询端点

**文件**：`backend/src/contexts/collect/interface/manage/log_handler.py`

```python
"""log_handler — 采集日志查询端点

提供：
    GET /collect/logs/{service_name}            日志列表
    GET /collect/logs/{service_name}/{log_id}   单条日志详情
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from shared.interface import _response as R
from contexts.collect.application.service.manage import CollectLogService
from contexts.collect.infrastructure.di.log_service import get_collect_log_service

router = APIRouter(prefix="/collect/logs", tags=["采集-日志查询"])


@router.get("/{service_name}", summary="查询某 service 的最近采集日志")
async def list_logs(
    service_name: str,
    limit: int = 10,
    log_service: CollectLogService = Depends(get_collect_log_service),
) -> dict[str, Any]:
    items = await log_service.list_logs(service_name=service_name, limit=limit)
    return R.ok({"items": items})


@router.get("/{service_name}/{log_id}", summary="查询单条采集日志详情")
async def get_log(
    service_name: str,
    log_id: str,
    log_service: CollectLogService = Depends(get_collect_log_service),
) -> dict[str, Any]:
    log = await log_service.get_log(log_id=log_id, service_name=service_name)
    if log is None:
        raise HTTPException(status_code=404, detail=f"日志 {log_id!r} 不存在")
    return R.ok(log)


__all__ = ["router"]
```

#### 3.3.4 触发采集端点

**文件**：`backend/src/contexts/collect/interface/manage/collect_handler.py`

```python
"""collect_handler — 触发采集端点（Route 层零业务）

提供：
    POST /collect/{facet}/{service_name}
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from shared.interface import _response as R
from contexts.collect.infrastructure.di.collect_service_factory import get_service_by_name

router = APIRouter(prefix="/collect", tags=["采集-触发"])


@router.post("/{facet}/{service_name}", summary="触发采集")
async def trigger_collect(
    facet: str,
    service_name: str,
    body: dict,
) -> dict[str, Any]:
    """触发采集 - Route 层纯入口"""
    factory = get_service_by_name(service_name)
    if factory is None:
        raise HTTPException(404, f"service {service_name!r} 不存在")

    svc = await factory()
    result = await svc.collect(body.get("params", {}))

    return R.ok({
        **result,
        "service_name": service_name,
        "facet": facet,
        "message": "采集任务已创建，请通过 /collect/logs/{service_name} 轮询进度",
    })


__all__ = ["router"]
```

#### 3.3.5 Router 聚合

**文件**：`backend/src/contexts/collect/interface/manage/router.py`

```python
"""manage/router — 管理面所有 handler 的总装"""
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

#### 3.3.6 DailyKlineService 示例

**文件**：`backend/src/contexts/collect/application/service/tech/daily_kline_service.py`

```python
"""DailyKlineService — 日 K 线 service（v2）

v2 改造：
    - 注入 CollectLogService + CollectTaskRunner
    - collect()：编排入口（创建日志 + 派发任务）
    - _run_collect()：执行入口（实际采集，yield 进度）
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

    async def collect(self, params: dict) -> dict:
        """HTTP 触发入口：编排（不执行实际采集）"""
        log_id = await self._log_service.create_pending(
            service_name=self.META.name,
            facet=self.META.facet,
            kind=self.META.kind.value,
            params=params,
            trigger_source="manual",
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
            logger.exception(f"派发采集任务失败: {e}")
            await self._log_service.mark_failed(
                service_name=self.META.name,
                log_id=log_id,
                error=f"派发失败: {e}",
            )
            raise

        return {"log_id": log_id, "status": "pending"}

    async def _run_collect(
        self,
        params: dict,
        session: AsyncSession,
        log_id: str,
        *,
        facet: str = "",
        kind: str = "incremental",
    ) -> AsyncGenerator[dict, None]:
        """后台任务执行入口：实际采集"""
        symbols = params.get("symbols") or []
        start_date = params.get("start_date")
        end_date = params.get("end_date") or date.today().isoformat()

        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

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

        tasks = [asyncio.create_task(one(s)) for s in symbols]
        for coro in asyncio.as_completed(tasks):
            yield await coro

    async def _list_all_symbols(self) -> list[str]:
        return await list_all_a_symbols()

    async def _collect_one(self, symbol: str, start_date: date, end_date: date) -> int:
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

    async def get(
        self,
        symbol: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
    ) -> list[dict]:
        """实时查询日 K 线"""
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

#### 3.3.7 DI 工厂

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
    return CollectLogService(session=session, redis_client=redis)


__all__ = ["get_collect_log_service"]
```

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


async def get_daily_kline_service(
    session: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> "DailyKlineService":
    from contexts.collect.application.service.tech.daily_kline_service import DailyKlineService
    log_service = CollectLogService(session=session, redis_client=redis)
    task_runner = get_collect_task_runner()
    return DailyKlineService(session=session, log_service=log_service, task_runner=task_runner)


async def get_adj_factor_service(
    session: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> "AdjFactorService":
    from contexts.collect.application.service.tech.adj_factor_service import AdjFactorService
    log_service = CollectLogService(session=session, redis_client=redis)
    task_runner = get_collect_task_runner()
    return AdjFactorService(session=session, log_service=log_service, task_runner=task_runner)


# ... 其他 26 个 service 同理 ...


SERVICE_FACTORIES: dict[str, Callable[..., Awaitable[Any]]] = {
    "daily_kline": get_daily_kline_service,
    "adj_factor": get_adj_factor_service,
    # ... 其他 ...
}


def get_service_by_name(service_name: str) -> Callable[..., Awaitable[Any]] | None:
    return SERVICE_FACTORIES.get(service_name)


__all__ = [
    "SERVICE_FACTORIES",
    "get_service_by_name",
    "get_daily_kline_service",
    "get_adj_factor_service",
    # ... 其他 ...
]
```

---

## 四、前端设计

### 4.1 API 定义

**文件**：`frontend/src/views/collect-manage/api.ts`

前端代码基本不变，主要类型定义：

```typescript
/** 采集日志 */
export interface CollectLog {
  id: string
  service_name: string
  facet: string
  kind: 'incremental' | 'full_refresh' | 'realtime'
  trigger_source: 'manual' | 'script' | 'schedule'
  trigger_user: string | null
  params: Record<string, any>
  status: 'pending' | 'running' | 'success' | 'partial_fail' | 'failed' | 'skipped'
  total_count: number
  saved_count: number
  fail_count: number
  progress: number  // 0-100
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string | null
  updated_at: string | null
}

/** 触发采集响应 */
export interface CollectStartResponse {
  log_id: string
  status: string
  service_name: string
  facet: string
  message: string
}

/** 查询某 service 的最近采集日志 */
export const listCollectLogs = (serviceName: string, limit: number = 20) =>
  http.get<ApiResponse<{ items: CollectLog[] }>>(`/collect/logs/${serviceName}?limit=${limit}`).then(unwrap)

/** 查询单条采集日志详情 */
export const getCollectLog = (serviceName: string, logId: string) =>
  http.get<ApiResponse<CollectLog>>(`/collect/logs/${serviceName}/${logId}`).then(unwrap)

/** 手动触发一次 service（返回 log_id） */
export const runService = async (
  name: string,
  payload: { params: Record<string, any> } = { params: {} },
): Promise<CollectStartResponse> => {
  const path = buildPath(name, `/collect/_unknown/${name}`)
  return http.post<ApiResponse<CollectStartResponse>>(path, payload).then(unwrap)
}
```

### 4.2 轮询逻辑

**文件**：`frontend/src/views/collect-manage/components/CollectTaskPane.vue`

核心逻辑不变，主要流程：

```typescript
const POLL_INTERVAL = 2000  // 轮询间隔 2 秒

/** 触发采集 */
async function runServiceAndWait(serviceName: string, payload: { params: any }) {
  const res = await runService(serviceName, payload)
  activeLogId.value = res.log_id  // 开始轮询
  await loadLogs()
  startPolling()
}

/** 轮询进度 */
async function pollProgress() {
  if (!polling.value || !props.serviceName) return

  const res = await listCollectLogs(props.serviceName, 50)
  const latestLogs = res.items || []

  // 更新本地日志列表
  for (const log of latestLogs) {
    const idx = logs.value.findIndex(l => l.id === log.id)
    if (idx >= 0) {
      logs.value[idx] = log
    } else {
      logs.value.unshift(log)
      if (logs.value.length > 20) logs.value.pop()
    }
  }

  // 找到当前 activeLogId 对应的最新状态
  const currentLog = latestLogs.find(l => l.id === activeLogId.value)

  // 终态停止轮询
  if (currentLog && ['success', 'partial_fail', 'failed', 'skipped'].includes(currentLog.status)) {
    stopPolling()
    // 提示用户
    if (currentLog.status === 'success') {
      ElMessage.success(`采集完成：已保存 ${currentLog.saved_count} 条`)
    } else if (currentLog.status === 'partial_fail') {
      ElMessage.warning(`采集完成：成功 ${currentLog.saved_count} 条，失败 ${currentLog.fail_count} 条`)
    } else if (currentLog.status === 'failed') {
      ElMessage.error(`采集失败：${currentLog.error_message || '未知错误'}`)
    }
  }

  // 继续轮询
  if (polling.value) {
    pollTimer = setTimeout(pollProgress, POLL_INTERVAL)
  }
}
```

### 4.3 状态显示

**文件**：`frontend/src/views/collect-manage/components/CollectProgressCard.vue`

进度卡片展示：
- 进度条（0-100%）
- 状态徽标（pending/running/success/partial_fail/failed）
- 已保存数 / 失败数
- 错误信息（failed 时显示）

**文件**：`frontend/src/views/collect-manage/components/CollectLogList.vue`

日志列表展示：
- 开始时间
- 状态徽标
- 进度条
- 保存/失败数
- 错误信息

---

## 五、API 文档

### 5.1 接口列表

| Method | Path | 说明 |
|---|---|---|
| `POST` | `/collect/{facet}/{service_name}` | 触发采集，返回 log_id |
| `GET` | `/collect/logs/{service_name}` | 查询日志列表（合并 Redis 实时进度） |
| `GET` | `/collect/logs/{service_name}/{log_id}` | 查询单条日志详情 |
| `GET` | `/collect/catalog` | catalog（不变） |
| `GET` | `/collect/query/{name}` | 实时查询（不变） |

### 5.2 触发采集

**请求**：
```http
POST /collect/tech/daily_kline
Content-Type: application/json

{
  "params": {
    "symbols": [],
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }
}
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "log_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending",
    "service_name": "daily_kline",
    "facet": "tech",
    "message": "采集任务已创建，请通过 /collect/logs/{service_name} 轮询进度"
  }
}
```

### 5.3 查询日志列表

**请求**：
```http
GET /collect/logs/daily_kline?limit=10
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "service_name": "daily_kline",
        "facet": "tech",
        "kind": "incremental",
        "trigger_source": "manual",
        "params": { "symbols": [], "start_date": "2024-01-01", "end_date": "2024-12-31" },
        "status": "running",
        "total_count": 5000,
        "saved_count": 2341,
        "fail_count": 12,
        "progress": 47,
        "error_message": null,
        "started_at": "2024-12-01T10:00:00Z",
        "finished_at": null
      }
    ]
  }
}
```

### 5.4 查询单条日志

**请求**：
```http
GET /collect/logs/daily_kline/550e8400-e29b-41d4-a716-446655440000
```

**响应**：同上，单条数据。

---

## 六、完整调用链

### 6.1 触发采集

```
前端
  │ POST /collect/tech/daily_kline
  │ Body: { params: { symbols, start_date, end_date } }
  ▼
Route: collect_handler.trigger_collect
  │ - 找 service factory
  │ - factory() → 内部 Depends 注入 session/log_service/task_runner
  │ - svc.collect(params)
  ▼
Service: DailyKlineService.collect
  │ 1. log_service.create_pending(...)   ← 落库 + Redis
  │ 2. task_runner.dispatch(...)        ← 派发
  │ 3. dispatch 失败 → log_service.mark_failed(...)
  │ 4. return { log_id, status: "pending" }
  ▼
Route: return R.ok({ log_id, status, message })
  ▼
前端：拿到 log_id → 加入轮询列表
```

### 6.2 后台执行

```
TaskRunner._run (asyncio.Task)
  │ 独立 session: get_db_context()
  │ 注入 CollectLogService
  │
  │ svc = DailyKlineService(session, log_service, task_runner)
  │ async for batch in svc._run_collect(...):
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

### 6.3 查询日志

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

## 七、迁移步骤

### Step 1：基础设施（1 PR）

1. 新增 `infrastructure/adapter/background/collect_task_runner.py`
2. 新增 `infrastructure/di/log_service.py`
3. 新增 `infrastructure/di/collect_service_factory.py`
4. **不动其他文件**

### Step 2：日志子系统（1 PR）

1. 新增 `application/service/manage/collect_log_service.py`
2. 更新 `application/service/manage/__init__.py`
3. 新增 `interface/manage/log_handler.py`
4. 改造 `interface/manage/router.py`
5. 改造 `interface/manage/collect_handler.py`

### Step 3：daily_kline 改造（1 PR）

1. 改造 `application/service/tech/daily_kline_service.py`
2. 跑通：手动触发采集，看日志表 + Redis

### Step 4：27 service 接入（多个 PR）

按 `tech → capital → fundamental → news` 顺序，每批 5 个。

### Step 5：旧路由退役（1 PR）

删除 `interface/route/{facet}/__init__.py` 的 `@router.post(...)` 装饰。

### Step 6：DTO 整理（Phase 3）

重写 DTO，同步前端。

---

## 八、评审检查清单

- [ ] **日志独立子系统**：`log_handler.py` / `collect_log_service.py` / `collect_log_repository.py` 三层闭环
- [ ] **TaskRunner 独立基础设施**：`infra/adapter/background/collect_task_runner.py` 注入日志服务
- [ ] **无 AOP**：删除 `@collect_logger`，日志全手动调
- [ ] **collect() / _run_collect() 分工**：编排入口 + 执行入口
- [ ] **同事务 = 业务语义**：create_pending + dispatch 串行，失败 mark_failed
- [ ] **Route 层零业务**：只调 `svc.collect()`，不持 session
- [ ] **工厂注册表**：`collect_service_factory.py` 解决 Route 层找 service 问题
- [ ] **路径兼容**：v1 URL 仍 work
- [ ] **日志表名不变**：`collect_logs` 保持
- [ ] **前端 0 改动**：API 路径不变，前端只改类型定义

---

## 九、相关文档

| 文档 | 关系 |
|---|---|
| `01-采集日志进度优化方案.md` | v1（handler 创建日志，本轮返工） |
| `02-采集日志进度优化落地总结.md` | v1 落地 |
| `03-Phase2日志业务下沉重构方案.md` | 本轮详细方案 |
| `../../config/depend管理.md` | 核心规则 |
| `../../contexts/user/infrastructure/adapter/background/operation_dispatcher.py` | Runner 范式参考 |

---

## 十、风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| TaskRunner 重启后丢失任务 | 日志卡在 running | 重启时清理 running 状态为 failed |
| 派发成功但 service 实例化失败 | 日志卡在 running | TaskRunner 内部 try/except 调 mark_failed |
| Redis 写入失败 | 日志表正常、Redis 缺失实时进度 | 降级：Redis 失败时回退到只查 DB |
| 27 service 改造引入 bug | 进度数据不准确 | 每批 5 个改完跑 smoke test |
| 旧路由切换时部分 service 未接入 | 返回 404 | 明确提示 |
