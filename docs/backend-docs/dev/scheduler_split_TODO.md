# step7 拆分后续 TODO

## P0 — 前后端联通 BUG（拆分时发现，**非本次拆分引入**）

collect 17 个 service 的 `__init__` 接受 fetcher 参数，但 DI 工厂 `get_xxx_service()` 全部写成
`return XxxService()` 没传 fetcher。访问对应 HTTP 路由时会立即抛 `TypeError: missing fetcher`。

### 受影响的 service（17 个）：

| 工厂 | 缺少 fetcher 类型 | 路由路径 |
|---|---|---|
| `get_suspend_service` | `SuspendTushareFetcher` | POST /api/v1/collect/tech/suspend/trigger |
| `get_name_change_service` | `NameChangeTushareFetcher` | POST /api/v1/collect/tech/name-change/trigger |
| `get_news_service` | `NewsTushareFetcher` | POST /api/v1/collect/news/trigger |
| `get_block_trade_service` | `BlockTradeTushareFetcher` | POST /api/v1/collect/capital/.../trigger |
| `get_margin_service` | `MarginDetailTushareFetcher` | POST /api/v1/collect/capital/.../trigger |
| `get_hsgt_top10_service` | `HsgtTop10TushareFetcher` | POST /api/v1/collect/capital/.../trigger |
| `get_limit_list_service` | `LimitListTushareFetcher` | POST /api/v1/collect/capital/.../trigger |
| `get_holder_number_service` | `HolderNumberTushareFetcher` | POST /api/v1/collect/capital/.../trigger |
| `get_moneyflow_hsgt_service` | `MoneyflowHsgtTushareFetcher` | POST /api/v1/collect/capital/.../trigger |
| `get_fin_income_service` | `FinIncomeTushareFetcher` | POST /api/v1/collect/fundamental/.../trigger |
| `get_top10_holders_service` | `Top10HoldersTushareFetcher` | POST /api/v1/collect/fundamental/.../trigger |
| `get_top10_float_holders_service` | `Top10FloatHoldersTushareFetcher` | POST /api/v1/collect/fundamental/.../trigger |
| `get_dividend_service` | `DividendTushareFetcher` | POST /api/v1/collect/fundamental/.../trigger |
| `get_concept_list_service` | `ConceptListAdataFetcher` | POST /api/v1/collect/concept/.../trigger |
| `get_concept_membership_service` | `ConceptMembersAdataFetcher` | POST /api/v1/collect/concept/.../trigger |
| `get_concept_index_service` | `ConceptIndexDailyAdataFetcher` | POST /api/v1/collect/concept/.../trigger |
| `get_concept_minute_service` | `ConceptMinuteAdataFetcher` | （query 类）|
| `get_concept_snapshot_service` | `ConceptSnapshotAdataFetcher` | （query 类）|
| `get_stock_concepts_service` | `StockConceptsAdataFetcher` | POST /api/v1/collect/concept/.../trigger |

### 不受影响的 service（9 个，可无参构造）：

- `get_daily_kline_service` / `get_minute_kline_service` （query 类）
- `get_adj_factor_service`
- `get_stock_basic_service`（query 类）
- `get_moneyflow_service`
- `get_top_list_service`
- `get_top_inst_service`
- `get_daily_basic_service`
- `get_sentiment_service`（未在 DI 工厂中注册，但 service 类存在）

### 最小修复方案（单文件改动 `infrastructure/di/collect_service.py`）：

**对每个受影响的 `get_xxx_service` 工厂**改为：

```python
def get_suspend_service():
    from contexts.collect.application.service.collect.suspend_service import SuspendService
    from contexts.collect.infrastructure.fetcher.tech.SuspendTushareFetcher import SuspendTushareFetcher
    return SuspendService(fetcher=SuspendTushareFetcher())
```

或者更优雅的版本——用映射表：

```python
# 顶部定义
_FETCHER_FACTORIES = {
    "suspend":       ("contexts.collect.application.service.collect.suspend_service",     "SuspendService",     "contexts.collect.infrastructure.fetcher.tech.SuspendTushareFetcher",      "SuspendTushareFetcher"),
    "name_change":   (...),
    ...
}

# 工厂函数统一为
def get_suspend_service():
    from contexts.collect.infrastructure.fetcher.tech.SuspendTushareFetcher import SuspendTushareFetcher
    from contexts.collect.application.service.collect.suspend_service import SuspendService
    return SuspendService(fetcher=SuspendTushareFetcher())
```

**改动量**：1 个文件，~20 个工厂函数体各加 1 行（导入 fetcher + 传参）。

**为什么本次不修**：用户明确说"暂时先不实现定时调度相关功能，先拆离出 collect 模块"。
修 BUG 是另一个独立任务，建议在开新 session 处理。

---

## P1 — scheduler 模块后续可补充

1. **APScheduler 适配器** `contexts/scheduler/infrastructure/scheduler/apscheduler_adapter.py`
2. **ScheduleRunner** `contexts/scheduler/application/service/schedule_runner.py`（轮询 schedule 表 + 触发 service）
3. **RunLogService** `contexts/scheduler/application/service/run_log_service.py`（start/finish_success/finish_failed）
4. **scheduler HTTP 路由** `contexts/scheduler/interface/route/schedule.py` + `run_log.py`（CRUD + 查询）
5. **DTO** `contexts/scheduler/interface/dto/request/schedule.py` + `response/schedule.py`
6. **DI 工厂** `contexts/scheduler/infrastructure/di/scheduler_service.py`
7. **DB 表名迁移**（可选）`ALTER TABLE collect_schedule RENAME TO schedule` + 索引重命名
8. **scheduler 路由挂载**（在 `shared/interface/router_compat.py` 中加 `api_router.include_router(scheduler_router)`）

---

## 本次拆分改动统计

### 删除（7 个文件 / 2 个目录）

| 路径 |
|---|
| `contexts/collect/domain/entitys/collect_schedule/{entity,vo,repository,__init__}.py` (4 个) |
| `contexts/collect/domain/entitys/collect_run_log/{entity,vo,repository,__init__}.py` (4 个) |
| `contexts/collect/application/port/scheduler_port.py` |
| `contexts/collect/infrastructure/persistence/models/collect_schedule.py` |
| `contexts/collect/infrastructure/persistence/models/collect_run_log.py` |
| `contexts/collect/infrastructure/persistence/repositories/collect_schedule_repo.py` |
| `contexts/collect/infrastructure/persistence/repositories/collect_run_log_repo.py` |

共 11 个文件删除 + 2 个空目录清理。

### 新建（19 个文件）

```
contexts/scheduler/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── value_objects.py
│   ├── entitys/
│   │   ├── schedule/
│   │   │   ├── __init__.py
│   │   │   ├── entity.py
│   │   │   ├── repository.py
│   │   │   └── vo.py
│   │   └── run_log/
│   │       ├── __init__.py
│   │       ├── entity.py
│   │       ├── repository.py
│   │       └── vo.py
├── application/
│   ├── __init__.py
│   └── port/
│       ├── __init__.py
│       └── scheduler_port.py
└── infrastructure/
    ├── __init__.py
    └── persistence/
        ├── models/
        │   ├── __init__.py
        │   ├── schedule.py
        │   └── run_log.py
        └── repositories/
            ├── __init__.py
            ├── schedule_repo.py
            └── run_log_repo.py
```

### 修改（3 个文件）

| 文件 | 改动 |
|---|---|
| `contexts/collect/application/port/__init__.py` | 删除 `ApschedulerPort` / `JobHandler` re-export |
| `contexts/collect/infrastructure/persistence/repositories/__init__.py` | 删除 `SqlCollect*` re-export |
| `contexts/collect/application/service/base.py` | 注释：`collect_schedule` → `schedule`（见 scheduler 模块）|

### 命名变化（类名跟随模块重命名）

| 旧类名 | 新类名 | 位置 |
|---|---|---|
| `CollectSchedule` | `Schedule` | `scheduler.domain.entitys.schedule.entity` |
| `CollectScheduleDB` | `ScheduleDB` | `scheduler.infrastructure.persistence.models.schedule` |
| `CollectScheduleRepository` | `ScheduleRepository` | `scheduler.domain.entitys.schedule.repository` |
| `SqlCollectScheduleRepository` | `SqlScheduleRepository` | `scheduler.infrastructure.persistence.repositories.schedule_repo` |
| `CollectRunLog` | `RunLog` | `scheduler.domain.entitys.run_log.entity` |
| `CollectRunLogDB` | `RunLogDB` | `scheduler.infrastructure.persistence.models.run_log` |
| `CollectRunLogRepository` | `RunLogRepository` | `scheduler.domain.entitys.run_log.repository` |
| `SqlCollectRunLogRepository` | `SqlRunLogRepository` | `scheduler.infrastructure.persistence.repositories.run_log_repo` |

### DB 表名（**未改**）

| ORM | `__tablename__` |
|---|---|
| `ScheduleDB` | `collect_schedule` (保留) |
| `RunLogDB` | `collect_run_log` (保留) |

理由：避免破坏已有 DB 数据；后续 RENAME TABLE 由独立迁移脚本处理。
