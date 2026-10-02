# application/ 应用层分析

> 关联：[`00-总览与建议清单.md`](00-总览与建议清单.md) · [`../config/DDD.md` §2.2](../../config/DDD.md)

---

## 1. 当前文件清单

```
backend/src/application/
├── __init__.py                 （空，git status 误标）
├── port/                       （采集/调度对外抽象接口）
│   ├── __init__.py             （空）
│   ├── collector_port.py       （6 类 fetcher Protocol + RateLimitError）
│   └── registry.py             （FetcherRegistry 单例 + setup_default_registry）
└── service/                    （9 个 AppService）
    ├── collect_app_service.py         （420 行）
    ├── concept_app_service.py         （298 行）
    ├── kline_app_service.py           （429 行）
    ├── panel_app_service.py           （156 行）
    ├── pool_app_service.py            （272 行）
    ├── pool_operation_app_service.py  （187 行）
    ├── realtime_app_service.py        （git status 误标，实际不存在）
    ├── stock_app_service.py           （199 行）
    └── stock_analysis_app_service.py  （167 行）
```

---

## 2. 各 AppService 职责矩阵

| AppService | 聚合根 | 依赖的 Repository | 是否用 DI 注入 | 备注 |
|---|---|---|---|---|
| `CollectAppService` | `SysCollectTask` + `CollectPlan` + `CollectGroup` | 自管（不走 DI） | ❌ 直接构造 RepoImpl | 旧路径 |
| `KlineAppService` | `Kline` | `KlineRepository` + `StockInfoRepository` + `IndicatorCalculator` | ✅（route 层）但 scheduler 子任务内 ❌ 仍自 new | **不一致** |
| `StockAppService` | `StockInfo` | `StockInfoRepository` | ✅（route 层） | OK |
| `ConceptAppService` | `Concept` | `ConceptRepository` + `ConceptFetcher` | ❌ route 内构造 | partial |
| `PanelAppService` | （组合视图） | `StockPanelComposeRepository` + `ConceptRepository` + `ConceptBriefService` | ✅（DI） | OK |
| `StockPoolAppService` | `StockPool` | `StockPoolRepository` + `StockInfoRepository` | ✅（route 层） | OK |
| `PoolOperationAppService` | `PoolOperation` | `StockPoolRepository` + `PoolOperationRepository` + `OperationDispatcher` | ✅（route 层） | OK |
| `StockAnalysisAppService` | （聚合视图） | `StockInfoRepository` + `KlineRepository` + `StockPoolRepository` + `SignalDetector` | ✅（route 层） | OK |
| `RealtimeAppService` | — | — | **不存在** | 已被 `RealtimeQueryFramework` 替代 |

---

## 3. 发现的问题

### 3.1 `CollectAppService` 没走 DI（中等）

**位置**：`backend/src/application/service/collect_app_service.py:74-93` 内的 `SubmittedTask` / 工具函数 + `submit/run_one` 方法——直接 `await CollectConfigRepoImpl(session)`、`await SysCollectTaskDB(...)`。

**问题**：唯一不依赖注入的应用服务。`main.py:98-135` 的 lifespan 直接 `setup_collect_task_registry([...])`，并不通过 DI 工厂。

**建议**：
- 方案 A（推荐）：保持现状。`CollectAppService` 是"跨请求/后台调度"的入口（lifespan、APScheduler 触发），与依赖 FastAPI Depends 的"路由级"service 性质不同，独立构造即可。
- 方案 B：新增 `infrastructure/config/di.py::get_collect_app_service(session)`，让 route 层也走 DI，scheduler 子层自己挂。

**ROI**：中。**现状可控**，建议加 docstring 说明"为何不注入"，不必动代码。

### 3.2 `KlineAppService` 在 scheduler 子任务内自 new Repo（高优先级）

**位置**：`infrastructure/adapter/scheduler/collect/daily_kline.py:98`：

```python
async with AsyncSessionLocal() as session:
    svc = KlineAppService(KlineRepoImpl(session), StockRepoImpl(session))
    resp = await asyncio.wait_for(
        svc.collect(build_request(symbol, params), fetcher),
        timeout=UNIT_TIMEOUT,
    )
```

**问题**：违背 DDD "AppService 只接收 Repository，不构造"。

**建议**：把构造逻辑提到工厂方法：

```python
# kline_app_service.py
class KlineAppService:
    @classmethod
    def from_session(cls, session, calc: IndicatorCalculator | None = None):
        return cls(
            kline_repo=KlineRepoImpl(session),
            stock_repo=StockRepoImpl(session),
            indicator_calc=calc,
        )
```

或在 `infrastructure/config/di.py` 加 `build_kline_app_service(session)` 函数，scheduler 调用方统一走工厂。

**ROI**：高。改动小，价值大（彻底一致）。

### 3.3 `ConceptAppService` 由 route 自构造（中等）

**位置**：`route/api/v1/concept.py:34-43`：

```python
def get_concept_app_service(
    db: AsyncSession = Depends(get_db),
) -> ConceptAppService:
    registry = get_registry()
    if not registry.has(ConceptFetcher):
        raise HTTPException(503, "概念采集器未注册")
    fetcher = registry.get(ConceptFetcher)
    repo = ConceptRepoImpl(db)
    return ConceptAppService(repo=repo, fetcher=fetcher)
```

**问题**：DI 工厂在 route 层而不是 `infrastructure/config/di.py`。同一模式也存在于 `pool.py`。

**建议**：把所有 "AppService 工厂" 集中到 `infrastructure/config/di.py`，route 层只 `Depends(...)`。

**ROI**：高（一致性收益大）。但代码量多，需要逐个迁移（约 8 个 router）。

### 3.4 `RealtimeAppService` 在 git status 误标（清理）

**位置**：git status 列了 `?? application/service/realtime_app_service.py` 与 `?? application/port/__init__.py`。

**实际状态**：`infrastructure/adapter/realtime/framework.py::RealtimeQueryFramework` 已经替代了它；不再需要 AppService（实时接口无业务编排，是纯框架调用）。

**建议**：检查 `realtime_app_service.py` 是否真存在；如不存在，让 git 上提一个 commit 让状态干净。

---

## 4. 推荐改造清单

### 4.1 必须做

| 编号 | 动作 | 工作量 |
|---|---|---|
| A1 | 修复 `kline_app_service.py:3` 与 `stock_analysis_app_service.py:11` 的过期注释 | 5 min |
| A2 | `KlineAppService` 加 `from_session` 类方法，scheduler 子任务统一走工厂 | 30 min |
| A3 | 把 `concept_app_service` 的工厂挪到 `infrastructure/config/di.py`，route 改 `Depends(get_concept_app_service)` | 1 h |
| A4 | 同样改造 `pool_app_service` / `pool_operation_app_service` / `stock_app_service` 的工厂 | 2 h |

### 4.2 建议做

| 编号 | 动作 | 工作量 |
|---|---|---|
| A5 | `CollectAppService` 头注释补"独立构造，不走 DI"的说明 | 5 min |
| A6 | 把 `domain/kline/vo.py` 的 `SINGLETON` / `LEGACY` 旧占位移除（如果还在） | 5 min |
| A7 | `application/port/__init__.py` 内容若仍为空则保留（为子包标记） | 0 |

### 4.3 不建议做

| 编号 | 动作 | 原因 |
|---|---|---|
| A8 | 把 `PoolOperationAppService` 合并到 `StockPoolAppService` | 两者职责（CRUD vs 后台派发）不同，硬合会让 StockPoolAppService 超过 600 行 |
| A9 | 按"读写"再切分 service | DDD 反模式；破坏"按聚合根分文件"的清晰度 |
| A10 | 把 `StockAnalysisAppService` 合并到 `StockAppService` | 分析聚合依赖 4 个 repository + SignalDetector，与 CRUD 复杂度差距大 |

---

## 5. 一句话总结

**AppService 切分已经稳定且符合 DDD 战术模式**；剩下都是「构造注入一致性」与「过期注释」两类低成本改动。**不要轻易合并或拆分**，避免破坏当前清晰的"按聚合根 → 一个 AppService"映射。