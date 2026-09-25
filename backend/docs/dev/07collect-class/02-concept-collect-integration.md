# 02 — 概念采集接入采集管理：专项集成方案

> 配套文档：本文聚焦「概念同步如何接入现有采集管理框架」
> 总览设计：`docs/dev/07collect-class/01-collect-task-class-design.md`
> 配套 UML：`docs/PlantUML/CollectTask/02-hierarchy.puml`（基类与子类关系）
> 总览 UML：`docs/PlantUML/CollectTask/01-class.puml`
> 概念原设计：`docs/dev/06gainian/02-infrastructure-design.md §5` + `docs/dev/06gainian/03-application-and-route-design.md §3.1`

---

## 一、为什么需要专项方案

概念采集在 2026-09 已落地（见 `06gainian/` 一整套设计），但**当前没有走采集管理 tab**：

```
现状路径：
用户 → /concepts/sync → ConceptRouter → ConceptAppService.sync_concepts()
                                        └→ ConceptSyncOperation.sync_all()  ← "伪后台"（同步阻塞）

缺失能力：
· 采集管理 tab 看不到「概念同步」入口
· 没有 task_id → 无法轮询进度
· 没有 cancel 接口 → 中途出错只能等跑完
· 历史记录散落在 ConceptEntity.last_synced_at，无 sys_collect_tasks 行
```

**目标**：复用 `01-collect-task-class-design.md` 的 `BaseCollectTask` 框架，零业务改动接入概念同步。

---

## 二、设计原则（与原方案保持一致）

| 原则 | 落地动作 |
|:---|:---|
| **框架负责通用，子类负责业务** | `execute_task()` 模板方法接管进度/取消/收尾；子类只实现 `run()` |
| **业务代码零重写** | 复用 `ConceptSyncOperation._sync_one()`，新子类只做编排 |
| **每单元独立 session** | 避免一个概念失败回滚全部（参考 `operation_dispatcher.py:60-80`） |
| **路由级同步入口保留** | `ConceptAppService.sync_concepts()` 不动，作为快速同步保留接口 |

---

## 三、概念采集接入的关键决策

### 3.1 决策 1：复用 `_sync_one()` 而不是重写

| 候选 | 评估 | 选择 |
|:---|:---|:---:|
| **A. 直接复用 `_sync_one()`** | 业务逻辑零回归；新增子类只承担"循环 + 上报"职责 | ✅ |
| B. 在新子类里重写 upsert | 违反 DRY；未来 `_sync_one` 改动需要双修 | ❌ |
| C. 把 `_sync_one` 提到公共方法 | 范围太大，影响 `ConceptAppService` 接口 | ❌ |

**复用方式**（伪代码）：

```python
class ConceptCollectTask(BaseCollectTask):
    async def run(self, params, on_unit_done):
        fetcher = AkShareConceptFetcher()
        concepts = fetcher.fetch_concept_list()    # AKShare 同步拉清单
        
        for bo in concepts:
            async with AsyncSessionLocal() as session:    # 每概念独立 session
                repo_i = ConceptRepoImpl(session)
                op_i = ConceptSyncOperation(repo=repo_i, fetcher=fetcher)
                member_count = await op_i._sync_one(bo)
                await session.commit()
            on_unit_done(UnitResult(success=True, detail=bo.name,
                                    saved_count=member_count), bo.name)
```

### 3.2 决策 2：每概念独立 session（而非长事务）

| 候选 | 评估 | 选择 |
|:---|:---|:---:|
| **A. 每概念独立 session** | 单点失败不影响其他；事务短锁少 | ✅ |
| B. 一个长事务包全部 423 个概念 | 长事务锁表 + 失败全回滚风险 | ❌ |
| C. 批量（50 个一组）事务 | 中间方案；但 partial commit 逻辑复杂 | ❌ |

> 现状 `ConceptSyncOperation.sync_all()` 共用一个 `_repo`，需要在新子类里改用"每单元新建 repo + session"模式 —— 这正是 `OperationDispatcher._run()` 已验证过的模式。

### 3.3 决策 3：`estimate_total` 走同步 AKShare 调用

| 候选 | 评估 | 选择 |
|:---|:---|:---:|
| **A. 同步拉清单拿总数** | 复用 fetcher；零额外代码；延迟 0.3s × retry < 5s 可接受 | ✅ |
| B. 异步预热缓存 | 复杂；首次采集必阻塞 | ❌ |
| C. 总数硬编码（取上次 sync 的 total） | 不准确；新入概念会漏 | ❌ |

> **风险**：AKShare 偶发 5xx 重试可能让 router 端慢 5s。后续可加 Redis 缓存（key=`concept:list:em:meta`，TTL=10min）做 fallback，**当前阶段先兼容现状**。

### 3.4 决策 4：与 `ConceptAppService.sync_concepts()` 并存

| 入口 | 场景 | 行为 |
|:---|:---|:---|
| `POST /concepts/sync`（既有） | 路由级快速同步，**同步返回 VO** | 由用户感知完成；不进 sys_collect_tasks |
| `POST /collect/tasks {task_type: 'concept'}`（新增） | 采集管理 tab 异步触发，**返回 task_id** | 进入 sys_collect_tasks；可轮询进度、可取消 |

**为什么并存？**
- `/concepts/sync` 是「一次性触发」语义（同步返回结果），适合脚本/调试
- 采集管理 tab 是「任务管理」语义（异步 + 进度 + 取消），适合 UI 触发

两者共用 `ConceptSyncOperation._sync_one()`，业务层零分叉。

---

## 四、采集管理类继承层次总览

> 完整类图：`docs/PlantUML/CollectTask/02-hierarchy.puml`

```
                    ┌──────────────────────────────────┐
                    │   <<abstract>> BaseCollectTask   │
                    │ ─────────────────────────────────│
                    │ + name : ClassVar[str]           │
                    │ ─────────────────────────────────│
                    │ + estimate_total(params) : int   │
                    │ + run(params, on_unit_done) : TS │
                    │ + pre_execute(params)            │
                    │ + post_execute(params, summary)  │
                    │ - _update_progress(...)          │
                    │ - _finish_task(...)              │
                    │ + execute_task(...) [static]     │
                    └────────────┬─────────────────────┘
                                 │
        ┌────────────────────────┼─────────────────────────┐
        │                        │                         │
        ▼                        ▼                         ▼
┌───────────────────┐  ┌───────────────────┐  ┌──────────────────────┐
│ DailyKlineCollect │  │ DailyBasicCollect │  │ StockBasicCollect    │
│ name="daily_kline"│  │ name="daily_basic"│  │ name="stock_basic"   │
│ ─────────────────│  │ ─────────────────│  │ ─────────────────────│
│ 单元: 每 symbol   │  │ 单元: 每 trade_date│ │ 单元: 仅 1 个 (整体)  │
│ 并发: N 个 fetcher│  │ 顺序: 按日期      │  │ 一次性 fetch+upsert   │
│ 迁移自: 172-292  │  │ 迁移自: 294-352   │  │ 迁移自: 354-400       │
└───────────────────┘  └───────────────────┘  └──────────────────────┘

                                 ┌──────────────────────┐
                                 │ <<NEW>>              │
                                 │ ConceptCollectTask   │
                                 │ name="concept"       │
                                 │ ─────────────────────│
                                 │ 单元: 每个概念名      │
                                 │ 复用: _sync_one()    │
                                 │ session: 每概念独立   │
                                 └──────────────────────┘
```

**4 个子类的"单元"语义对比：**

| 子类 | 单元维度 | 单元数 | 并发模型 | 失败策略 |
|:---|:---|---:|:---|:---|
| `DailyKlineCollectTask` | symbol | ~5000 | `Semaphore(N)` + `Queue` 池 | 单元失败 → 累计 fail，不中断 |
| `DailyBasicCollectTask` | trade_date | ~1~7 | 顺序循环 | 单元失败 → 累计 fail，不中断 |
| `StockBasicCollectTask` | 整体 | 1 | 单次 | 失败 → 直接 failed |
| `ConceptCollectTask` | concept_name | ~423 | 顺序循环（AKShare 限频） | 单元失败 → 累计 fail，不中断 |

---

## 五、ConceptCollectTask 实现要点

### 5.1 完整代码（约 80 行）

```python
# backend/src/infrastructure/tasks/collect/concept.py
from __future__ import annotations
import logging
from typing import Callable

from infrastructure.tasks.collect.base import (
    BaseCollectTask, UnitResult, TaskSummary, Cancelled,
)
from infrastructure.tasks.collect.registry import request_cancel, is_cancelled
from infrastructure.collectors.akshare.fetcher import AkShareConceptFetcher
from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.repositories.concept_repository import ConceptRepoImpl
from infrastructure.tasks.concept_sync_operation import ConceptSyncOperation

logger = logging.getLogger(__name__)


class ConceptCollectTask(BaseCollectTask):
    """概念全量同步（采集管理 tab 用）"""
    name = "concept"

    def __init__(self):
        self._fetcher = AkShareConceptFetcher()

    def estimate_total(self, params: dict) -> int:
        """同步拉清单拿总数（AKShare 0.3s 延迟 + retry < 5s）"""
        return len(self._fetcher.fetch_concept_list())

    async def run(
        self,
        params: dict,
        on_unit_done: Callable[[UnitResult, str], None],
    ) -> TaskSummary:
        """逐概念同步，单元 = 每个概念"""
        concepts = self._fetcher.fetch_concept_list()
        total = len(concepts)
        success = fail = 0

        for i, bo in enumerate(concepts):
            # ── 取消检查（低频检查点，每单元一次）──
            if is_cancelled(self._current_task_id()):
                raise Cancelled()

            try:
                # ── 每概念独立 session ──
                async with AsyncSessionLocal() as session:
                    repo_i = ConceptRepoImpl(session)
                    op_i = ConceptSyncOperation(repo=repo_i, fetcher=self._fetcher)
                    member_count = await op_i._sync_one(bo)
                    await session.commit()

                on_unit_done(
                    UnitResult(success=True, detail=bo.name,
                               saved_count=member_count),
                    bo.name,
                )
                success += 1
            except Cancelled:
                raise
            except Exception as e:
                logger.warning("概念 %s 同步失败: %s", bo.name, e)
                on_unit_done(
                    UnitResult(success=False, detail=bo.name, error=str(e)),
                    bo.name,
                )
                fail += 1

            if (i + 1) % 50 == 0:
                logger.info("概念同步进度: %d/%d", i + 1, total)

        return TaskSummary(
            success=success, fail=fail, total_count=total,
            message=f"完成: 成功 {success} 概念, 失败 {fail}",
        )

    def _current_task_id(self) -> int:
        """子类 run() 内需要用 task_id 做取消检查"""
        # 由 execute_task() 模板方法通过 self._task_id 注入
        # 当前通过闭包传入；下文 §5.2 有改进方案
        return getattr(self, "_task_id", -1)
```

### 5.2 改进点：取消检查的 task_id 注入

`run()` 签名只接受 `params` 和 `on_unit_done`，**没有 task_id**。需要在 `BaseCollectTask` 上做小幅扩展：

**方案 A（推荐）**：`on_unit_done` 改为 BoundMethod，子类调 `self.on_unit_done(...)`，基类在 `execute_task()` 内 monkey-patch 注入 task_id：

```python
# base.py
async def execute_task(task_id, handler, params):
    handler._task_id = task_id           # 注入
    handler.on_unit_done = handler._make_on_unit_done(task_id)
    ...

def _make_on_unit_done(self, task_id):
    async def on_unit_done(result, label):
        if is_cancelled(task_id):
            raise Cancelled()
        await self._update_progress(...)
    return on_unit_done
```

**方案 B（最小改动）**：把 `task_id` 作为 `params` 字段传入（但污染 params 命名空间）。

→ **采用方案 A**：基类扩展 5 行，子类 `self._task_id` 直接可用。

### 5.3 与既有路径的对比

| 维度 | 既有 `sync_concepts()` | 新 `ConceptCollectTask.run()` |
|:---|:---|:---|
| **session 模型** | 共用一个 `_repo`，整个 `sync_all` 在 1 个 session 上 | 每概念独立 session |
| **取消能力** | ❌ 无 | ✅ 基类 `Cancelled` 支持 |
| **进度上报** | 仅 logger（无结构化） | ✅ `_update_progress` → Redis + sys_collect_task |
| **历史记录** | ❌ 仅 `concepts.last_synced_at` | ✅ sys_collect_tasks 行（含 success/fail/duration） |
| **业务逻辑** | `sync_all` 内联 | 委托 `_sync_one()`，**零改动** |

---

## 六、注册 & 接入步骤

### Step 1：在 `lifespan` 注册（3 行）

```python
# backend/src/main.py
from infrastructure.tasks.collect import (
    DailyKlineCollectTask, DailyBasicCollectTask,
    StockBasicCollectTask, ConceptCollectTask,
)
from infrastructure.tasks.collect.registry import setup_collect_task_registry

async def lifespan(app):
    # ... 既有迁移 ...
    setup_collect_task_registry([
        DailyKlineCollectTask(),
        DailyBasicCollectTask(),
        StockBasicCollectTask(),
        ConceptCollectTask(),         # 🆕 概念接入
    ])
    yield
```

### Step 2：Router 白名单从硬编码改为读 registry

```python
# collect_task.py: create_task()
- if task_type not in ("daily_kline", "daily_basic", "stock_basic"):
-     return R.ok({"message": f"不支持的任务类型: {task_type}"})
+ registry = get_collect_task_registry()
+ if registry.get(task_type) is None:
+     return R.ok({"message": f"不支持的任务类型: {task_type}，已支持: {registry.supported_types()}"})
+ handler = registry.get(task_type)
```

### Step 3：前端增补概念同步卡片

`frontend/src/views/data-collect/components/CollectPanel.vue` 新增一项：

```vue
<el-card class="task-card" shadow="hover">
    <template #header>概念同步</template>
    <el-form-item label="数据源">
      <el-select v-model="form.concept.source">
        <el-option label="东方财富 (em)" value="em" />
      </el-select>
    </el-form-item>
    <el-form-item label="强制重传">
      <el-switch v-model="form.concept.forceResync" />
    </el-form-item>
    <el-button type="primary" :loading="loading"
               @click="submit('concept', form.concept)">开始同步</el-button>
  </el-card>
```

→ **零业务改动**：复用现有 `TaskProgress.vue` 轮询 `/collect/tasks/{id}/progress`。

---

## 七、风险与回退

| 风险 | 概率 | 影响 | 对策 | 回退方案 |
|:---|:---:|:---|:---|:---|
| AKShare 拉清单超时导致 `estimate_total` 慢 | 中 | router 端延迟 1~5s | 当前可接受；后续 Redis 缓存 fallback | 手动改 router 端 `total=423` 硬编码 |
| 子类误把异常逃出 `run()` | 低 | 任务卡死 | 基类顶层 try/except | 已设计强制 failed |
| AKShare 与既有 `sync_concepts()` 并行触发，触发限流 | 低 | 部分概念失败 | AKShare 内置 `REQUEST_DELAY=0.3s`；两边串行可缓解 | 在 fetcher 加 `threading.Lock()` |
| `_sync_one()` 内部 session 生命周期假设破坏 | 低 | 概念失败率升高 | 新子类已经按"每概念独立 session"重写 | 保留 `ConceptSyncOperation.sync_all()` 不动，旧路径仍可用 |

---

## 八、验收标准

✅ 单元级：
- `python -m pytest backend/tests/infrastructure/tasks/collect/test_concept.py`
  - `test_estimate_total_returns_count`：mock fetcher 返回 5 个概念，断言 == 5
  - `test_run_calls_sync_one_per_concept`：mock `_sync_one`，断言调用 5 次
  - `test_run_raises_cancelled_when_flag_set`：mock `is_cancelled=True`，断言抛 `Cancelled`

✅ 集成级：
- `POST /collect/tasks {task_type:"concept"}` → 返回 `task_id` + `total_count: 423`
- `GET /collect/tasks/{id}/progress` → 每 3s 看到 `done++`、`current` 切换
- `POST /collect/tasks/{id}/cancel` → 下一个单元前抛 `Cancelled`，status=cancelled
- `sys_collect_tasks` 新增一行，status=success/cancelled/failed

✅ 兼容性：
- `POST /concepts/sync`（既有路径）行为不变
- `GET /concepts/`、`GET /concepts/{name}` 等查询接口行为不变

---

## 九、文件清单（新增）

| 文件 | 估行数 | 性质 |
|:---|---:|:---|
| `infrastructure/tasks/collect/__init__.py` | 10 | 重导出 |
| `infrastructure/tasks/collect/base.py` | ~190 | 模板方法 + 数据类 + execute_task |
| `infrastructure/tasks/collect/registry.py` | ~60 | CollectTaskRegistry |
| `infrastructure/tasks/collect/concept.py` | ~80 | **本次重点** |
| `main.py` lifespan | +5 | 注册 4 个 handler |
| `route/api/v1/collect_task.py` | 468 → ~150 | router 瘦身 |
| `frontend/.../CollectPanel.vue` | +30 | 概念同步卡片 |

合计净增 ~375 行，换来：
- 4 个 task_type 行为统一（包含新增 concept）
- 概念同步在采集管理 tab 跑通（进度 + 取消 + 历史）
- router 行数 -68%
- 后续新增 task_type 改动从 2 文件 → 1 文件