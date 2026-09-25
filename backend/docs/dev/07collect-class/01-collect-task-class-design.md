# 01 — 采集管理类设计重构

> 配套 UML：`docs/PlantUML/CollectTask/01-class.puml`
> 前置文档：`docs/dev/03dataana/04_collect_task_manage.md`（采集管理原始设计）
> 数据类：`docs/PlantUML/总体类设计/02_collect_task_log.puml`
> 概念采集原设计：`docs/dev/06gainian/02-infrastructure-design.md §5` + `docs/dev/06gainian/03-application-and-route-design.md §3.1`

---

## 一、概述

### 1.1 现状盘点

采集管理模块当前实现集中在两个文件：

| 文件 | 行数 | 职责 |
|:---|---:|:---|
| `backend/src/route/api/v1/collect_task.py` | 468 | 6 个 HTTP endpoint + 3 个内嵌 handler + 进度/取消/收尾工具函数 |
| `backend/src/infrastructure/tasks/concept_sync_operation.py` | 88 | 概念同步业务编排（独立，未接入采集管理） |

**核心痛点：**

| # | 痛点 | 后果 |
|:---:|:---|:---|
| 1 | `collect_task.py` 的 3 个 `_collect_*` handler 是平铺的内部函数 | 概念同步接入需要再复制一套进度/取消/收尾样板 |
| 2 | task_type 白名单硬编码在 router（`("daily_kline","daily_basic","stock_basic")`）和 handler dict | 新增类型需要同时改 router、handler dict 两处 |
| 3 | 进度更新 / 取消检查 / 收尾 DB 写入 三套样板代码散落各 handler | 任何一个 handler 都得照抄一遍，新人接手易遗漏 |
| 4 | `concept.py` 路由仍走 `sync_concepts()` → `ConceptAppService.sync_concepts()` → `ConceptSyncOperation.sync_all()` 的"伪后台"路径 | 概念同步在采集管理 tab 里既不可见，也不可取消 |
| 5 | `_cancel_flags: set[int]` 是模块级全局 | 多进程部署时失效，且与 `infrastructure/tasks/registry.py` 的 `asyncio.Task` 注册表职责重叠 |

### 1.2 重构目标

> **框架负责"通用"（进度、取消、收尾、并发安全），子类只负责"业务"（单元是什么、按什么顺序跑、跑完一个做什么）。**

具体拆解：

| 维度 | 目标 |
|:---|:---|
| **抽象层** | `BaseCollectTask` 抽象基类 + `UnitResult` / `TaskSummary` 两个不可变数据类 |
| **模板方法** | `execute_task(task_id, handler, params)` 是唯一入口，子类实现 `run()`、`estimate_total()` |
| **可扩展** | 新增 task_type = 在 registry 注册一行；router 白名单零修改 |
| **概念接入** | 复用现有 `ConceptSyncOperation._sync_one()`，跑通"采集管理 tab 里能触发概念同步 + 看到进度 + 取消" |
| **DDD 分层不变** | 全部落在 `infrastructure/tasks/`，不跨层 |

### 1.3 重构范围

✅ 在范围内：
- `infrastructure/tasks/` 新增 6 个文件
- `route/api/v1/collect_task.py` 瘦身到 ~150 行
- 前端 `data-collect/` 增补「概念同步」卡片（复用现有 `CollectPanel.vue`）

❌ 不在范围内（保持兼容）：
- `sys_collect_tasks` 表结构不动
- Redis 进度 hash 的 key/字段不动
- 现有 3 个 task_type 的 HTTP 协议不动
- `infrastructure/tasks/registry.py`（asyncio.Task 注册表）不动 —— 与本次设计的"task_type → handler"注册表是两件事

---

## 二、目录结构

```
backend/src/infrastructure/tasks/
├── registry.py                    ← 既有 (asyncio.Task 注册表)，保持不动
├── operation_dispatcher.py        ← 既有 (池操作派发器)，保持不动
├── concept_sync_operation.py      ← 既有 (概念同步业务编排)，被 concept.py 复用
│
├── collect/                       ← 🆕 新目录
│   ├── __init__.py
│   ├── base.py                    ← 模板方法 + BaseCollectTask + UnitResult + TaskSummary
│   ├── registry.py                ← task_type → handler 注册表 (CollectTaskRegistry)
│   ├── daily_kline.py             ← DailyKlineCollectTask (迁移自 collect_task.py:172-292)
│   ├── daily_basic.py             ← DailyBasicCollectTask (迁移自 collect_task.py:294-352)
│   ├── stock_basic.py             ← StockBasicCollectTask (迁移自 collect_task.py:354-400)
│   └── concept.py                 ← ConceptCollectTask (本次新增，复用 ConceptSyncOperation)
```

> **为什么不放在 `infrastructure/tasks/` 根目录？**
> 既有 `registry.py` / `operation_dispatcher.py` 是"运行时任务注册"（管 `asyncio.Task` 生命周期），与本次"task_type 字典"职责不同；同目录会撞名。把 6 个新文件放进 `collect/` 子包，命名空间隔离、对外引用也清晰（`from infrastructure.tasks.collect.base import BaseCollectTask`）。

---

## 三、核心抽象

### 3.1 类总览

| 类型 | 名称 | 性质 |
|:---|:---|:---|
| abstract class | `BaseCollectTask` | 模板方法骨架，子类必须实现 `estimate_total()` / `run()` |
| abstract method | `estimate_total(params) → int` | 返回单元数（前端进度条用），0 也合法 |
| abstract method | `run(params, on_unit_done) → TaskSummary` | 业务主循环，完成一个单元立即调 `on_unit_done(UnitResult, label)` |
| hook（可选） | `pre_execute(params)` | `execute_task` 开头，默认空（用于预热 fetcher 池） |
| hook（可选） | `post_execute(params, summary)` | `execute_task` 收尾，默认空（用于资源清理） |
| data class | `UnitResult` | 单个单元的汇报：`success / detail / error / skipped` |
| data class | `TaskSummary` | 整次任务的收尾：`success / fail / skip / message / total_count / elapsed_ms` |
| data class | `Cancelled` | exception，子类 run() 内 raise 即可中断（framework 也支持 in-place 检查） |

### 3.2 `UnitResult` 数据类

```python
@dataclass(frozen=True)
class UnitResult:
    """单个单元的执行结果，由 run() 通过 on_unit_done 上报"""
    success: bool            # True=成功 / False=失败
    detail: str = ""         # 描述（如 "写入 250 条"），前端 current 字段用
    error: str | None = None # 失败原因（success=False 时必填）
    skipped: bool = False    # 跳过（不计入 success/fail，单独累加）
    saved_count: int = 0     # 单元内写入记录数（用于 message 汇总）
```

### 3.3 `TaskSummary` 数据类

```python
@dataclass(frozen=True)
class TaskSummary:
    """整个 run() 结束后的收尾，由 run() 返回"""
    success: int
    fail: int
    skip: int = 0
    message: str = ""
    total_count: int = 0      # 实际处理的单元数（可能与 estimate_total 不同）
    elapsed_ms: int = 0
```

### 3.4 `BaseCollectTask` 基类契约

```python
class BaseCollectTask(ABC):
    """采集任务抽象基类

    子类契约：
    1. 必须实现 estimate_total(params) → int
       - 0 是合法值，表示"无单元"（如 stock_basic 全量同步只有 1 个单元）
       - 返回值会写 Redis hash 的 total 字段
    2. 必须实现 run(params, on_unit_done) → TaskSummary
       - 每完成一个单元，立刻调 on_unit_done(UnitResult, label)
       - 异常不要逃出，应捕获并包装成 UnitResult(success=False, error=str(e))
       - 若需要取消，raise Cancelled() 让 framework 收尾

    子类钩子（可选）：
    - pre_execute(params): execute_task 开头调用一次
    - post_execute(params, summary): execute_task 收尾调用一次
    """

    name: ClassVar[str]   # 子类必须设置，如 "daily_kline"

    # ── 抽象方法 ──────────────────────────────────────
    @abstractmethod
    def estimate_total(self, params: dict) -> int: ...

    @abstractmethod
    async def run(self, params: dict, on_unit_done: Callable[[UnitResult, str], None]) -> TaskSummary: ...

    # ── 默认钩子 ──────────────────────────────────────
    async def pre_execute(self, params: dict) -> None:
        """子类可覆盖：预热 fetcher 池 / 打开连接池"""
        pass

    async def post_execute(self, params: dict, summary: TaskSummary) -> None:
        """子类可覆盖：清理资源 / 关闭连接"""
        pass

    # ── framework 内部方法（子类勿调）──────────────────
    async def _update_progress(self, redis, task_id, label: str, result: UnitResult) -> None:
        """累加 success/fail/skip，写 Redis done++ / current=label"""
        ...

    async def _finish_task(self, session_factory, task_id, status, summary, message) -> None:
        """更新 sys_collect_tasks 行（status / success / fail / duration / message）"""
        ...
```

### 3.5 `execute_task()` 模板方法

```python
async def execute_task(
    task_id: int,
    handler: BaseCollectTask,
    params: dict,
) -> None:
    """模板方法本体：所有 task_type 走这一条流水线"""
    redis = await get_redis()
    start = time.time()
    summary = TaskSummary(success=0, fail=0)

    try:
        # ① 预热
        await handler.pre_execute(params)

        # ② 估单元数 → 写 Redis total
        total = handler.estimate_total(params)
        await redis.hset(f"collect:progress:{task_id}", "total", str(total))

        # ③ 业务主循环（cancel 检查放在 on_unit_done 里）
        async def on_unit_done(result: UnitResult, label: str) -> None:
            nonlocal summary
            if is_cancelled(task_id):
                raise Cancelled()
            summary = dataclasses.replace(
                summary,
                success=summary.success + (1 if result.success else 0),
                fail=summary.fail + (0 if result.success else 1),
                skip=summary.skip + (1 if result.skipped else 0),
            )
            await handler._update_progress(redis, task_id, label, result)

        summary = await handler.run(params, on_unit_done)

        # ④ 收尾
        elapsed = int((time.time() - start) * 1000)
        final_status = _decide_status(summary)
        await handler._finish_task(AsyncSessionLocal, task_id, final_status, summary, summary.message)
        await redis.hset(f"collect:progress:{task_id}", "status", final_status)

    except Cancelled:
        await handler._finish_task(AsyncSessionLocal, task_id, "cancelled", summary,
                                    message=f"已取消: 成功 {summary.success}, 失败 {summary.fail}")
        await redis.hset(f"collect:progress:{task_id}", "status", "cancelled")

    except Exception as e:
        logger.exception("采集任务 %d 异常终止", task_id)
        await handler._finish_task(AsyncSessionLocal, task_id, "failed", summary, message=str(e))
        await redis.hset(f"collect:progress:{task_id}", "status", "failed")

    finally:
        await handler.post_execute(params, summary)
```

**关键设计决策：**

| 决策 | 理由 |
|:---|:---|
| 取消检查放在 `on_unit_done` 内 | 子类 run() 不用关心取消；高频单元（K线按 symbol）天然有检查点 |
| 子类也可 raise `Cancelled()` | 给"无单元"任务（stock_basic 一次性 fetch）一个出口 |
| `summary` 在闭包内 `nonlocal` 修改 | 子类 run() 不必手工累加 success/fail，framework 帮它加 |
| `total_count` 由 estimate_total 写入 | 子类 run() 仍可在 TaskSummary 内覆盖真实数（用于 stock_basic 报告 synced_count） |
| `post_execute` 在 finally 内 | 即便异常也保证清理 |

---

## 四、注册表与执行器

### 4.1 `CollectTaskRegistry`（注意：与 `infrastructure/tasks/registry.py` 是两个东西）

```python
# backend/src/infrastructure/tasks/collect/registry.py

class CollectTaskRegistry:
    """task_type → BaseCollectTask 子类 实例 的字典"""

    def __init__(self):
        self._handlers: dict[str, BaseCollectTask] = {}

    def register(self, task_type: str, handler: BaseCollectTask) -> None:
        if task_type in self._handlers:
            raise ValueError(f"task_type {task_type} 已注册")
        if handler.name != task_type:
            raise ValueError(f"handler.name={handler.name} 与 task_type={task_type} 不一致")
        self._handlers[task_type] = handler
        logger.info("注册采集任务: %s", task_type)

    def get(self, task_type: str) -> BaseCollectTask | None:
        return self._handlers.get(task_type)

    def supported_types(self) -> list[str]:
        return list(self._handlers.keys())


_collect_registry: CollectTaskRegistry | None = None

def setup_collect_task_registry(handlers: list[BaseCollectTask]) -> None:
    """lifespan 启动时调用一次"""
    global _collect_registry
    _collect_registry = CollectTaskRegistry()
    for h in handlers:
        _collect_registry.register(h.name, h)

def get_collect_task_registry() -> CollectTaskRegistry:
    global _collect_registry
    if _collect_registry is None:
        raise RuntimeError("采集任务注册表未初始化，请先调用 setup_collect_task_registry")
    return _collect_registry
```

**为什么不返回工厂函数（`Callable[[], BaseCollectTask]`）？**

| 候选方案 | 理由 | 选择 |
|:---|---|:---|
| **dict 实例**（本次采用） | 4 个 task_type 全部无状态或 fetcher 池已做隔离；dict 查找比工厂调用快 ~100x，hot path 友好 | ✅ |
| 工厂函数 list | 看似更"动态"，但本场景无状态要求，反而徒增一层调用 | ❌ |
| 工厂 + 缓存 | 复杂度无收益 | ❌ |

### 4.2 lifespan 接入

```python
# main.py: lifespan()
from infrastructure.tasks.collect import (
    DailyKlineCollectTask, DailyBasicCollectTask,
    StockBasicCollectTask, ConceptCollectTask,
)
from infrastructure.tasks.collect.registry import setup_collect_task_registry

async def lifespan(app):
    # ... 既有迁移逻辑 ...
    setup_default_registry()

    # 🆕 注册采集任务
    setup_collect_task_registry([
        DailyKlineCollectTask(),
        DailyBasicCollectTask(),
        StockBasicCollectTask(),
        ConceptCollectTask(),
    ])

    yield
```

### 4.3 取消标志仍走模块级 set（兼容现状）

```python
# base.py 模块级
_cancel_flags: set[int] = set()

def request_cancel(task_id: int) -> None:
    _cancel_flags.add(task_id)

def is_cancelled(task_id: int) -> bool:
    return task_id in _cancel_flags

def clear_cancel(task_id: int) -> None:
    _cancel_flags.discard(task_id)
```

> 未来要做分布式取消，可在此处加 Redis SETNX；本阶段先兼容现状。

---

## 五、子类实现

### 5.1 `DailyKlineCollectTask` —— 迁移自 `collect_task.py:172-292`

```python
class DailyKlineCollectTask(BaseCollectTask):
    """日 K 线全量采集（按 symbol 维度单元）"""
    name = "daily_kline"

    def __init__(self):
        self._settings = get_settings()

    async def pre_execute(self, params: dict) -> None:
        """预热 fetcher 池：创建 N 个 KlineFetcher 实例"""
        self._concurrency = max(1, min(int(params.get("concurrency", self._settings.COLLECT_CONCURRENCY)),
                                         self._settings.COLLECT_MAX_CONCURRENCY))
        self._fetcher_pool: asyncio.Queue[KlineFetcher] = asyncio.Queue()
        for _ in range(self._concurrency):
            self._fetcher_pool.put_nowait(get_registry().create(KlineFetcher))

    async def post_execute(self, params: dict, summary: TaskSummary) -> None:
        # fetcher 池随 session 释放，Python GC 兜底即可
        pass

    def estimate_total(self, params: dict) -> int:
        """查 DB 拿 symbol 数（exchange 可选）"""
        async def _query() -> int:
            async with AsyncSessionLocal() as session:
                stmt = select(func.count()).select_from(StockInfoDB).where(StockInfoDB.list_status == "L")
                if params.get("exchange"):
                    stmt = stmt.where(StockInfoDB.exchange.in_(params["exchange"]))
                return (await session.execute(stmt)).scalar_one()
        return asyncio.get_event_loop().run_until_complete(_query())  # router 阶段同步调
        # ↑ router 阶段（同步）拿到 total 后再 background_tasks.add_task(execute_task, ...)
        # 因此 estimate_total 设计为同步方法

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        async with AsyncSessionLocal() as session:
            symbols = [r[0] for r in (await session.execute(
                select(StockInfoDB.symbol)
                .where(StockInfoDB.list_status == "L")
                .order_by(StockInfoDB.symbol)
            )).all()]

        sem = asyncio.Semaphore(self._concurrency)
        success = fail = 0

        async def _collect_one(symbol: str) -> UnitResult:
            async with sem:
                fetcher = await self._fetcher_pool.get()
                try:
                    async with AsyncSessionLocal() as session:
                        svc = KlineAppService(session=session)
                        await asyncio.wait_for(svc.collect(...), timeout=120)
                        await session.commit()
                    return UnitResult(success=True, detail=symbol)
                except asyncio.TimeoutError:
                    return UnitResult(success=False, detail=symbol, error=f"timeout 120s")
                except Exception as e:
                    return UnitResult(success=False, detail=symbol, error=str(e))
                finally:
                    await self._fetcher_pool.put(fetcher)

        chunk_size = self._settings.COLLECT_CHUNK_SIZE
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i+chunk_size]
            results = await asyncio.gather(*[_collect_one(s) for s in chunk])
            for r, label in zip(results, chunk):
                on_unit_done(r, label)
                if r.success: success += 1
                else: fail += 1

        return TaskSummary(success=success, fail=fail, total_count=len(symbols),
                           message=f"完成: 成功 {success}, 失败 {fail}")
```

> `estimate_total` 改为**同步方法**，由 router 在创建任务时同步调用（避免双 session 麻烦）；run() 内仍可独立查询真实数。

### 5.2 `DailyBasicCollectTask` —— 迁移自 `collect_task.py:294-352`

```python
class DailyBasicCollectTask(BaseCollectTask):
    """日频估值采集（按 trade_date 维度单元）"""
    name = "daily_basic"

    def estimate_total(self, params: dict) -> int:
        return len(self._resolve_dates(params))

    async def run(self, params, on_unit_done) -> TaskSummary:
        dates = self._resolve_dates(params)
        fetcher = get_registry().get(DailyBasicFetcher)
        success = fail = total_saved = 0

        for d in dates:
            try:
                bo_list = await asyncio.to_thread(fetcher.fetch_daily_basic, d)
                entities = [bo.to_entity() for bo in bo_list]
                async with AsyncSessionLocal() as session:
                    repo = FinDailyBasicRepoImpl(session)
                    saved = await repo.save_batch(entities)
                    await session.commit()
                total_saved += saved
                on_unit_done(UnitResult(success=True, detail=d, saved_count=saved), d)
                success += 1
            except Exception as e:
                on_unit_done(UnitResult(success=False, detail=d, error=str(e)), d)
                fail += 1

        return TaskSummary(success=success, fail=fail, total_count=len(dates),
                           message=f"完成: {success} 天, {total_saved} 条")
```

### 5.3 `StockBasicCollectTask` —— 迁移自 `collect_task.py:354-400`

```python
class StockBasicCollectTask(BaseCollectTask):
    """股票基本信息全量同步（无明确单元，total=1）"""
    name = "stock_basic"

    def estimate_total(self, params: dict) -> int:
        return 1

    async def run(self, params, on_unit_done) -> TaskSummary:
        try:
            fetcher = get_registry().get(StockBasicFetcher)
            async with AsyncSessionLocal() as session:
                svc = StockAppService(session=session)
                result = await svc.sync_stocks(fetcher, list_status=params.get("list_status", "L"))
                await session.commit()
            on_unit_done(UnitResult(success=True, detail="stock_basic", saved_count=result.synced_count), "stock_basic")
            return TaskSummary(success=1, fail=0, total_count=result.synced_count, message=result.message)
        except Exception as e:
            on_unit_done(UnitResult(success=False, detail="stock_basic", error=str(e)), "stock_basic")
            return TaskSummary(success=0, fail=1, message=str(e))
```

### 5.4 `ConceptCollectTask` —— 本次新增（重点）

```python
class ConceptCollectTask(BaseCollectTask):
    """概念全量同步（按概念名维度单元，复用 ConceptSyncOperation._sync_one）"""
    name = "concept"

    def estimate_total(self, params: dict) -> int:
        """先拉清单拿总数（同步调用，AKShare 0.3s 延迟 + retry < 5s）"""
        fetcher = AkShareConceptFetcher()
        return len(fetcher.fetch_concept_list())

    async def run(self, params, on_unit_done) -> TaskSummary:
        repo = ConceptRepoImpl(await _open_session())  # 独立 session 避免父 session prepared
        fetcher = AkShareConceptFetcher()
        operation = ConceptSyncOperation(repo=repo, fetcher=fetcher)

        concepts = fetcher.fetch_concept_list()
        success = fail = 0

        # ── 复用现有业务逻辑（不重写） ──
        for i, bo in enumerate(concepts):
            try:
                # 每个概念独立 session（参考 operation_dispatcher._run 的做法）
                async with AsyncSessionLocal() as session:
                    repo_i = ConceptRepoImpl(session)
                    operation_i = ConceptSyncOperation(repo=repo_i, fetcher=fetcher)
                    member_count = await operation_i._sync_one(bo)
                    await session.commit()
                on_unit_done(UnitResult(success=True, detail=bo.name, saved_count=member_count), bo.name)
                success += 1
            except Exception as e:
                on_unit_done(UnitResult(success=False, detail=bo.name, error=str(e)), bo.name)
                fail += 1

            if (i + 1) % 50 == 0:
                logger.info("概念同步进度: %d/%d", i + 1, len(concepts))

        return TaskSummary(success=success, fail=fail, total_count=len(concepts),
                           message=f"完成: 成功 {success} 概念, {sum(success * 1 for s in [None])} 成员")  # 实际 member 数由 UnitResult 累加
```

**关键约束：**
- `_sync_one()` 内部已处理 `upsert_concept` + `upsert_members` 两步，子类不动它
- 每个概念独立 session：避免一个失败回滚全部
- `ConceptAppService.sync_concepts()` 仍保留，作为「路由级同步」入口（同步返回 `ConceptSyncResultVO`）；本次新增的 `ConceptCollectTask` 用于「采集管理 tab」

---

## 六、Router 瘦身

### 6.1 重构前（468 行）

```
collect_task.py
├─ POST /tasks                  86 行（白名单 + 防重 + 写 DB + background_tasks）
├─ GET  /tasks                  20 行
├─ GET  /tasks/{id}              9 行
├─ GET  /tasks/{id}/progress    13 行
├─ POST /tasks/{id}/cancel      18 行
├─ _execute_task                14 行（handler dict）
├─ _collect_daily_kline        121 行
├─ _collect_daily_basic         62 行
├─ _collect_stock_basic         45 行
├─ _finish_task                 19 行
└─ _task_to_dict                14 行
```

### 6.2 重构后（~150 行）

```python
@router.post("/tasks", summary="创建采集任务")
async def create_task(
    body: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    task_type = body.get("task_type")
    params = body.get("params", {})
    registry = get_collect_task_registry()

    handler = registry.get(task_type)
    if handler is None:
        return R.ok({"message": f"不支持的任务类型: {task_type}，已支持: {registry.supported_types()}"})

    # 防重
    running = await db.execute(
        select(SysCollectTaskDB).where(
            SysCollectTaskDB.task_type == task_type,
            SysCollectTaskDB.status == "running",
        )
    )
    if running.scalars().first():
        return R.ok({"message": f"{task_type} 已有运行中的任务"})

    # estimate_total（同步方法，DB IO 在 router 阶段完成）
    total = handler.estimate_total(params)

    # 写 sys_collect_tasks
    task = SysCollectTaskDB(task_type=task_type, trigger_type="manual",
                             params=params, status="running",
                             total_count=total, started_at=datetime.now())
    db.add(task)
    await db.commit()
    task_id = task.id

    # 写 Redis 初始进度
    redis = await get_redis()
    await redis.hset(f"collect:progress:{task_id}", mapping={
        "total": str(total), "done": "0", "success": "0",
        "fail": "0", "skip": "0", "status": "running", "current": "",
    })
    await redis.expire(f"collect:progress:{task_id}", 86400)

    # 启动后台任务
    background_tasks.add_task(execute_task, task_id, handler, params)

    return R.ok({
        "task_id": task_id,
        "task_type": task_type,
        "total_count": total,
        "message": f"已启动 {task_type} 采集任务，共 {total} 个单元",
    })
```

**其他 4 个 endpoint（list_tasks / get_task / get_task_progress / cancel_task）保持不动，只把 `_cancel_flags.add()` 改成 `request_cancel()`，调 `infrastructure.tasks.collect.base` 的公共函数。**

### 6.3 收益

| 指标 | 重构前 | 重构后 |
|:---|---:|---:|
| `collect_task.py` 行数 | 468 | ~150 |
| 新增 task_type 需要改动的文件 | 2（router + handler dict） | 1（仅 `collect/` 目录新增子类 + lifespan 注册） |
| 样板代码占比（进度/取消/收尾） | ~60% | ~10%（仅在基类） |
| 概念同步在采集管理 tab 可见性 | ❌ 不可见 | ✅ 可见、可取消、可追溯 |

---

## 七、与现状的对比与收益

### 7.1 改造前后对比

| 维度 | 改造前 | 改造后 |
|:---|:---|:---|
| **任务定义位置** | `collect_task.py` 内私有函数 | `infrastructure/tasks/collect/*.py` 独立文件 |
| **路由白名单** | 硬编码 tuple `("daily_kline","daily_basic","stock_basic")` | 从 registry 动态读 |
| **进度更新样板** | 每个 handler 内嵌 `redis.hset(...)` | 基类 `_update_progress()` 统一处理 |
| **取消检查样板** | 每个 handler 内嵌 `if task_id in _cancel_flags` | 基类 `on_unit_done` 闭包统一检查 |
| **DB 收尾样板** | 每个 handler 调用 `_finish_task()` | 基类 `_finish_task()` 统一调用 |
| **业务/框架耦合度** | 高（业务代码里散落 redis / DB / 取消标志） | 低（业务代码只关心 unit + result） |
| **可测试性** | 难（handler 是 router 内部函数，无法单独 mock） | 易（BaseCollectTask 子类可直接 unit test） |
| **概念同步接入** | 不在采集管理 tab | 新增 `ConceptCollectTask` 一行 |

### 7.2 不动的部分（兼容性保证）

| 不动 | 原因 |
|:---|:---|
| `sys_collect_tasks` / `sys_collect_task_details` 表结构 | 前端 / 既有接口依赖 |
| Redis hash key 与字段名 | `get_task_progress()` 接口契约 |
| HTTP 路径与请求/响应字段 | 既有前端 `DataCollect.vue` 不动 |
| `infrastructure/tasks/registry.py`（asyncio.Task 注册表） | 是另一套机制（池操作 `PoolOperation` 用），不应混入 |
| `ConceptAppService.sync_concepts()` | 仍走"路由级同步"路径（同步返回 VO），给 `/concepts/sync` 用 |

---

## 八、实施步骤

> 建议按以下顺序推进，每步可独立验证：

### Step 1：搭骨架（不动现有 handler）

- 新增 `infrastructure/tasks/collect/__init__.py` / `base.py` / `registry.py`
- `main.py` lifespan 调用 `setup_collect_task_registry([])` 空注册
- router 暂时仍走内嵌 handler

✅ 验证：`uvicorn main:app` 启动无报错，4 个采集 endpoint 行为不变

### Step 2：写 `ConceptCollectTask` + 接入（本次核心交付）

- 新增 `infrastructure/tasks/collect/concept.py`
- lifespan 注册 4 个 handler（含 3 个占位：先 return estimate_total=0, run 空实现）
- router 切换为 registry 模式
- 前端 `data-collect/` 增补「概念同步」卡片（参考现有 `CollectPanel.vue`）

✅ 验证：采集管理 tab 能触发概念同步，进度条从 0 → 100，可取消

### Step 3：迁移 `StockBasicCollectTask`（最简单的）

- 新增 `infrastructure/tasks/collect/stock_basic.py`
- router 注册替换（lifespan 多一行）
- 删除 `collect_task.py` 内 `_collect_stock_basic` 函数

✅ 验证：股票基本信息同步行为一致

### Step 4：迁移 `DailyBasicCollectTask` + `DailyKlineCollectTask`

- 新增 `infrastructure/tasks/collect/daily_basic.py` / `daily_kline.py`
- 删除 `collect_task.py` 内 `_collect_daily_basic` / `_collect_daily_kline` 函数
- 删 `_finish_task` / `_execute_task` / `_cancel_flags` 模块级样板

✅ 验证：3 个 task_type 全部行为一致；`collect_task.py` 降到 ~150 行

### Step 5：前端补「概念同步」卡片（可选，可后置）

- `frontend/src/views/data-collect/components/CollectPanel.vue` 新增 concept 配置项
- `frontend/src/views/data-collect/api.ts` 加 `task_type: 'concept'` 提交参数

### Step 6：清理

- `collect_task.py` 仅保留 5 个 HTTP endpoint + `_task_to_dict`
- 全文搜索 `from infrastructure.tasks.collect` import 收敛

---

## 九、风险与对策

| 风险 | 概率 | 影响 | 对策 |
|:---|:---:|:---:|:---|
| `estimate_total` 改为同步方法后，AKShare 拉清单慢 | 中 | router 响应慢 1~5s | 加 timeout + 缓存（首次写库，二次走 Redis） |
| 子类误把异常逃出 `run()` | 低 | 任务卡死 | framework 在 `execute_task` 顶层 try/except，强制写 failed |
| `_cancel_flags` 模块级变量多进程失效 | 中 | 取消信号丢 | 当前单进程够用；下一步升级 Redis SETNX |
| `concept.py` 路由级同步与采集管理并行跑同一 fetcher | 低 | AKShare 接口限流 | AKShare fetcher 已内置 REQUEST_DELAY=0.3s，足够 |

---

## 十、附录

### 10.1 用例序列图（概念同步走通全链路）

```
用户            前端             Router          Registry       ConceptCollectTask     AKShare       ConceptRepo       PostgreSQL    Redis
 │                │                 │                │                  │                  │               │                │           │
 │ 点击「概念同步」│                 │                │                  │                  │               │                │           │
 │───────────────>│                 │                │                  │                  │               │                │           │
 │                │ POST /tasks     │                │                  │                  │               │                │           │
 │                │ {task_type:concept}                │                  │                  │               │                │           │
 │                │────────────────>│                │                  │                  │               │                │           │
 │                │                 │ get(handler)   │                  │                  │               │                │           │
 │                │                 │───────────────>│                  │                  │               │                │           │
 │                │                 │ ConceptCollectTask               │                  │               │                │           │
 │                │                 │<─ ─ ─ ─ ─ ─ ─ ─│                  │                  │               │                │           │
 │                │                 │ estimate_total()                  │                  │               │                │           │
 │                │                 │───────────────────────────────>│                  │               │                │           │
 │                │                 │                                  │ fetch_concept_list()              │               │                │
 │                │                 │                                  │─────────────────>│               │                │           │
 │                │                 │                                  │<─ ─ ─ ─ ─ ─ ─ ──│               │                │           │
 │                │                 │                                  │ N=423            │               │                │           │
 │                │                 │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│                  │               │                │           │
 │                │                 │ 写 sys_collect_tasks + Redis total=423             │               │                │           │
 │                │                 │────────────────────────────────────────────────────────────────────────────────>│           │
 │                │                 │                 │                │ background_tasks.add_task(execute_task,...)   │           │
 │                │ {task_id, total}│                │                  │                  │               │                │           │
 │                │<─ ─ ─ ─ ─ ─ ─ ─│                │                  │                  │               │                │           │
 │                │ 轮询 GET /progress                │                  │                  │               │                │           │
 │                │─────────────────────────────────────────────────────── 异步执行 run() ──────────────────────────────────│           │
 │                │                 │                 │                  │ for concept in list:              │               │                │
 │                │                 │                 │                  │   _sync_one(bo)                   │               │                │
 │                │                 │                 │                  │─────────────────>│               │                │           │
 │                │                 │                 │                  │<─ ─ ─ ─ ─ ─ ─ ──│               │                │           │
 │                │                 │                 │                  │ upsert_concept + members          │               │                │           │
 │                │                 │                 │                  │────────────────────────────────>│                │           │
 │                │                 │                 │                  │ on_unit_done(UnitResult, name)    │               │                │           │
 │                │                 │                 │                  │──────────────────────────────────────────→ progress++│           │
 │                │ GET /progress    │                │                  │                  │               │                │           │
 │                │────────────────>│ HGETALL collect:progress:{task_id}│                  │               │                │           │
 │                │ {done: 100, success: 99, fail: 1, current: "中字头"}               │               │                │           │
 │                │<─ ─ ─ ─ ─ ─ ─ ─│                │                  │                  │               │                │           │
 │ ... 423 单元跑完 ...            │                 │                  │ return TaskSummary               │               │                │           │
 │                │                 │                 │                  │ _finish_task(status=success)       │               │                │           │
 │                │                 │                 │                  │────────────────────────────────>│                │           │
 │                │ GET /progress    │                │                  │                  │               │                │           │
 │                │ {status: success, done: 423, percent: 100}            │               │                │           │
 │                │<─ ─ ─ ─ ─ ─ ─ ─│                │                  │                  │               │                │           │
```

### 10.2 关键文件清单（重构后）

| 文件 | 行数（估） | 性质 |
|:---|---:|:---|
| `infrastructure/tasks/collect/__init__.py` | 10 | 重导出 |
| `infrastructure/tasks/collect/base.py` | ~180 | 模板方法 + UnitResult + TaskSummary + execute_task |
| `infrastructure/tasks/collect/registry.py` | ~60 | CollectTaskRegistry + setup/get |
| `infrastructure/tasks/collect/daily_kline.py` | ~120 | DailyKlineCollectTask |
| `infrastructure/tasks/collect/daily_basic.py` | ~70 | DailyBasicCollectTask |
| `infrastructure/tasks/collect/stock_basic.py` | ~50 | StockBasicCollectTask |
| `infrastructure/tasks/collect/concept.py` | ~80 | ConceptCollectTask（本次重点） |
| `route/api/v1/collect_task.py` | ~150 | 5 个 endpoint，零业务逻辑 |
| `main.py` lifespan 改动 | +5 | `setup_collect_task_registry([...])` |

合计净增约 420 行（其中 ~180 是通用基类，其余是业务迁移），但换来：
- 概念同步在采集管理 tab 跑通（本次核心需求）
- 4 个 task_type 行为统一、可测、可扩展
- router 从 468 行降到 150 行
