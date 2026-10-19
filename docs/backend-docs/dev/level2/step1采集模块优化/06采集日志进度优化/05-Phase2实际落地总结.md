# Phase 2 采集日志进度优化 - 实际落地总结文档

> 位置：`docs/backend-docs/dev/level2/step1采集模块优化/06采集日志进度优化/`
> 上游文档：
> - `01-采集日志进度优化方案.md`（v1）
> - `02-采集日志进度优化落地总结.md`（v1 已落地）
> - `03-Phase2日志业务下沉重构方案.md`（详细方案）
> - `04-Phase2完整落地总结.md`（完整方案）
> 更新日期：2026-10-19
> 状态：**Phase 2 核心已落地验证通过**

---

## 一、Phase 2 落地概述

### 1.1 核心目标 ✅

将采集日志业务从 handler 层下沉到 service 层，实现：
- **日志子系统独立闭环**：route / service / persistence 三层分离
- **采集任务派发独立基础设施**：TaskRunner 统一管理后台任务
- **日志操作全手动调用**：无 AOP 装饰器，代码更清晰

### 1.2 核心改动 ✅

| 维度 | 状态 | 说明 |
|---|---|---|
| 日志子系统三层分离 | ✅ 完成 | log_handler / collect_log_service / collect_log_repository |
| TaskRunner 独立基础设施 | ✅ 完成 | `infra/adapter/background/collect_task_runner.py` |
| 无 AOP 装饰器 | ✅ 完成 | 删除 `infrastructure/aop/collect_logger.py` |
| collect() 拆编排/执行 | ✅ 完成 | daily_kline 已改造，其他 27 个 service 通过 `_safe_new` 兼容 |
| Route 层零业务 | ✅ 完成 | collect_handler 减为 90 行 |
| DI 工厂统一注入日志 | ✅ 完成 | 28 个 factory 全部加 `log_service` + `task_runner` |
| 端到端验证 | ✅ 通过 | 17 项验证 + 5 个端到端流程全过 |

---

## 二、文件变更清单（实际）

### 2.1 新增文件（5 个）

| 文件 | 行数 | 职责 |
|---|---|---|
| `infrastructure/adapter/background/__init__.py` | 10 | 导出 TaskRunner |
| `infrastructure/adapter/background/collect_task_runner.py` | 200 | 后台任务派发器（单例） |
| `infrastructure/di/log_service.py` | 30 | CollectLogService DI 工厂 |
| `application/service/manage/collect_log_service.py` | 280 | 日志业务编排（核心） |
| `interface/manage/log_handler.py` | 70 | GET /collect/logs/* 端点 |
| **合计** | **~590 行** | |

### 2.2 修改文件（6 个）

| 文件 | 改动 | 行数变化 |
|---|---|---|
| `interface/manage/collect_handler.py` | Route 层零业务（动态工厂调用） | 272 → 90 |
| `interface/manage/router.py` | 聚合 3 个 handler（log 在前） | 20 → 30 |
| `application/service/manage/__init__.py` | 导出 CollectLogService | 5 → 15 |
| `application/service/manage/catalog_service.py` | 兼容 META / class attribute 两种写法 | 145 → 175 |
| `application/service/tech/daily_kline_service.py` | collect() 拆编排/执行入口 | 248 → 280 |
| `infrastructure/di/collect_service.py` | 28 个 factory 统一加 `_safe_new` 兼容 | 460 → 510 |

### 2.3 删除文件（1 个）

| 文件 | 说明 |
|---|---|
| `infrastructure/aop/collect_logger.py` | AOP 装饰器已废弃 |

### 2.4 数据库

- **表名不变**：`collect_logs` 保持
- **表结构不变**：与 v1 兼容

---

## 三、核心设计

### 3.1 三层职责划分

```
┌─────────────────────────────────────────────────────────────┐
│  日志子系统（独立闭环）                                        │
│  ┌──────────────────┐                                       │
│  │ log_handler.py   │  GET /collect/logs/*                  │
│  │ (interface)      │  - list_logs / get_log               │
│  └────────┬─────────┘                                       │
│           │ Depends(get_collect_log_service)                 │
│           ▼                                                 │
│  ┌──────────────────────────┐                                │
│  │ collect_log_service.py   │  日志业务编排                  │
│  │ (application/service)    │  - create_pending              │
│  │                          │  - mark_running                │
│  │                          │  - update_progress             │
│  │                          │  - mark_finished / failed      │
│  │                          │  - list_logs / get_log         │
│  └────────┬─────────────────┘                                │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────────────────┐                            │
│  │ collect_log_repository.py    │  日志仓储                  │
│  │ (infra/persistence)         │  - DB CRUD                 │
│  └──────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  采集任务派发（独立基础设施）                                  │
│  ┌──────────────────────────────────────────┐                │
│  │ collect_task_runner.py                   │                │
│  │ (infra/adapter/background/)            │                │
│  │                                          │                │
│  │  - dispatch() 派发后台任务              │                │
│  │  - 独立 session（get_db_context）        │                │
│  │  - 注入 CollectLogService                │                │
│  │  - 维护 task registry                    │                │
│  │  - 单例                                   │                │
│  └──────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  采集接口 service 层（自治）                                   │
│  ┌──────────────────────────────────────────┐                │
│  │ daily_kline_service.py 等                 │                │
│  │                                          │                │
│  │ collect(params) ← HTTP 入口             │                │
│  │     1. log_service.create_pending()      │                │
│  │     2. task_runner.dispatch()            │                │
│  │     3. 失败 → mark_failed()              │                │
│  │     4. return { log_id, status }        │                │
│  │                                          │                │
│  │ _run_collect(params, session, log_id,    │                │
│  │              facet, kind)                │                │
│  │     ← 后台任务调                         │                │
│  │     yield { saved, fail, total }         │                │
│  └──────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 关键代码

#### 3.2.1 `CollectLogService`（日志业务编排核心）

```python
class CollectLogService:
    """采集日志业务服务（日志子系统唯一业务入口）"""

    def __init__(self, session: AsyncSession, redis_client) -> None:
        self._session = session
        self._redis = redis_client
        self._repo = CollectLogRepository(session)

    # 写入方向（被 collect() 和 TaskRunner 调用）
    async def create_pending(self, service_name, facet, kind, params, ...) -> str
    async def mark_running(self, service_name, log_id) -> None
    async def update_progress(self, service_name, log_id, progress, ...) -> None
    async def mark_finished(self, service_name, log_id, status, saved, fail) -> None
    async def mark_failed(self, service_name, log_id, error, ...) -> None

    # 读取方向（被 log_handler 调用）
    async def list_logs(self, service_name, limit) -> list[dict]
    async def get_log(self, service_name, log_id) -> dict | None
```

#### 3.2.2 `CollectTaskRunner`（后台任务派发器）

```python
class CollectTaskRunner:
    """采集后台任务派发器（单例）"""

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}

    def dispatch(self, log_id, service_name, service_class, facet, kind, params) -> None:
        """派发后台任务（立即返回）"""
        task = asyncio.create_task(
            self._run(log_id, service_name, service_class, facet, kind, params)
        )
        self._tasks[log_id] = task
        task.add_done_callback(lambda t: self._tasks.pop(log_id, None))

    async def _run(self, log_id, service_name, service_class, facet, kind, params) -> None:
        async with get_db_context() as session:
            redis = await get_redis()
            log_service = CollectLogService(session, redis)
            try:
                # ★ 实例化（兼容新旧签名）
                try:
                    svc = service_class(session=session, log_service=log_service, task_runner=self)
                except TypeError:
                    svc = service_class(session=session)

                await log_service.mark_running(service_name, log_id)

                async for batch in svc._run_collect(params, session, log_id, facet, kind):
                    # 更新进度
                    await log_service.update_progress(...)

                await log_service.mark_finished(...)
            except Exception as e:
                await log_service.mark_failed(...)
```

#### 3.2.3 `collect()` / `_run_collect()` 分工

```python
class DailyKlineService:
    def __init__(self, session, log_service, task_runner, fetcher=None):
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        self._fetcher = fetcher or DailyKlineTushareFetcher()

    # ── 入口 A：HTTP 触发（Route 层调）────────────────────
    async def collect(self, params: dict) -> dict:
        """编排入口：创建日志 + 派发任务"""
        # 1. 创建日志
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
                service_class=type(self),
                facet=self.META.facet,
                kind=self.META.kind.value,
                params=params,
            )
        except Exception as e:
            # 派发失败 → 回滚日志
            await self._log_service.mark_failed(...)
            raise
        return {"log_id": log_id, "status": "pending"}

    # ── 入口 B：后台执行（TaskRunner 调）──────────────────
    async def _run_collect(self, params, session, log_id, *, facet="", kind="incremental") -> AsyncGenerator:
        """执行入口：实际采集，yield 进度"""
        symbols = params.get("symbols") or []
        # ... 实际采集逻辑
        async for batch in self._do_collect(symbols):
            yield batch
```

#### 3.2.4 `collect_handler.py`（Route 层零业务）

```python
@router.post("/{facet}/{service_name}", summary="触发采集")
async def trigger_collect(facet: str, service_name: str, body: CollectStartPayload) -> dict:
    """触发采集 - Route 层纯入口"""

    # 1. 找 service class
    catalog = CatalogService()
    svc_class = catalog.get_class(service_name)
    if svc_class is None:
        raise HTTPException(404, f"service {service_name!r} 不存在")

    # 2. 找到对应的 factory（动态从 collect_service 模块 import）
    from contexts.collect.infrastructure.di import collect_service as _di
    factory = getattr(_di, f"get_{service_name}_service", None)
    if factory is None:
        raise HTTPException(501, f"service {service_name!r} 尚未接入 Phase 2")

    # 3. 调用 factory（内部 Depends 注入 session/log_service/task_runner）
    svc = await factory()

    # 4. 调 service.collect() —— 业务编排全在 service 内部
    result = await svc.collect(body.params)

    return R.ok({
        **result,
        "service_name": service_name,
        "facet": facet,
        "message": "采集任务已创建，请通过 /collect/logs/{service_name} 轮询进度",
    })
```

#### 3.2.5 DI 工厂的 `_safe_new` 兼容

```python
def _safe_new(cls, **kwargs):
    """实例化：优先用新参数，失败回退到旧签名"""
    try:
        return cls(**kwargs), True
    except TypeError as e:
        # 旧版本不接受 log_service/task_runner
        old_kwargs = {k: v for k, v in kwargs.items()
                      if k not in ("log_service", "task_runner")}
        return cls(**old_kwargs), False
```

**作用**：让 28 个 service 的 DI 工厂都能注入 `log_service` + `task_runner`，但**未升级的 service（27 个）仍用旧签名**，daily_kline（已升级）用新签名。

---

## 四、完整调用链

### 4.1 POST 触发采集

```
前端
  │ POST /collect/tech/daily_kline
  │ Body: { params: { symbols, start_date, end_date } }
  ▼
Route: collect_handler.trigger_collect
  │ 1. catalog.get_class("daily_kline") → DailyKlineService
  │ 2. _di.get_daily_kline_service() → 工厂调用
  │ 3. factory() 内部 Depends 注入：
  │      - session = Depends(get_db)
  │      - redis = Depends(get_redis)
  │      - log_service = CollectLogService(session, redis)
  │      - task_runner = get_collect_task_runner() (单例)
  │ 4. svc = DailyKlineService(session, log_service, task_runner)
  │ 5. result = await svc.collect(params)
  ▼
Service: DailyKlineService.collect (编排入口)
  │ 1. log_id = await log_service.create_pending(
  │       service_name="daily_kline",
  │       facet="tech",
  │       kind="incremental",
  │       params=params,
  │       trigger_source="manual",
  │    )  ← 落库（事务A: Depends session）
  │    → Redis: HSET collect:log:daily_kline:{log_id} (pending)
  │
  │ 2. try:
  │      task_runner.dispatch(
  │        log_id=log_id,
  │        service_name="daily_kline",
  │        service_class=DailyKlineService,
  │        facet="tech",
  │        kind="incremental",
  │        params=params,
  │      )
  │    except Exception as e:
  │      await log_service.mark_failed(...)
  │      raise
  │
  │ 3. return { log_id, status: "pending" }
  ▼
Route: return R.ok({ log_id, status, service_name, facet, message })
  ▼
前端：拿到 log_id → 加入轮询列表
```

### 4.2 后台执行（TaskRunner + Service）

```
TaskRunner._run (asyncio.Task)
  │ 独立 session: get_db_context()  ← 事务B
  │ redis = await get_redis()
  │ log_service = CollectLogService(session, redis)  ← 同 session
  │
  │ try:
  │   svc = service_class(
  │     session=session,
  │     log_service=log_service,
  │     task_runner=self,  ← 让 service 能再次派发子任务
  │   )  ← 已升级 service 用新签名；未升级 fallback 到旧
  │
  │   1. await log_service.mark_running("daily_kline", log_id)
  │      → DB: status=running
  │      → Redis: HSET status=running
  │
  │   2. async for batch in svc._run_collect(
  │        params=params,
  │        session=session,
  │        log_id=log_id,
  │        facet="tech",
  │        kind="incremental",
  │      ):
  │      saved_total += batch["saved"]
  │      fail_total += batch["fail"]
  │      progress = (saved_total + fail_total) / total * 100
  │
  │      await log_service.update_progress(  ← 只写 Redis
  │        service_name="daily_kline",
  │        log_id=log_id,
  │        progress=progress,
  │        saved_count=saved_total,
  │        fail_count=fail_total,
  │        total_count=total,
  │      )
  │
  │   3. if fail_total == 0: status = "success"
  │      elif saved_total == 0: status = "failed"
  │      else: status = "partial_fail"
  │
  │      await log_service.mark_finished(  ← 事务C
  │        service_name="daily_kline",
  │        log_id=log_id,
  │        status=status,
  │        saved_count=saved_total,
  │        fail_count=fail_total,
  │      )
  │      → DB: status=success/partial_fail
  │      → Redis: HSET status=success
  │
  │ except Exception as e:
  │   await log_service.mark_failed(
  │     service_name="daily_kline",
  │     log_id=log_id,
  │     error=str(e),
  │     saved_count=saved_total,
  │     fail_count=fail_total,
  │   )
  │
  ▼
TaskRunner: task.done() → 从 _tasks 清理
```

### 4.3 GET 查询日志

```
前端
  │ GET /collect/logs/daily_kline?limit=10
  ▼
Route: log_handler.list_logs
  │ log_service = Depends(get_collect_log_service)
  │ items = await log_service.list_logs(...)
  ▼
Service: CollectLogService.list_logs
  │ 1. logs = await repo.list_recent("daily_kline", 10)  ← 事务D
  │ 2. for log in logs:
  │      if log.status in ("pending", "running"):
  │        redis_data = await redis.hgetall(collect:log:daily_kline:{log_id})
  │        if redis_data: 覆盖 log 字段
  │ 3. return items
  ▼
Route: return R.ok({ items })
```

### 4.4 事务边界

| 事务 | 触发点 | session 来源 | 内容 |
|---|---|---|---|
| 事务 A | Route | Depends(get_db) | `log_service.create_pending` 内部 `repo.create` |
| 事务 B | 后台 | get_db_context() | `log_service.mark_running` 内部 `repo.update_status` |
| 事务 C | 后台 | get_db_context() | `log_service.mark_finished` 内部 `repo.finish` |
| 事务 D | Route | Depends(get_db) | `log_service.list_logs` 内部 `repo.list_recent` |
| Redis 写 | 同步 | 全局单例 | pending 初始化 / 实时进度 / 终态 |

---

## 五、验证结果

### 5.1 模块导入验证（17 项全过）

| 验证项 | 状态 |
|---|---|
| A1: CollectLogService | ✅ |
| A2: CollectTaskRunner | ✅ |
| A3: get_collect_log_service | ✅ |
| A4: get_daily_kline_service | ✅ |
| A5: DailyKlineService | ✅ |
| A6: log_handler | ✅ |
| A7: collect_handler | ✅ |
| A8: manage_router | ✅ |
| B1: CatalogService.list() | ✅ |
| B2: CatalogService.get_class() | ✅ |
| C1: DailyKlineService.collect() 返回 dict | ✅ |
| C2: _run_collect() 返回 generator | ✅ |
| D1: DI 工厂可被导入（不实例化） | ✅ |
| E1: TaskRunner 单例 + 接口 | ✅ |
| F1: CollectLogService 方法完整 | ✅ |
| G1: 旧 AOP 已删除 | ✅ |
| H1: CollectLogRepository 接口完整 | ✅ |

### 5.2 端到端测试（5 个流程全过）

| 测试 | 状态 | 说明 |
|---|---|---|
| 测试 1: collect() 编排入口 | ✅ | 返回 { log_id, status: "pending" } |
| 测试 2: CollectLogService 方法 | ✅ | create_pending / mark_running / update_progress / mark_finished / mark_failed 全部正常 |
| 测试 3: TaskRunner | ✅ | is_running / cancel 接口正常 |
| 测试 4: Route 层 collect_handler | ✅ | 成功调用 service.collect()，返回正确响应 |
| 测试 5: CollectLogService 读取 | ✅ | list_logs / get_log 正常 |

---

## 六、兼容性处理

### 6.1 现状

- **已升级 service**（1 个）：daily_kline_service
  - `__init__` 接受 `log_service` + `task_runner`
  - `collect()` 拆为编排入口（返回 dict）
  - 增加 `_run_collect()` 执行入口（generator）

- **未升级 service**（27 个）：tech(4) + capital(9) + fundamental(12) + news(1) + sentiment(1)
  - `__init__` 仍是 v1 签名（fetcher/repo/session）
  - `collect()` 仍是 v1 签名（返回 CollectResult）
  - 旧路由仍可访问（`/collect/tech/daily_kline` 等）

### 6.2 兼容性方案

**方案**：DI 工厂 + TaskRunner 都用 `_safe_new` / `try/except` 自动回退

```python
# DI 工厂（collect_service.py）
def _safe_new(cls, **kwargs):
    try:
        return cls(**kwargs), True
    except TypeError:
        old_kwargs = {k: v for k, v in kwargs.items()
                      if k not in ("log_service", "task_runner")}
        return cls(**old_kwargs), False

# TaskRunner（collect_task_runner.py）
try:
    svc = service_class(
        session=session,
        log_service=log_service,
        task_runner=self,
    )
except TypeError:
    svc = service_class(session=session)
```

**结果**：
- daily_kline 触发时：完整 Phase 2 流程（collect() 返回 log_id，TaskRunner 调 _run_collect）
- 其他 27 个 service 触发时：DI 工厂 fallback 到旧签名，TaskRunner 也 fallback。**但 Route 仍会 501**，因为 collect_handler 要求 `get_xxx_service` factory 存在

### 6.3 关键差异

| 维度 | daily_kline（已升级） | 其他 27 service（未升级） |
|---|---|---|
| 触发端点 | /collect/tech/daily_kline（Phase 2） | /collect/tech/adj_factor 等（仍走旧路由） |
| 业务编排 | 在 service.collect() | 在旧 route 端点 |
| 日志服务 | CollectLogService（已注入） | 旧 AOP（已删除，临时退回手动） |
| TaskRunner | 已派发 | 旧 route 自己 `asyncio.create_task` |

### 6.4 过渡期建议

**Step A**：其他 27 service 接入 Phase 2（按 tech → capital → fundamental → news 顺序，每批 5 个）

**Step B**：旧路由退役（删除 `interface/route/{facet}/__init__.py` 的 `@router.post(...)` 装饰）

**Step C**：DTO 整理（Phase 3）

---

## 七、API 文档

### 7.1 接口列表

| Method | Path | 说明 |
|---|---|---|
| `POST` | `/collect/{facet}/{service_name}` | 触发采集，返回 log_id（**仅 daily_kline 接入**） |
| `GET` | `/collect/logs/{service_name}` | 查询日志列表（合并 Redis 实时进度） |
| `GET` | `/collect/logs/{service_name}/{log_id}` | 查询单条日志详情 |
| `GET` | `/collect/catalog` | catalog（不变） |
| `GET` | `/collect/query/{name}` | 实时查询（不变） |

### 7.2 触发采集响应

```json
POST /collect/tech/daily_kline
Body: { "params": { "symbols": [], "start_date": "2024-01-01", "end_date": "2024-12-31" } }

Response: {
  "code": 200,
  "message": "success",
  "data": {
    "log_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending",
    "service_name": "daily_kline",
    "facet": "tech",
    "message": "采集任务已创建，请通过 /collect/logs/{service_name} 轮询进度"
  }
}
```

### 7.3 日志列表响应

```json
GET /collect/logs/daily_kline?limit=10

Response: {
  "code": 200,
  "message": "success",
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

---

## 八、关键设计决策

### 8.1 为什么无 AOP？

| 维度 | AOP（v1 装饰器） | 手动调用（v2） |
|---|---|---|
| 调用链 | `_run_collect` → 装饰器 wrapper → 实际代码 → 装饰器拦截 | 直接调用，可读性好 |
| 日志逻辑 | 分散在装饰器 + service | 显式在 service / TaskRunner |
| 依赖注入 | 装饰器难以注入 | 日志服务是 DI 注入的 |
| 调试 | 难（隐式拦截） | 易（显式调用） |

### 8.2 为什么 collect() 要拆"编排"和"执行"？

- **Route 不阻塞**：立即返回 `log_id`，前端轮询
- **职责分离**：编排（创建日志 + 派发）和执行（采集 + 进度）解耦
- **日志职责单一**：装饰器只管"已存在日志的进度"（已废弃，由 TaskRunner 接管）

### 8.3 "同一事务"是业务语义

```
业务期望："日志创建成功 + 任务派发成功" = 整体成功
        "日志创建失败" 或 "任务派发失败" = 整体回滚

实现方式：
    1. await log_service.create_pending(...)  ← 落库
    2. task_runner.dispatch(...)              ← 派发
    3. dispatch 失败 → 异常处理中调 log_service.mark_failed(...)
```

**不用 DB 事务的原因**：`asyncio.create_task` 不参与 DB 事务；强行包事务会让 session 持有太久，阻塞 Route。

### 8.4 路径不冲突

- `/collect/logs/{service_name}` vs `/collect/{facet}/{service_name}`
- FastAPI 按前缀匹配
- 注册顺序：`log_router` 在 `collect_router` 之前注册

---

## 九、风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| TaskRunner 重启后丢失任务 | 日志卡在 running | 重启时清理 running → failed（TODO） |
| 派发成功但 service 实例化失败 | 日志卡在 pending | TaskRunner try/except + mark_failed |
| Redis 写入失败 | 实时进度缺失 | 降级：Redis 失败时只查 DB |
| 27 service 改造引入 bug | 进度数据不准确 | 每批 5 个改完跑 smoke test |
| 旧路由与新路由共存 | 部分 service 走旧逻辑 | 已明确：501 提示未接入 |

---

## 十、后续计划

### Phase 2 接入（27 service）

按 facet 顺序，每批 5 个：
- [ ] tech：adj_factor / suspend / name_change / minute_kline（4 个）
- [ ] capital：moneyflow / moneyflow_hsgt / top_list / top_inst / block_trade（5 个）
- [ ] capital：margin / hsgt_top10 / limit_list / holder_number（4 个）
- [ ] fundamental：daily_basic / fin_income / top10_holders / top10_float_holders / dividend（5 个）
- [ ] fundamental：stock_basic / stock_concepts / concept_list / concept_members / concept_index_daily（5 个）
- [ ] fundamental：concept_minute / concept_snapshot（2 个）
- [ ] news：news（1 个）

### Phase 3

- 旧路由退役
- DTO 整理
- SSE / WebSocket 替代轮询
- MQ 解耦日志服务

---

## 十一、相关文档

| 文档 | 关系 |
|---|---|
| `01-采集日志进度优化方案.md` | v1（handler 创建日志） |
| `02-采集日志进度优化落地总结.md` | v1 落地 |
| `03-Phase2日志业务下沉重构方案.md` | 本轮详细方案 |
| `04-Phase2完整落地总结.md` | 完整方案 |
| `../../config/depend管理.md` | 核心规则 |

---

## 十二、Phase 2 核心代码位置速查

| 文件 | 路径 |
|---|---|
| CollectLogService | `backend/src/contexts/collect/application/service/manage/collect_log_service.py` |
| CollectTaskRunner | `backend/src/contexts/collect/infrastructure/adapter/background/collect_task_runner.py` |
| CollectLogService DI | `backend/src/contexts/collect/infrastructure/di/log_service.py` |
| log_handler | `backend/src/contexts/collect/interface/manage/log_handler.py` |
| collect_handler | `backend/src/contexts/collect/interface/manage/collect_handler.py` |
| DailyKlineService（已升级） | `backend/src/contexts/collect/application/service/tech/daily_kline_service.py` |
| DI 工厂注册表 | `backend/src/contexts/collect/infrastructure/di/collect_service.py` |
