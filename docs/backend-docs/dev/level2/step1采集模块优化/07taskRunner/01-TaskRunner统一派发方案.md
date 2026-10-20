# 07-TaskRunner 统一派发方案

> 位置：`docs/backend-docs/dev/level2/step1采集模块优化/07taskRunner/`
> 上游文档：
> - `../06采集日志进度优化/01-采集日志进度优化方案.md`（collect_logs 表 + Redis 进度已落地）
> - `../03整体同步/01-interface-service-repo同步方案.md`（28 个 service 三层同步已落地）
> - `../../config/DDD.md`（DDD 架构规范）
> 更新日期：2026-10-19
> 状态：**待评审（暂不修改代码）**

---

## 〇、决策与方向（评审前先看）

### 0.1 本次优化目标

本次优化解决两个问题：

1. **`log_id` 与后台任务绑定关系弱**：当前 Phase 2 实现了 `collect_logs` 表 + `CollectTaskRunner`，但 `log_id` 的生成、派发、状态更新之间缺乏强不变量保证；进程重启后卡在 `running` 状态的任务无法恢复；`service_class=type(self)` 传递方式无法支持 scheduler 等外部派发。
2. **TaskRunner 与 service 耦合过紧**：Runner 接收 `service_class` / `facet` / `kind` 等参数，但这些全部可从 `service.META` 派生；27 个 service 中 25 个还是同步阻塞的旧模式，Runner 的 generator 协议无人使用；双 session 架构（`get_raw_db` vs `get_db`）导致 DI 工厂混乱。

### 0.2 解决思路

| 问题 | 方案 |
|---|---|
| `log_id` 与任务绑定弱 | 复用 `CatalogService._cls_by_name` 路由表（`service_name` → class），dispatch 只传 `log_id / service_name / params`；进程启动时 `recover_orphan_logs()` 扫描卡在 `running` 的日志 |
| Runner 接收过多参数 | dispatch 接口极简化：`dispatch(log_id, service_name, params)`；facet/kind 全从 `META` 派生 |
| Phase 1/2 共存导致双签名兼容 | 全部 25 个旧 service 升级到 `_run_collect()` 协议；删除 `_safe_new` 双签名回退逻辑 |
| 进程重启后 orphan 任务 | `recover_orphan_logs()`：启动时扫 `status=running` + `updated_at < now - 30min`，标记 `failed` |
| 错误粒度不够导致整批 failed | service 层 `_collect_one_safe()` 兜底：单 symbol 失败 → yield `{saved:0, fail:1}` 而非抛异常穿透 |

### 0.3 重要决策（评审通过项）

- **不引入 MQ**：日志创建、进度更新、终态落库全部走 DB/Redis，**不引入 RabbitMQ/Kafka**。
- **不引入全局任务队列**（如 Celery）：asyncio.create_task 进程内派发够用，多进程部署用 `multiprocessing` 或独立 worker。
- **不新增 service 注册表**：复用现有 `CatalogService._cls_by_name`（`service_name` → class 路由表）—— 28 个 service 已经在 catalog 启动时全量反射过一份，**不再维护第二份注册表**。
- **dispatch 接口极简**：`dispatch(log_id, service_name, params)`；class / facet / kind 全从 `CatalogService.get_class(name).META` 派生。
- **`_run_collect()` 收窄到只接 `params`**：service 自身从 `self.META` 拿 facet/kind，Runner 不用再传；进一步减少 Runner 与 service 之间的耦合。
- **双 session 架构在 DI 工厂层解**：所有 service 的日志写入统一走 `CollectLogService`，不需要每个 service factory 单独声明 `log_session`。
- **service 层仍是 `collect()` + `_run_collect()` 双入口**：HTTP 调 `collect()`（编排），Runner 调 `_run_collect()`（执行）；不合并为单一方法（因为 HTTP 入口需要立即返回 log_id）。
- **进度只写 Redis**：终态才写 DB；orphan recovery 兜底 Redis 丢失的场景。

---

## 一、现状问题详解

### 1.1 `log_id` 生命周期现状

```
HTTP Handler (FastAPI)
  │
  ├─ ① service.collect(params)  [HTTP session]
  │     └─ log_service.create_pending()   → INSERT collect_logs (status=pending)
  │                                         + HSET Redis (status=pending)
  │
  └─ ② return { log_id, status }  [立即返回 HTTP]
         │
         │ 同时后台：
         ▼
       TaskRunner._run(log_id, ...)  [新 session]
         └─ mark_running()              → UPDATE collect_logs (status=running)
         └─ async for batch in svc._run_collect(...)  [generator]
         └─ update_progress()            → HSET Redis (progress)
         └─ mark_finished()             → UPDATE collect_logs (终态)
```

### 1.2 当前实现的 6 个核心问题

#### 问题 1：`log_id` 创建与派发不在同一事务边界

```python
# daily_kline_service.py
async def collect(self, params: dict) -> dict:
    log_id = await self._log_service.create_pending(...)  # ← INSERT + commit
    self._task_runner.dispatch(log_id=log_id, ...)        # ← asyncio.create_task，异步
    return {"log_id": log_id, "status": "pending"}
```

- `create_pending` 已经 commit（`CollectLogRepository.create()` 最后有 `await self._session.commit()`）
- `dispatch()` 是纯内存操作，几乎不失败
- 但语义上：日志创建成功后，如果进程在 commit 之后、`create_task` 之前 crash，任务被永久丢失

#### 问题 2：进程内 `_tasks[log_id]` registry 重启丢失

```python
class CollectTaskRunner:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}  # ← 进程内 dict
```

- gunicorn workers 多进程：每个 worker 各自一份 `_tasks`
- 进程重启（reload/oom/部署）：`_tasks` 全丢，但 `collect_logs` 里可能有 `status=running` 的记录
- 没有 orphan recovery 机制 → 这些任务永远卡住

#### 问题 3：`service_class=type(self)` 无法从外部派发

```python
# service.collect() 内
self._task_runner.dispatch(
    log_id=log_id,
    service_class=type(self),  # ← 只能传 class，不能传字符串
    ...
)
```

- 想做 scheduler（定时任务）派发：scheduler 进程里没有 HTTP 请求，拿不到 `type(self)`
- 想做 admin 后台"重试失败任务"：也需要 import 对应的 service class
- 需要一个字符串路由键 `service_name` → class 的映射（已有 `CatalogService._cls_by_name`，本方案直接复用）

#### 问题 4：双 session 架构导致 DI 工厂混乱

```python
# collect_service.py
def get_stock_basic_service(
    session: AsyncSession = Depends(get_raw_db),   # ← 数据写 raw_data_db
    log_session: AsyncSession = Depends(get_db),  # ← 日志写 attribution_db
    redis=Depends(get_redis),
):
    return StockBasicService(
        session=session,
        log_service=_build_log_service(session, redis, log_session=log_session),
        ...
    )
```

- `stock_basic` / `daily_kline` 数据在 raw_data_db，日志在 attribution_db → 需要双 session
- 其他 26 个 service 混用 `get_raw_db` 或 `get_db`，行为不一致
- `_build_log_service` 的 `log_session` 参数是隐藏的坑，新 service 容易漏

#### 问题 5：Phase 1/2 共存导致双签名兼容

```python
# TaskRunner._run() 内
try:
    svc = service_class(session=session, log_service=log_service, task_runner=task_runner)
except TypeError:
    svc = service_class(session=session)  # ← 回退到旧签名
```

- 25 个 service 走旧签名 → `_run_collect()` 不存在 → 实际不会调用 generator
- 旧 service 的 `collect()` 是同步的，不会触发 `asyncio.create_task`
- 前端看到的效果：部分 service 异步有进度，部分 service 同步阻塞

#### 问题 6：错误粒度不够导致整批 failed

```python
# daily_kline_service._collect_one()
for attempt in range(3):
    try:
        klines = await self._fetcher.fetch(...)
        return await self._save(symbol, klines)
    except Exception as e:
        if attempt < 2:
            await asyncio.sleep(1)
        else:
            raise  # ← 抛出 → generator 退出 → TaskRunner except 捕获 → 整批 failed
```

---

## 二、统一抽象设计

### 2.1 复用 `CatalogService` 路由表（不新增 registry）

`CatalogService` 启动时已经反射 28 个 service class，内部维护了一份 `service_name → class` 路由表：

```python
# contexts/collect/application/service/manage/catalog_service.py
class CatalogService:
    def __init__(self, services: tuple[type, ...] | None = None) -> None:
        self._services = services or self._default_services()
        # ★ 路由表：service_name → class ★
        self._cls_by_name: dict[str, type] = {
            self._name_of(cls): cls for cls in self._services
        }
        ...

    def get_class(self, name: str) -> type | None:
        return self._cls_by_name.get(name)
```

**直接复用**，不维护第二份 registry：

| 旧方案 | 新方案 |
|---|---|
| 新建 `registry.py` + `@register_service` 装饰器 | ❌ **删** |
| `_SERVICE_REGISTRY: dict[str, type]` 进程内 dict | ❌ **删** |
| `get_service_class(name)` 函数 | ✅ 改为 `CatalogService.get_class(name)` |

**TaskRunner 拿到 `CatalogService` 的两种方式**：

| 方式 | 代码 | 适用 |
|---|---|---|
| **进程内单例**（推荐） | `_catalog = CatalogService()`（模块级 import 时建） | FastAPI 单进程；gunicorn 每个 worker 各自一份 |
| **依赖注入** | `runner = get_collect_task_runner(catalog=catalog)`（通过 FastAPI Depends） | 需要替换 catalog 的测试场景 |

> **不要**为了 registry 再造一次反射 —— 28 个 service 已经在 catalog 启动时全量反射过了。`CatalogService` 是 collect 模块唯一的 service 索引源，TaskRunner / 后续 scheduler / admin 重试工具都从它拿。

### 2.2 `CollectTaskSpec`：Runner 派发契约

```python
# contexts/collect/application/service/base.py

from dataclasses import dataclass


@dataclass(frozen=True)
class CollectTaskSpec:
    """Runner 派发契约 —— 任何 service 只要能产出这个 spec 就能 dispatch

    注意：fetcher / repo 不在这里 —— 那是 service 自己的私事，Runner 不感知。
    class / facet / kind 也不在这里 —— Runner 通过 CatalogService.get_class(name).META 派生。
    """
    log_id: str                    # 日志 ID（已由 create_pending 生成）
    service_name: str              # 路由键（与 META.name 一致）
    params: dict                   # 采集参数（持久化到 collect_logs.params）
```

### 2.3 `CollectServiceProtocol`：统一 service 接口

```python
# contexts/collect/application/service/base.py

from typing import AsyncGenerator, ClassVar


class CollectServiceProtocol(Protocol):
    """采集 service 统一接口

    所有 service 必须：
      1. 声明 META: ClassVar[ServiceMeta]
      2. 实现 collect(params) → dict（HTTP 编排入口）
      3. 实现 _run_collect(params) → AsyncGenerator（后台执行入口）

    collect() 负责建日志 + dispatch，不执行实际采集。
    _run_collect() 负责实际采集，yield 进度。
    """
    META: ClassVar["ServiceMeta"]

    async def collect(self, params: dict) -> dict:
        """HTTP 编排入口：建日志 + 派发后台任务，立即返回 { log_id, status }"""
        ...

    async def _run_collect(
        self,
        params: dict,
    ) -> AsyncGenerator[dict, None]:
        """后台执行入口：实际采集，yield 进度

        facet / kind 不再由 Runner 传入 —— service 自身从 self.META 派生：
            facet = self.META.facet
            kind  = self.META.kind.value

        Yields:
            每批结果 dict:
                - saved: 本批入库数
                - fail: 本批失败数
                - total: 本批总量（可选，用于进度计算）
        """
        ...
```

### 2.4 统一 `CollectLogService`：日志子系统独立闭环

```python
# contexts/collect/application/service/manage/collect_log_service.py

class CollectLogService:
    """采集日志业务服务（日志子系统唯一业务入口）

    所有写操作都在这里：
      - create_pending()
      - mark_running()
      - update_progress()
      - mark_finished()
      - mark_failed()
      - recover_orphan_logs()  ← 新增：进程启动时恢复 orphan
    """

    # 写方向
    async def create_pending(...) -> str:
        """创建日志（pending）"""
        ...

    async def mark_running(...) -> None:
        """pending → running"""
        ...

    async def update_progress(...) -> None:
        """实时进度（只写 Redis）"""
        ...

    async def mark_finished(...) -> None:
        """终态：success / partial_fail"""
        ...

    async def mark_failed(...) -> None:
        """异常：failed"""
        ...

    async def recover_orphan_logs(self, timeout_minutes: int = 30) -> int:
        """进程启动时恢复 orphan 日志

        扫描 status=running 且 updated_at 早于 timeout 的记录，
        全部标记为 failed（原因：process_restart）。

        Returns:
            恢复的日志数量
        """
        ...

    # 读方向
    async def list_logs(...) -> list[dict]:
        ...

    async def get_log(...) -> dict | None:
        ...
```

---

## 三、TaskRunner 重构方案

### 3.1 新旧 dispatch 接口对比

| 字段 | 旧接口 | 新接口 |
|---|---|---|
| `log_id` | ✅ 传 | ✅ 传 |
| `service_name` | ✅ 传 | ✅ 传 |
| `service_class` | ✅ 传 | ❌ **删**（从 `CatalogService.get_class(name)` 查） |
| `facet` | ✅ 传 | ❌ **删**（从 META 派生） |
| `kind` | ✅ 传 | ❌ **删**（从 META 派生） |
| `params` | ✅ 传 | ✅ 传 |

### 3.2 新 dispatch 接口

```python
# contexts/collect/infrastructure/adapter/background/collect_task_runner.py

from contexts.collect.application.service.manage import CatalogService

# 进程内单例 —— catalog 启动时已全量反射过 28 个 service，路由表可直接复用
_catalog = CatalogService()


class CollectTaskRunner:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}

    def dispatch(
        self,
        log_id: str,
        service_name: str,
        params: dict,
    ) -> None:
        """派发后台采集任务（立即返回）

        Args:
            log_id: 日志 ID（已由 create_pending 创建）
            service_name: 服务名（与 META.name 一致，用于路由）
            params: 采集参数
        """
        # ★ 从 CatalogService 路由表查 class 和 meta
        service_class = _catalog.get_class(service_name)
        if service_class is None:
            raise KeyError(f"unknown service: {service_name!r}")
        meta = service_class.META

        task = asyncio.create_task(
            self._run(log_id, service_class, meta, params)
        )
        self._tasks[log_id] = task
        logger.info(
            "派发采集任务: log_id=%s, service=%s/%s",
            log_id, meta.facet, service_name,
        )
        task.add_done_callback(lambda t: self._tasks.pop(log_id, None))
```

**依赖方向**：

```
collect_task_runner.py
  └─ import: contexts.collect.application.service.manage.catalog_service (CatalogService)
                       ↑
                       └─ CatalogService 自身依赖 28 个 service class 的 import
```

> CatalogService 在 `manage/__init__.py` 已 re-export，**不引入新的循环依赖**。`TaskRunner → CatalogService → service classes` 是单向链。

### 3.3 新 `_run()` 入口

```python
async def _run(
    self,
    log_id: str,
    service_class: type,
    meta: "ServiceMeta",
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
            # ★ 实例化 service（只传 session，log_service 和 task_runner 暂不传）
            svc = service_class(session=session)

            # ★ 1. 标记 running
            await log_service.mark_running(meta.name, log_id)

            # ★ 2. 执行采集（generator 模式）
            #     facet / kind 不再传入 —— service 自身从 self.META 读
            saved_total = 0
            fail_total = 0
            total = 0

            async for batch in svc._run_collect(params=params):
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
                    service_name=meta.name,
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
                service_name=meta.name,
                log_id=log_id,
                status=status,
                saved_count=saved_total,
                fail_count=fail_total,
            )

        except Exception as e:
            logger.exception("采集任务失败: log_id=%s, service=%s", log_id, meta.name)
            await log_service.mark_failed(
                service_name=meta.name,
                log_id=log_id,
                error=str(e),
                saved_count=saved_total,
                fail_count=fail_total,
            )
```

### 3.4 移除双签名兼容

**旧逻辑（删）**：

```python
try:
    svc = service_class(session=session, log_service=log_service, task_runner=task_runner)
except TypeError:
    svc = service_class(session=session)  # ← 回退到旧签名
```

**新逻辑（删）**：

所有 service 升级到 Phase 2 后，`service_class(session=session)` 是唯一入口。`_run_collect()` 是强制接口，不存在则 AttributeError。

### 3.5 `recover_orphan_logs()`：孤儿日志恢复

```python
async def recover_orphan_logs(self, timeout_minutes: int = 30) -> int:
    """进程启动时恢复 orphan 日志

    扫描 collect_logs 表中 status=running 且 updated_at 早于 timeout 分钟的记录，
    全部标记为 failed（原因：进程重启）。

    在 App lifespan startup 时调用。
    """
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(minutes=timeout_minutes)

    # 1. 查 orphan 日志
    stmt = (
        select(CollectLogDB)
        .where(CollectLogDB.status == "running")
        .where(CollectLogDB.updated_at < cutoff)
    )
    orphans = (await self._session.execute(stmt)).scalars().all()

    if not orphans:
        return 0

    # 2. 批量标记 failed
    for log in orphans:
        await self._repo.finish(
            log.id,
            "failed",
            saved_count=log.saved_count or 0,
            fail_count=log.fail_count or 0,
            error=f"process_restart: orphan recovered at {datetime.now().isoformat()}",
            finished_at=datetime.now(),
        )
        logger.warning("恢复 orphan 日志: log_id=%s, service=%s, started_at=%s",
                       log.id, log.service_name, log.started_at)

    await self._session.commit()
    return len(orphans)
```

### 3.6 DI 工厂简化

```python
# contexts/collect/infrastructure/di/collect_service.py

# ── 旧逻辑（删）─────────────────────────────────────────────
def _build_log_service(session, redis, *, log_session=None):
    return CollectLogService(session=log_session or session, redis_client=redis)

def _safe_new(cls, **kwargs):
    try:
        return cls(**kwargs), True
    except TypeError:
        old_kwargs = {k: v for k, v in kwargs.items()
                      if k not in ("log_service", "task_runner")}
        return cls(**old_kwargs), False
# ── 旧逻辑（删）─────────────────────────────────────────────

# ── 新逻辑（简）─────────────────────────────────────────────
from shared.infrastructure.di.db_session import get_db, get_raw_db
from shared.infrastructure.di.redis_session import get_redis
from contexts.collect.application.service.manage import CollectLogService
from contexts.collect.infrastructure.adapter.background import get_collect_task_runner

def _new_service(
    cls: type,
    session,
):
    """统一实例化：所有 service 都用相同参数"""
    return cls(session=session)  # ← 只传 session，其他从 self.META / CatalogService 查
# ── 新逻辑（简）─────────────────────────────────────────────

# 示例：get_daily_kline_service
def get_daily_kline_service(
    session: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.tech.daily_kline_service import (
        DailyKlineService,
    )
    return _new_service(DailyKlineService, session=session)

# 示例：get_stock_basic_service（数据在 raw_db，日志在 attribution_db）
def get_stock_basic_service(
    data_session: AsyncSession = Depends(get_raw_db),  # ← 数据 session
    log_session: AsyncSession = Depends(get_db),          # ← 日志 session
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.fundamental.stock_basic_service import (
        StockBasicService,
    )
    from contexts.collect.application.service.manage import CollectLogService

    # 日志服务单独建（双 session 问题在日志服务层解）
    log_service = CollectLogService(session=log_session, redis_client=redis)

    return StockBasicService(
        session=data_session,
        log_service=log_service,          # ← 显式传日志服务
        task_runner=get_collect_task_runner(),
    )
```

> **说明**：双 session 问题在 DI 工厂层显式声明，而不是用隐藏的 `_build_log_service(session, redis, log_session=log_session)` trick。

---

## 四、service 层改造方案

### 4.1 旧 service 升级到 Phase 2

所有 25 个旧 service 需要改造：

```
旧 collect(params) → CollectResult
      ↓
新 collect(params) → dict (log_id + status)
新 _run_collect(params) → AsyncGenerator   ← facet/kind 从 self.META 派生
```

### 4.2 改造模板（写库类）

```python
# xxx_service.py（改造后）

class XxxService:
    META = ServiceMeta(
        name="xxx",
        facet="...",
        label="...",
        kind=ServiceKind.INCREMENTAL,
        rate_limit=("tushare", 200, 60),
        concurrency=1,
    )

    def __init__(
        self,
        session: AsyncSession,
        log_service: "CollectLogService" | None = None,
        task_runner: "CollectTaskRunner" | None = None,
        fetcher: "XxxTushareFetcher" | None = None,
        repo: "XxxRepository" | None = None,
    ) -> None:
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        self._fetcher = fetcher or XxxTushareFetcher()
        self._repo = repo or XxxRepository()

    # ═══════════════════════════════════════════════════════════════
    # 入口 A：HTTP 触发（Route 层调）
    # ═══════════════════════════════════════════════════════════════

    async def collect(self, params: dict) -> dict:
        """HTTP 触发入口：编排（不执行实际采集）"""
        # 1. 创建日志
        log_id = await self._log_service.create_pending(
            service_name=self.META.name,
            facet=self.META.facet,
            kind=self.META.kind.value,
            params=params,
            trigger_source="manual",
        )
        # 2. 派发后台任务（service_name 是唯一路由键）
        self._task_runner.dispatch(log_id=log_id, service_name=self.META.name, params=params)
        return {"log_id": log_id, "status": "pending"}

    # ═══════════════════════════════════════════════════════════════
    # 入口 B：后台执行（TaskRunner 调）
    # ═══════════════════════════════════════════════════════════════

    async def _run_collect(
        self,
        params: dict,
    ) -> AsyncGenerator[dict, None]:
        """后台执行入口：实际采集，yield 进度

        facet / kind 不再由 Runner 传入 —— 直接从 self.META 拿：
            facet = self.META.facet
            kind  = self.META.kind.value
        """
        # 1. 解析参数
        symbols = params.get("symbols") or []
        trade_date = params.get("trade_date")

        # 2. 限流
        await check(self.META.rate_limit)

        # 3. 全量模式
        if not symbols:
            symbols = await list_all_a_symbols()
            if not symbols:
                yield {"saved": 0, "fail": 1, "total": 0, "message": "symbols 为空"}
                return

        symbols = [str(s).zfill(6) for s in symbols]
        total = len(symbols)
        sem = asyncio.Semaphore(self.META.concurrency)

        async def _collect_one_safe(s: str) -> dict:
            """单笔采集兜底：失败返回 fail dict 而非抛异常"""
            try:
                return await self._collect_one(s)
            except Exception as e:
                logger.warning("采集 %s 失败: %s", s, e)
                return {"saved": 0, "fail": 1, "total": 1, "message": str(e)}

        async def one(s: str) -> dict:
            async with sem:
                return await _collect_one_safe(s)

        # 4. 边完成边 yield
        tasks = [asyncio.create_task(one(s)) for s in symbols]
        for coro in asyncio.as_completed(tasks):
            yield await coro

    # ═══════════════════════════════════════════════════════════════
    # 内部方法（业务逻辑，不涉及日志）
    # ═══════════════════════════════════════════════════════════════

    async def _collect_one(self, s: str) -> dict:
        """采集单笔（可抛异常）"""
        await check(self.META.rate_limit)
        for attempt in range(3):
            try:
                bos = await self._fetcher.fetch(symbol=s)
                saved = await self._repo.save(bos, self._session)
                return {"saved": saved, "fail": 0, "total": 1}
            except RateLimited as e:
                if attempt < 2:
                    import asyncio
                    await asyncio.sleep(e.retry_after)
                else:
                    raise
        return {"saved": 0, "fail": 1, "total": 1}
```

### 4.3 改造清单

| # | service | facet | kind | 改造方式 |
|---|---|---|---|---|
| 1 | `AdjFactorService` | tech | INCREMENTAL | 模板改造 |
| 2 | `SuspendService` | tech | INCREMENTAL | 模板改造 |
| 3 | `NameChangeService` | tech | FULL_REFRESH | 模板改造 |
| 4 | `MoneyflowService` | capital | INCREMENTAL | 模板改造 |
| 5 | `MoneyflowHsgtService` | capital | INCREMENTAL | 模板改造 |
| 6 | `TopListService` | capital | INCREMENTAL | 模板改造 |
| 7 | `TopInstService` | capital | INCREMENTAL | 模板改造 |
| 8 | `BlockTradeService` | capital | INCREMENTAL | 模板改造 |
| 9 | `MarginService` | capital | INCREMENTAL | 模板改造 |
| 10 | `HsgtTop10Service` | capital | INCREMENTAL | 模板改造 |
| 11 | `LimitListService` | capital | INCREMENTAL | 模板改造 |
| 12 | `HolderNumberService` | capital | INCREMENTAL | 模板改造 |
| 13 | `DailyBasicService` | fundamental | INCREMENTAL | 模板改造 |
| 14 | `FinIncomeService` | fundamental | INCREMENTAL | 模板改造 |
| 15 | `Top10HoldersService` | fundamental | INCREMENTAL | 模板改造 |
| 16 | `Top10FloatHoldersService` | fundamental | INCREMENTAL | 模板改造 |
| 17 | `DividendService` | fundamental | INCREMENTAL | 模板改造 |
| 18 | `StockBasicService` | fundamental | FULL_REFRESH | ✅ 已有（检查） |
| 19 | `StockConceptsService` | fundamental | FULL_REFRESH | 模板改造 |
| 20 | `ConceptListService` | fundamental | FULL_REFRESH | 模板改造 |
| 21 | `ConceptMembersService` | fundamental | INCREMENTAL | 模板改造 |
| 22 | `ConceptIndexDailyService` | fundamental | INCREMENTAL | 模板改造 |
| 23 | `ConceptSnapshotService` | fundamental | REALTIME | 模板改造（可跳过） |
| 24 | `NewsService` | news | INCREMENTAL | 模板改造 |
| 25 | `SentimentService` | sentiment | FULL_REFRESH | 空壳，不动 |

> `DailyKlineService` 和 `StockBasicService` 已经是 Phase 2，只需检查 `_run_collect()` 是否符合新签名。

---

## 五、Route 层改造方案

### 5.1 旧 `_run()` helper（删）

```python
# 旧：5 个 route 文件各自有 _run() helper
async def _run(svc, body: CollectRequest) -> CollectResponse:
    result = await svc.collect(body.params)
    # 旧逻辑：判断是 dict 还是 CollectResult
```

### 5.2 新统一 `_run()` helper

```python
# 统一 helper（放在 shared 或 base 模块）
from contexts.collect.interface.dto.response.collect import ApiResponse, CollectResponse

async def run_collect(svc, body: CollectRequest) -> dict:
    """统一执行：所有 route 共用

    Phase 2 统一返回 dict（log_id + status）。
    """
    result = await svc.collect(body.params)
    return CollectResponse(
        log_id=result.get("log_id"),
        status=result.get("status"),
        message=f"采集任务已派发，请用 log_id 轮询",
    )
```

### 5.3 新 route 模板

```python
# route/tech/__init__.py（改造后）
@router.post(
    "/daily_kline",
    summary="日 K 线采集",
    response_model=ApiResponse[CollectResponse],
)
async def daily_kline_trigger(
    body: CollectRequest,
    svc=Depends(get_daily_kline_service),
) -> dict:
    return R.ok((await run_collect(svc, body)).model_dump())
```

---

## 六、CollectLogService 改造方案

### 6.1 新增 `recover_orphan_logs()`

```python
async def recover_orphan_logs(self, timeout_minutes: int = 30) -> int:
    """进程启动时恢复 orphan 日志

    扫描 status=running 且 updated_at 早于 timeout 分钟的记录，
    批量标记为 failed（原因：进程重启）。
    """
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(minutes=timeout_minutes)

    stmt = (
        select(CollectLogDB)
        .where(CollectLogDB.status == "running")
        .where(CollectLogDB.updated_at < cutoff)
    )
    result = await self._session.execute(stmt)
    orphans = result.scalars().all()

    if not orphans:
        return 0

    for log in orphans:
        await self._repo.finish(
            log.id,
            status="failed",
            saved_count=log.saved_count or 0,
            fail_count=log.fail_count or 0,
            error=f"orphan recovered: process_restart at {datetime.now().isoformat()}",
            finished_at=datetime.now(),
        )
        logger.warning(
            "恢复 orphan 日志: log_id=%s, service=%s, started_at=%s",
            log.id, log.service_name, log.started_at,
        )

    await self._session.commit()
    return len(orphans)
```

### 6.2 App lifespan startup 集成

```python
# main.py 或 app lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：恢复 orphan 日志
    from shared.infrastructure.di.db_session import get_db_context
    from shared.infrastructure.di.redis_session import get_redis
    from contexts.collect.application.service.manage import CollectLogService

    async with get_db_context() as session:
        redis = await get_redis()
        log_service = CollectLogService(session=session, redis_client=redis)
        recovered = await log_service.recover_orphan_logs(timeout_minutes=30)
        if recovered:
            logger.info("进程启动：恢复 %d 个 orphan 日志", recovered)

    yield

    # 关闭时：取消所有正在运行的任务（可选）
    runner = get_collect_task_runner()
    for log_id, task in list(runner._tasks.items()):
        if not task.done():
            task.cancel()
```

---

## 七、文件改动清单

### 7.1 新增/改动文件

| 文件 | 说明 |
|---|---|
| `contexts/collect/application/service/manage/catalog_service.py`（**已有，不改**） | 复用 `_cls_by_name` 路由表，TaskRunner 通过 `CatalogService.get_class(name)` 查 |
| `contexts/collect/application/service/base.py`（改） | 新增 `CollectTaskSpec` + 强化 `CollectServiceProtocol`（`_run_collect` 收窄为只接 `params`） |

> **没有新增文件**。`registry.py` 已删除 —— 不再单独维护 service 注册表，复用 `CatalogService`。

### 7.2 改造文件

| 文件 | 改动 |
|---|---|
| `contexts/collect/infrastructure/adapter/background/collect_task_runner.py` | dispatch 极简化 + 删 `_safe_new` + 删 facet/kind/class 参数 |
| `contexts/collect/application/service/manage/collect_log_service.py` | 新增 `recover_orphan_logs()` |
| `contexts/collect/infrastructure/di/collect_service.py` | 简化 DI 工厂 + 删 `_build_log_service` + 删 `_safe_new` |
| `contexts/collect/interface/route/tech/__init__.py` | 统一 `_run()` helper |
| `contexts/collect/interface/route/capital/__init__.py` | 同上 |
| `contexts/collect/interface/route/fundamental/__init__.py` | 同上 |
| `contexts/collect/interface/route/news/__init__.py` | 同上 |
| `contexts/collect/interface/route/sentiment/__init__.py` | 同上 |
| `contexts/collect/application/service/tech/adj_factor_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/tech/suspend_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/tech/name_change_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/capital/moneyflow_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/capital/moneyflow_hsgt_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/capital/top_list_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/capital/top_inst_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/capital/block_trade_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/capital/margin_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/capital/hsgt_top10_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/capital/limit_list_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/capital/holder_number_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/fundamental/daily_basic_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/fundamental/fin_income_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/fundamental/top10_holders_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/fundamental/top10_floatholders_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/fundamental/dividend_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/fundamental/stock_concepts_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/fundamental/concept_list_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/fundamental/concept_members_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/fundamental/concept_index_daily_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/fundamental/concept_snapshot_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/news/news_service.py` | Phase 2 升级 |
| `contexts/collect/application/service/tech/daily_kline_service.py` | 检查签名 |
| `contexts/collect/application/service/fundamental/stock_basic_service.py` | 检查签名 |

### 7.3 main.py / lifespan 集成

| 文件 | 改动 |
|---|---|
| `main.py` 或 `app.py` | lifespan startup 调用 `recover_orphan_logs()` |

---

## 八、实现优先级

### Phase 1：核心闭环（TaskRunner 自身改造）

1. 改造 `CollectTaskRunner.dispatch()` —— 进程内单例 `_catalog = CatalogService()`，从 `get_class(name).META` 拿 facet/kind；**不新建任何 registry**
2. 改造 `CollectTaskRunner._run()` —— 调 `svc._run_collect(params=params)`，**不再传 facet/kind**
3. 新增 `CollectLogService.recover_orphan_logs()`
4. DI 工厂简化（删 `_build_log_service` + `_safe_new`）
5. lifespan startup 集成 `recover_orphan_logs()`
6. **选 1 个 service（AdjFactorService）做完整链路验证**

### Phase 2：25 个旧 service 全部升级

7. 剩余 24 个 service 逐个改造为 Phase 2 模板（`collect()` + `_run_collect(params)` 双入口）
8. `daily_kline_service.py` / `stock_basic_service.py` 检查签名

### Phase 3：Route 层简化

9. 统一 `_run()` helper，下沉到 shared 或 base 模块
10. 5 个 route 文件统一使用新 helper

### Phase 4：验收

11. 全量 28 个 endpoint 回归测试
12. 进程重启 orphan 恢复测试
13. 多 service 并发派发测试

---

## 九、实现工作量估算

| Phase | 步骤 | 估算 |
|---|---|---|
| **Phase 1** | 1-7（TaskRunner 改造 + 1 个 service 验证） | 2-3 小时 |
| **Phase 2** | 8-10（25 个旧 service 升级） | 每个 30 分钟，共 ~12 小时 |
| **Phase 3** | 11-12（Route 层简化） | 1 小时 |
| **Phase 4** | 13-15（验收 + 测试） | 2 小时 |
| **总计** | | **~17-18 小时** |

---

## 十、验收清单

### 10.1 静态验证

```bash
# 1. CatalogService 能查到全部 28 个 service（含 sentiment）
python -c "
from contexts.collect.application.service.manage import CatalogService
c = CatalogService()
print(f'已注册 service 数: {len(c.list()) + 1}（含隐藏的 sentiment）')
print(f'路由表大小: {len(c._cls_by_name)}')
"

# 2. 无 _safe_new 双签名回退逻辑
grep -r "_safe_new" backend/src/contexts/collect/
# 期望：无结果

# 3. 无 _build_log_service 隐藏双 session
grep -r "_build_log_service" backend/src/contexts/collect/
# 期望：无结果

# 4. 无 SERVICE_REGISTRY / register_service 残留
grep -r "SERVICE_REGISTRY\|register_service" backend/src/contexts/collect/
# 期望：无结果

# 5. TaskRunner.dispatch() 签名检查
grep -A5 "def dispatch" backend/src/contexts/collect/infrastructure/adapter/background/collect_task_runner.py
# 期望：只有 log_id / service_name / params 三个参数
```

### 10.2 功能验证

```bash
# 1. 触发任意 service 采集，log_id 正常返回
curl -X POST http://localhost:8000/collect/capital/margin \
  -H "Content-Type: application/json" \
  -d '{"params": {"trade_date": "2026-10-18"}}'

# 期望：{"code": 0, "data": {"log_id": "xxx", "status": "pending"}}

# 2. 轮询日志进度
curl http://localhost:8000/collect/logs/margin/<log_id>

# 期望：status 从 pending → running → success/partial_fail/failed

# 3. 进程重启后 orphan 恢复
# kill -9 进程（模拟 crash）
# 重启后检查日志
grep "recover orphan" logs/app.log
```

### 10.3 并发验证

```bash
# 同时派发 3 个不同 service 的任务
for svc in margin moneyflow top_list; do
  curl -X POST http://localhost:8000/collect/capital/$svc \
    -H "Content-Type: application/json" \
    -d '{"params": {}}' &
done
wait

# 期望：3 个 log_id 都正常返回，互不干扰
```

---

## 十一、决策项（待评审）

| # | 决策 | 选项 | 推荐 |
|---|---|---|---|
| **D1** | 双 session 问题在谁解决 | A. DI 工厂显式声明 / B. 日志服务内部判断 | **A**（显式更清晰） |
| **D2** | `recover_orphan_logs()` 超时阈值 | A. 30 分钟 / B. 60 分钟 | **A**（够短，能及时发现 crash） |
| **D3** | 旧 service 升级顺序 | A. 按 facet 批量 / B. 按依赖顺序（fundamental 先） | **A**（tech 5 个先做，验证链路） |
| **D4** | `facet`/`kind` 是否还在 `collect_logs` 表存 | A. 保留（冗余） / B. 从 service_name 派生 | **A**（查询时避免 join） |

---

## 十二、风险与回退

### 12.1 风险

| 风险 | 概率 | 缓解 |
|---|---|---|
| 25 个 service 升级引入回归 | 中 | 每个 service 改造后单独测试；Phase 4 全量回归 |
| `recover_orphan_logs()` 在多进程场景误判 | 低 | timeout=30min，且只改 `status=failed`，不删数据 |
| DI 工厂简化破坏现有 service | 中 | Phase 1 先验证 `daily_kline` / `stock_basic`，再批量升级 |

### 12.2 回退策略

每 Phase 独立 commit；任一 Phase 失败可 `git revert`。

---

## 十三、后续排队

| 序号 | PR | 依赖 | 状态 |
|---|---|---|---|
| **#P3-7** | Phase 1: TaskRunner 自身改造 + orphan 恢复 | — | 本次 |
| **#P3-8** | Phase 2: 25 个旧 service 全部升级到 Phase 2 | P3-7 | 本次 |
| **#P3-9** | Phase 3: Route 层简化 | P3-7 | 本次 |
| **#P3-10** | Phase 4: 验收 + 测试 | P3-7 + P3-8 + P3-9 | 本次 |
| **#P3-11**（延后） | Phase 5: scheduler 定时任务统一走 dispatch | P3-10 | 延后 |
| **#P3-12**（延后） | Phase 6: SSE/WebSocket 替代轮询 | P3-10 | 延后 |

---

**总结**：
- **本次 4 个 Phase，约 17-18 小时**，落地后所有 27 个 service 统一走 `TaskRunner.dispatch()`（**复用 `CatalogService._cls_by_name` 路由表，不维护第二份 registry**）。
- `_run_collect()` 收窄到只接 `params`（facet/kind 从 `self.META` 派生），Runner 与 service 之间的耦合度进一步降低。
- `log_id` 与任务强绑定：`create_pending()` → `dispatch()` → `mark_running()` → `update_progress()` → `mark_finished()` 全链路可追溯。
- 进程重启后 `recover_orphan_logs()` 兜底，避免卡在 `running` 的任务永远不结束。
- 双 session 问题在 DI 工厂层显式声明，不再用隐藏的 `_build_log_service` trick。
- PR 拆 4 个，每个 Phase 独立可回退。
