# infrastructure/ 基础设施层分析

> 关联：[`00-总览与建议清单.md`](00-总览与建议清单.md) · [`../config/DDD.md` §2.4](../../config/DDD.md)

---

## 1. 当前文件清单（共 79 个）

```
backend/src/infrastructure/
├── __init__.py               （空）
├── adapter/                  ← ACL 防腐层（对内：实现 application/port；对内：封装外部 SDK）
│   ├── __init__.py           ← 重导出 collector_port + registry
│   ├── base.py               ← 旧占位（已无用）
│   ├── fetcher/              ← 数据源采集器实现（与 application/port/ 对应）
│   │   ├── __init__.py      ← 重导出所有 fetcher + parser
│   │   ├── base.py          ← BaseCollector 基类（logger/source_name）
│   │   ├── tushare.py       ← KlineFetcher/StockBasicFetcher/DailyBasicFetcher/FinReportFetcher
│   │   ├── pytdx.py         ← MinuteKlineFetcher
│   │   └── adata.py          ← ConceptFetcher（Adata 同花顺）
│   ├── realtime/             ← 实时查询（按需请求 + Redis 缓存，不入库）
│   │   ├── __init__.py
│   │   ├── base.py          ← BaseRealtimeQuery（协议基类）
│   │   ├── framework.py      ← RealtimeQueryFramework（缓存/单飞/限流/降级）
│   │   ├── registry.py       ← RealtimeQueryRegistry + setup_realtime_registry
│   │   ├── concept_minute.py ← ConceptMinuteQuery
│   │   └── stock_minute_kline.py ← StockMinuteKlineQuery
│   ├── scheduler/            ← 批量采集调度（后台任务 + APScheduler）
│   │   ├── __init__.py
│   │   ├── registry.py       ← TaskRegistry（asyncio.Task 生命周期管理）
│   │   ├── collect_scheduler.py ← CollectScheduler（APScheduler 定时调度）
│   │   ├── operation_dispatcher.py ← OperationDispatcher（池操作后台任务派发）
│   │   └── collect/         ← 采集任务框架 + 子类实现
│   │       ├── __init__.py  ← 重导出所有子类 + BaseCollectTask
│   │       ├── base.py      ← BaseCollectTask + execute_task 模板方法
│   │       ├── registry.py  ← CollectTaskRegistry + TaskDef/FacetGroup
│   │       ├── daily_kline.py
│   │       ├── daily_basic.py
│   │       ├── stock_basic.py
│   │       ├── fin_report.py
│   │       ├── concept.py    ← ConceptList/Membership/IndexTHCollectTask
│   │       └── planned.py   ← PlannedCollectTask × 14（占位任务）
│   └── cache/
│       └── redis_client.py  ← Redis 异步客户端（get_redis）
├── persistence/              ← 持久化层（ORM + Repository 实现）
│   ├── __init__.py          （空）
│   ├── base.py             ← SQLAlchemy DeclarativeBase
│   ├── mixins.py           ← TimestampMixin
│   ├── connection.py        ← AsyncSessionLocal + get_db + run_async
│   ├── models/             ← ORM 模型（与 domain/entitys/ 一对一）
│   │   ├── __init__.py     ← 重导出全部 23 个 DB 模型
│   │   ├── stock_info.py
│   │   ├── tech_kline.py
│   │   ├── pool.py
│   │   ├── concept.py
│   │   ├── fin_report.py
│   │   ├── fin_daily_basic.py
│   │   ├── collect_config.py
│   │   ├── sys_collect_task.py
│   │   └── [15 个 cap_*/fin_*/base_*/mkt_*/*.py]
│   └── repositories/         ← Repository 实现（与 domain/entitys/*/repository.py 一对一）
│       ├── __init__.py      （空）
│       ├── stock_repository.py
│       ├── kline_repository.py
│       ├── pool_repository.py
│       ├── pool_operation_repository.py
│       ├── panel_compose_repository.py
│       ├── concept_repository.py
│       └── [3 个 fin_*_repository.py]
└── config/                ← 应用配置 + DI 工厂
    ├── __init__.py         ← get_settings + PEP 562 按需加载 di
    ├── settings.py         ← pydantic-settings.Settings
    └── di.py               ← FastAPI Depends 工厂（get_kline_app_service / get_panel_app_service / ...）
```

---

## 2. adapter/ 各子模块职责分析

### 2.1 `adapter/fetcher/`（数据源适配）

**职责**：封装外部 SDK（Tushare / Pytdx / Adata），实现 `application/port/collector_port.py` 定义的 Protocol。

**现状**：
- `tushare.py`：实现 4 类 fetcher（KlineFetcher / StockBasicFetcher / DailyBasicFetcher / FinReportFetcher）
- `pytdx.py`：实现 MinuteKlineFetcher
- `adata.py`：实现 ConceptFetcher

**评价**：✅ **正确**。协议（`collector_port`）与实现（`fetcher/`）分离，新增数据源只需新增一个 fetcher 类 + 在 `setup_default_registry()` 注册。

⚠️ **问题**：`infrastructure/adapter/__init__.py:1` 写的是"采集器模块（ACL 防腐层）"，但同时 `base.py` 是空占位文件（`Error: File not found` 表明可能已删除但 git 未更新）。

### 2.2 `adapter/realtime/`（实时查询）

**职责**：页面当前要看的按需请求数据，结果只写 Redis、不入库。

**子模块**：
- `framework.py`：技术框架（缓存 GET/SET、单飞锁、Semaphore 限流、超时、降级、统计），**不持有任何业务逻辑**。
- `base.py`：`BaseRealtimeQuery` 协议（`cache_key/fetch/fallback/normalize`）
- `concept_minute.py` / `stock_minute_kline.py`：具体实现

**评价**：✅ **正确**。技术框架必须在 infrastructure 层。

⚠️ **争议点**：`base.py` 的 `facet`/`sub_facet`/`label`/`sort_order` 等 ClassVar 是"采集管理目录树的 UI 元数据"，与 DDD 无关。但放在 infrastructure 层是可以接受的（因为这是"采集管理"这个横切关注点的展示数据，不是业务规则）。

### 2.3 `adapter/scheduler/`（批量采集）

**职责**：后台批量采集任务（模板方法 + APScheduler 定时）。

**子模块**：
- `collect/base.py`：`BaseCollectTask` 抽象基类 + `execute_task` 模板方法——纯技术框架
- `collect/daily_kline.py`：日 K 线采集子类
- `collect/daily_basic.py`：日频估值子类
- `collect/stock_basic.py`：股票清单子类
- `collect/fin_report.py`：利润表子类
- `collect/concept.py`：概念（3 个子类）
- `collect/planned.py`：14 个占位任务
- `collect/registry.py`：`CollectTaskRegistry`（注册表 + catalog）
- `collect_scheduler.py`：APScheduler 定时调度
- `operation_dispatcher.py`：池操作后台任务派发
- `registry.py`：`TaskRegistry`（asyncio.Task 生命周期）

**评价**：✅ **正确**。批量采集调度是典型的基础设施职责。

⚠️ **`operation_dispatcher.py` 持有对 `OperationDispatcher` 的引用**：
```python
# pool_operation_app_service.py:38
self._dispatcher = OperationDispatcher()
```
而 `OperationDispatcher` 依赖 `get_task_registry()`（后台任务注册）。这形成了"AppService → OperationDispatcher → asyncio.create_task"的跨进程通信链路，放在 infrastructure 层是合理的。

### 2.4 `adapter/cache/`（Redis 客户端）

**职责**：`get_redis()` 封装。

**评价**：✅ **极简**。全局单例 Redis 客户端，无额外复杂度。

---

## 3. persistence/ 持久化层分析

### 3.1 models/ 与 repositories/ 对称性

每个 `domain/entitys/{name}/repository.py`（Protocol）→ `infrastructure/persistence/models/{name}.py`（ORM）+ `infrastructure/persistence/repositories/{name}_repository.py`（实现）。

**评价**：✅ **对称性完美**。三层对应（domain interface → ORM model → RepoImpl）。

⚠️ **命名不对齐**：`kline` entity 对应 `tech_kline.py`（ORM）。这是数据库表重命名（`daily_klines` → `tech_kline_dailys`）的历史遗留，应在 `StockInfoDB` 上加注释说明。

### 3.2 connection.py（数据库连接）

- `AsyncSessionLocal`：全局 session 工厂（NullPool 避免事件循环绑定）
- `get_db()`：FastAPI Depends 注入
- `get_db_context()`：Service 层独立事务
- `run_async()`：脚本入口工具

**评价**：✅ **清晰**。NullPool 是务实的选择（兼容 pytest + uvicorn 多场景）。

⚠️ **`run_async()` 在 `connection.py`**——若其他地方有重复工具函数（如 `_scripts/` 里有），应合并。

### 3.3 mixins.py（ORM 混入）

唯一混入：`TimestampMixin`（`created_at` / `updated_at`）。

**评价**：✅ **简单有效**。

---

## 4. config/（配置与 DI）

### 4.1 settings.py

**职责**：`pydantic-settings.Settings`，统一读取 `.env` + 环境变量。

**评价**：✅ **标准做法**。

⚠️ **`get_settings()` 用 `@lru_cache`**：多线程下 `lru_cache` 可能 race（首次并发）。建议用 `threading.Lock` 双重检查（当前代码已用 `_lock`——**已修复**）。

### 4.2 di.py（FastAPI Depends 工厂）

**现状**：只导出 3 个工厂函数：
- `get_indicator_calculator()`
- `get_kline_app_service()`
- `get_concept_brief_service()`
- `get_panel_app_service()`

**评价**：⚠️ **不完整**。route 层中仍有 4 个路由直接写 `Depends(...)` 工厂，而不是从 di.py 导入：
- `concept.py::get_concept_app_service()`（inline）
- `pool.py::get_pool_app_service()`（inline）
- `stock.py::get_stock_app_service()`（inline）
- `stock_analysis.py`（inline）

**建议**：把所有 AppService 工厂集中到 `di.py`，route 层统一 `Depends(get_xxx_app_service)`。

⚠️ **`CollectAppService` 没在 di.py 里**——因为它是独立构造，不走 Depends。需文档说明。

---

## 5. 发现的问题

### 5.1 `infrastructure/adapter/__init__.py` 导入路径

```python
from application.port.collector_port import (...)
from application.port.registry import (...)
```

**问题**：infrastructure 层直接 import application 层——这是**依赖反向**，违反 `application → domain ← infrastructure` 的分层原则。

**分析**：这是为了**聚合导出**（`infrastructure.adapter` 作为对外统一出口），而非实际业务依赖。`application/port/` 里没有 infrastructure 的 import。

**结论**：可以接受（与 `__all__` 重导出等价），但建议在 `__init__.py` 头注释明确说明"此导入仅用于聚合导出，不引入业务依赖"。

### 5.2 `infrastructure/adapter/akshare/` 等空目录

git status 标记了以下目录存在，但实际不存在：
- `infrastructure/adapter/akshare/`
- `infrastructure/adapter/pytdx/`（`fetcher/pytdx.py` 存在，是不同路径）
- `infrastructure/adapter/tushare/`
- `infrastructure/adapter/adata/`（`fetcher/adata.py` 存在，是不同路径）

**原因**：上一轮 DDD 重构时计划迁移 `pipeline`/`data_source` 的 fetcher 到 `adapter/akshare` 等路径，但最终实现放在 `adapter/fetcher/` 下，旧目录未真正创建（或创建后又被删除）。

**建议**：执行 `git clean -fd` 清理未跟踪的伪目录，或用 `find . -type d -name "akshare"` 确认。

### 5.3 `infrastructure/adapter/scheduler/registry.py`（TaskRegistry）

与 `infrastructure/adapter/scheduler/collect/registry.py`（CollectTaskRegistry）**名字相近但职责完全不同**：

| 文件 | 类 | 职责 |
|---|---|---|
| `scheduler/registry.py` | `TaskRegistry` | asyncio.Task 生命周期（派发/取消/查询） |
| `scheduler/collect/registry.py` | `CollectTaskRegistry` | task_type → BaseCollectTask 子类注册表 |

**评价**：⚠️ **两个 Registry 职责不同**，但在同一目录树下。建议：
- 把 `scheduler/registry.py` 改名为 `task_registry.py`（或移到 `scheduler/task_dispatcher.py`）
- 把 `scheduler/collect/registry.py` 改名为 `collect_task_registry.py`（或保持现状但加注释区分）

### 5.4 `collect/planned.py`（14 个占位任务）

```python
# planned.py
all_planned_tasks()  # 返回 14 个 PlannedCollectTask
```

**问题**：14 个"四面重构"中的占位任务（计划任务），`main.py:125` 里一次性注册：
```python
setup_collect_task_registry([
    ...,
    *all_planned_tasks(),  # 14 个占位
])
```

**评价**：✅ **设计合理**（占位 + 可扩展）。⚠️ 建议给 `PlannedCollectTask` 加上"未实现"的明确标记（如 `status = "planned"` 写入 `TaskDef`），避免用户在 UI 上点击后无反馈。

---

## 6. 推荐改造清单

### 6.1 必须做

| 编号 | 动作 | 工作量 |
|---|---|---|
| I1 | 确认并删除 `infrastructure/adapter/akshare/`、`infrastructure/adapter/pytdx/`、`infrastructure/adapter/tushare/`、`infrastructure/adapter/adata/` 伪空目录（如存在） | 5 min |
| I2 | `infrastructure/adapter/__init__.py` 头注释加"此导入仅用于聚合导出，不引入业务依赖" | 2 min |
| I3 | `scheduler/registry.py` 改名为 `task_registry.py`（区分 CollectTaskRegistry） | 5 min |
| I4 | `persistence/models/tech_kline.py` 头注释加一行说明数据库表重命名历史 | 2 min |
| I5 | 把 `concept/pool/stock/stock_analysis` 的 AppService 工厂从 route 层挪到 `di.py` | 3 h |

### 6.2 建议做

| 编号 | 动作 | 工作量 |
|---|---|---|
| I6 | `PlannedCollectTask` 的 `TaskDef` 强制设置 `status="planned"`，route 层 UI 根据 status 灰置按钮 | 30 min |
| I7 | `OperationDispatcher` 改名为 `PoolOperationDispatcher`（避免与通用"派发器"语义混淆） | 10 min |
| I8 | `run_async()` 从 `connection.py` 移到 `scripts/trigger_collect.py`（因为只有脚本用） | 5 min |
| I9 | 给 `infrastructure/adapter/realtime/base.py` 的 `facet`/`sub_facet` 加注释——这是采集管理的 UI 元数据，不是业务规则 | 5 min |

### 6.3 暂缓

| 编号 | 动作 | 原因 |
|---|---|---|
| I10 | 把 15 个 `persistence/models/cap_*.py` 统一改成 `persistence/models/datalink/` 子目录 | 高成本、零收益 |
| I11 | 把 `repositories/` 改名为 `dao/`（中文命名一致性） | 纯改名，路由表不变 |

---

## 7. 一句话总结

**infrastructure 层是架构最重的部分，但职责划分清晰**——fetcher 实现协议、scheduler 做任务框架、persistence 做 ORM + Repo。**最大问题是 DI 工厂分散在 4 个 route 文件里，应该集中到 di.py；次大问题是两个同名 Registry 需要注释或改名区分**。**空目录与 git status 清理是零成本高收益的清扫工作**。