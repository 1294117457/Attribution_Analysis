# 01 · 采集重构 · 方案文档

> 本目录是 step7 阶段的"采集架构精简"方案。**目标**：把当前"6 层（route / service / collect_manage_service / runner / task / fetcher + 5 装饰器链 + DataPort × 23 + DataGateway）"压成"3 层（route / service / fetcher）"——**service 自己管限流/并发/入库/缓存，fetcher 只调 SDK，APScheduler 读 `collect_schedule` 表直接调 service**。
>
> **核心设计原则**：
> - 没有 `Job`、没有 `Task`、没有 `DataPort`、没有 `DataGateway`、没有 5 装饰器链、没有 `collect_data_ports` 表
> - **Service = 业务 + 限流 + 并发 + 入库/缓存 + 调度入口**，**Fetcher = 纯 SDK 调用**
> - **调度配置靠 `collect_schedule` 表 + APScheduler**，调度日志靠 `collect_run_log` 表

## 0. 一句话目标

```
APScheduler 读 collect_schedule 触发
  → ScheduleRunner.fire(schedule_id)
    → CollectService.collect(params)            ← service 内部：限流 + 并发 + 调 fetcher + 入库
      → Fetcher.fetch(**params)                  ← 纯 SDK 调用
        → TushareClient / AdataClient / PytdxClient

HTTP 入口（route）
  → CollectService.collect(params)              ← 同一 service，同一接口
  → CollectService.get(...)                     ← 查询（repo + redis 缓存）
```

**3 层协作**（不再有 job / task / registry / gateway / 装饰器 / port）：

| 层 | 文件位置 | 职责 |
|:--|:--|:--|
| **route** | `contexts/collect/interface/route/` | HTTP 入口（采集触发、查询、调度配置 CRUD） |
| **service** | `contexts/collect/application/service/` | 业务 + 限流 + 并发 + 入库/缓存 + 调度入口 |
| **fetcher** | `contexts/collect/infrastructure/fetcher/` | 纯 SDK 封装（仅调 Tushare/Adata/Pytdx） |

**4 份文档**：

| 文件 | 主题 |
|:--|:--|
| [00-README.md](./00-README.md) | 目录入口 + 3 层架构 + 现状 vs 目标对照 |
| [01-精简方案总览.md](./01-精简方案总览.md) | Service 抽象、ServiceRegistry、collect_schedule / collect_run_log 表设计 |
| [02-删除旧层.md](./02-删除旧层.md) | 删 task / registry / runner / gateway / 装饰器 / port 的清单 |
| [03-实施计划与回退.md](./03-实施计划与回退.md) | 4 周分阶段实施 + 回退方案 |

## 1. 现状 vs 目标对照

| 维度 | 现状（step6 收尾，6 层） | 目标（step7，3 层） |
|:--|:--|:--|
| **采集触发** | `CollectManageService.submit` → `CollectRunner.execute`（状态机） → `Task.run` → `Task.collect_one` → `DataGateway.fetch` → 5 装饰器链 → `XxxTushareFetcher` | `APScheduler` 到点 → `ScheduleRunner.fire` → `Service.collect` → `Fetcher.fetch` |
| **运行模型** | 26 个 `BaseCollectTask` 子类（11 业务 + 14 Dynamic + 1 Planned） | **N 个 `CollectService` 实现类**（平均 50 行/个） |
| **调度配置** | `collect_jobs` 表（混合：mode/times/interval/params/status/success_count...） | `collect_schedule` 表（仅调度：service_name/trigger_type/times/interval/params/concurrency/） |
| **运行日志** | 同一张 `collect_jobs` 表（含 success_count/fail_count/skip_count/duration_ms/message） | `collect_run_log` 表（仅日志：service_name/trigger/started/finished/status/counts） |
| **任务元数据** | `collect_data_ports` 表（从 DB 读 port 目录） | **删除表**——service 内存注册（启动期装配 26 个 service） |
| **限流** | `ThrottleDecorator`（`THROTTLE_GROUPS` + `_GroupState`，进程内 Semaphore + min_interval） | **Service 类变量**——`SERVICE.RATE_LIMIT = ("tushare", 200, 60)` + `asyncio.Semaphore` |
| **重试** | `RetryDecorator`（指数退避 `UNAVAILABLE_BACKOFF`） | **Service 内部**——`for attempt in 3: try/except RateLimited → sleep → retry` |
| **统计** | `MetricsDecorator` 写 `ds:stats:{port}:{tool}:{yyyymmdd}` HASH + 调 `read_stats()` | **logger.info** 即可，**不写 Redis**（用户不再查采集统计页） |
| **缓存** | `CacheDecorator`（实时类 Port 走 `ds:cache:{port}:{sha1}` + 单飞锁） | **Service 内部**——`await cache.get_or_set(key, fetcher_fn, ttl)` |
| **多源切换** | `DataGateway._select` 按 `priority` 循环换源 | **不存在**——`fetcher` 1:1 对应 `source`（要换源就是另一个 fetcher 类） |
| **选源参数** | `source` 字段（缺省 = 多源优先级循环） | `source` 字段（**1:1 映射 fetcher**） |
| **抽象层级** | `DataPort[P,R]`（Generic）→ 23 个 `XxxPort` → 26 个 `XxxAdapter(XxxPort, AdapterBase)` | **仅 `BaseFetcher`（ABC）**——子类直接 `async def fetch(**params) → list[BO]` |
| **业务仓储调用** | `DailyKlineCollectTask.collect_one` 调 `stock_info_service.collect`（间接） | `DailyKlineService.collect` 调 `KlineTushareFetcher` + `KlineRepo.save_batch`（直接） |
| **HTTP 入口** | `POST /collect/jobs/{id}/run`（异步任务） + `GET /collect/jobs/{id}/progress` | `POST /collect/run/{service_name}`（同步返回 `CollectResult`） |
| **调度配置 CRUD** | `POST /collect/jobs`（同时建 job + schedule 字段） | `POST /collect/schedules`（仅 schedule） + `GET /collect/schedules` + `PUT /collect/schedules/{id}` + `DELETE /collect/schedules/{id}` |
| **多 worker** | `collect_jobs` + `SELECT FOR UPDATE SKIP LOCKED` 抢 job | APScheduler 单 worker 调度（不部署多 worker 调度） + HTTP worker N 个 |

## 2. 3 层架构全貌（合并后）

```
src/contexts/collect/
├── application/
│   ├── service/                              ← 业务 service（按"数据实体"分，~22 个）
│   │   ├── base.py                           ← CollectService Protocol + CollectResult
│   │   ├── registry.py                       ← ServiceRegistry（内存 name → service）
│   │   ├── daily_kline_service.py            ← DailyKlineService
│   │   ├── minute_kline_service.py           ← MinuteKlineService（实时）
│   │   ├── stock_basic_service.py            ← StockBasicService
│   │   ├── moneyflow_service.py              ← MoneyflowService
│   │   ├── moneyflow_hsgt_service.py
│   │   ├── margin_service.py
│   │   ├── margin_detail_service.py
│   │   ├── top_list_service.py
│   │   ├── top_inst_service.py
│   │   ├── block_trade_service.py
│   │   ├── holder_number_service.py
│   │   ├── hsgt_top10_service.py
│   │   ├── limit_list_service.py
│   │   ├── adj_factor_service.py
│   │   ├── suspend_service.py
│   │   ├── name_change_service.py
│   │   ├── daily_basic_service.py
│   │   ├── fin_income_service.py
│   │   ├── top10_holders_service.py
│   │   ├── top10_float_holders_service.py
│   │   ├── dividend_service.py
│   │   ├── concept_list_service.py
│   │   ├── concept_membership_service.py
│   │   ├── concept_index_service.py
│   │   ├── concept_reason_service.py
│   │   ├── concept_snapshot_service.py
│   │   ├── news_service.py
│   │   └── sentiment_service.py              ← 占位（暂无 fetcher）
│   └── ...
│
├── interface/                                ← HTTP 入口
│   ├── route/
│   │   ├── collect_run.py                    ← POST /collect/run/{service_name}
│   │   ├── collect_schedule.py               ← GET/POST/PUT/DELETE /collect/schedules
│   │   ├── collect_log.py                    ← GET /collect/logs
│   │   ├── kline.py                          ← GET /klines/daily, GET /klines/minute
│   │   ├── moneyflow.py                      ← GET /moneyflow/...
│   │   └── ...
│   └── dto/...
│
└── infrastructure/
    ├── fetcher/                              ← Fetcher 实现（26 个）
    │   ├── base.py                           ← BaseFetcher（ABC）
    │   ├── tech/
    │   │   ├── DailyKlineTushareFetcher.py
    │   │   ├── MinuteKlinePytdxFetcher.py
    │   │   ├── AdjFactorTushareFetcher.py
    │   │   ├── SuspendTushareFetcher.py
    │   │   └── NameChangeTushareFetcher.py
    │   ├── capital/
    │   │   ├── MoneyflowTushareFetcher.py
    │   │   ├── MarginDetailTushareFetcher.py
    │   │   ├── TopListTushareFetcher.py
    │   │   ├── TopInstTushareFetcher.py
    │   │   ├── BlockTradeTushareFetcher.py
    │   │   ├── HolderNumberTushareFetcher.py
    │   │   ├── HsgtTop10TushareFetcher.py
    │   │   ├── MoneyflowHsgtTushareFetcher.py
    │   │   └── LimitListTushareFetcher.py
    │   ├── fundamental/
    │   │   ├── StockBasicTushareFetcher.py
    │   │   ├── DailyBasicTushareFetcher.py
    │   │   ├── FinIncomeTushareFetcher.py
    │   │   ├── Top10HoldersTushareFetcher.py
    │   │   ├── Top10FloatHoldersTushareFetcher.py
    │   │   ├── DividendTushareFetcher.py
    │   │   ├── ConceptListAdataFetcher.py
    │   │   ├── ConceptMembersAdataFetcher.py
    │   │   ├── StockConceptsAdataFetcher.py
    │   │   ├── ConceptIndexDailyAdataFetcher.py
    │   │   ├── ConceptSnapshotAdataFetcher.py
    │   │   └── ConceptMinuteAdataFetcher.py
    │   ├── news/
    │   │   └── NewsTushareFetcher.py
    │   └── sentiment/                        ← 空
    ├── sdk/                                  ← 第三方 SDK 客户端封装
    │   ├── tushare.py                        ← TushareClient
    │   ├── adata.py                          ← AdataClient
    │   └── pytdx.py                          ← PytdxClient
    ├── persistence/                          ← 仓储 + ORM
    │   ├── models/
    │   │   ├── collect_schedule.py           ← 调度计划 ORM（NEW）
    │   │   ├── collect_run_log.py            ← 运行日志 ORM（NEW）
    │   │   ├── collect_data_port.py          ← ❌ 删除
    │   │   └── collect_job.py                ← ❌ 删除
    │   └── repo/
    │       ├── collect_schedule_repo.py      ← 调度 CRUD（NEW）
    │       ├── collect_run_log_repo.py       ← 日志写入（NEW）
    │       ├── kline_repo.py
    │       ├── stock_repo.py
    │       └── ...
    ├── adapter/
    │   ├── scheduler/
    │   │   └── apscheduler_adapter.py        ← ApschedulerAdapter（保留 + 简化）
    │   ├── runner/
    │   │   └── schedule_runner.py            ← ScheduleRunner（NEW，调度执行器）
    │   └── background/
    │       └── (旧 task_registry 删)         ← ❌ 删除
    ├── framework/                            ← ❌ 整个目录删除
    │   ├── gateway.py                        ← ❌
    │   ├── cache.py                          ← ❌
    │   ├── decorators.py                     ← ❌
    │   ├── registry.py                       ← ❌
    │   ├── context.py                        ← ❌
    │   ├── base.py                           ← ❌
    │   └── setup.py                          ← ❌
    └── setup.py                              ← setup_services()（NEW，启动期装配 service）
```

## 3. 与外部上下文的关系

| 外部上下文 | 保留？ | 关系 |
|:--|:--|:--|
| `user` | ✅ 保留 | 用户、权限、股票池——独立 |
| `shared` | ✅ 保留 | 跨上下文共享（Redis、Postgres、配置） |
| `market` | ✅ 保留 | 业务查询（K 线、股票）—— service 注入 `KlineRepo` 等 |
| `realtime` | ❌ 合并进来 | 实时查询 service 直接调 fetcher（不再走 task） |

**最终仍是 3 个上下文**：`collect` / `user` / `shared`。

## 4. 核心改进指标

| 指标 | 现状 | 目标 | 变化 |
|:--|:--|:--|:--|
| 抽象层数 | 6（route / service / manage / runner / task / fetcher + 装饰器 + port） | **3**（route / service / fetcher） | **-50%** |
| 表数 | 3（`collect_jobs` + `collect_data_ports` + `collect_logs`） | **2**（`collect_schedule` + `collect_run_log`） | **-1** |
| Task 类 | 26 个 | **0 个**（全删） | **-100%** |
| Fetcher 抽象 | `XxxTushareAdapter(XxxPort, AdapterBase)` 多重继承 | `XxxTushareFetcher(BaseFetcher)` 单继承 | 简化 |
| 装饰器链 | 5 个（Metrics / Retry / Throttle / Cache / Validate） | **0 个**（逻辑分散到 service） | **-100%** |
| DataPort 类 | 23 个 | **0 个**（删除 `DataPort` 抽象） | **-100%** |
| 调度器依赖 | `CollectRunner` 状态机 + `CollectManageService` + `CollectTaskRegistry` | **`ApschedulerAdapter` + `ScheduleRunner`** | 简化 |
| 代码行数 | ~6000 行（含 task / framework / port） | **~3500 行**（service 平均 50 行 × 22 + 框架 800 行） | **-40%** |
| 认知负担 | 5 层间接寻址（route → manage → runner → task → gateway → fetcher） | **2 层直接调用**（route → service → fetcher） | **-70%** |

## 5. 关键决策记录

| 决策 | 选项 | 选 | 理由 |
|:--|:--|:-:|:--|
| Service 按"5 个面"分 vs 按"数据实体"分 | A: 5 个巨型 service / B: ~22 个小型 service | **B** | 5 个巨型 service 每个含 5-10 个方法，构造器注入 5-10 个 fetcher，可读性差；22 个小 service 每个 ~50 行，注入 1-2 个依赖 |
| 进度跟踪是否保留 | A: 删 / B: 保留简单 collect_run_log | **A**（用户已确认） | 小规模项目 logger.info 足够；collect_run_log 仅记录最终结果，不记录实时进度 |
| 调度配置写代码 vs 写表 | A: APScheduler 硬编码 / B: collect_schedule 表 | **B**（用户已确认） | 表可后台改；26 个 service 都可被调度 |
| 调度日志是否合并到 schedule 表 | A: 同一张表 / B: 拆 run_log 表 | **B** | 1 个 schedule 对应 N 次 run；表分区更清晰 |
| `collect_data_ports` 表 | A: 保留 / B: 删除 | **B** | service 内存注册足够；端口元数据从代码读 |
| 实时分 K（minute_kline）走 task 还是 service | A: 入库 task / B: 仅 query service | **B** | 分 K 数据量大（每年 8700 万行），不持久化全量；实时查走 fetcher + redis 缓存 |
| Fetcher 与 SDK 的 1:1 关系 | A: 1 fetcher 对应 1 SDK / B: 1 fetcher 对应 N SDK | **A** | 跨 SDK 的同类数据极少（"日 K"主要是 tushare）；1:1 简单清晰 |
| HTTP 入口"采集触发"语义 | A: 异步返回 job_id / B: 同步返回 CollectResult | **B** | 22 个 service 大多能在合理时间内完成；同步简单；后台调度仍可异步 |
| 多 worker 部署 | A: 抢占 job / B: APScheduler 单 worker 调度 + HTTP worker N 个 | **B** | 调度由独立进程跑（生产可单跑 scheduler.py），HTTP worker 只接收请求和查询 |

## 6. 与 step6 三份文档的关系

| step6 文档 | step7 处理 |
|:--|:--|
| `00-README.md`（合并架构） | 已经被 step7 替代：service 进一步吸收 task 职责；task 整层删 |
| `02-去掉data_port表.md` | **采纳**——`collect_data_ports` 表删除、改为 service 内存注册 |
| `03-job_task_fetcher设计.md` | **部分采纳**——保留"fetcher 命名规则"和"限流/并发分散到采集方"，但 **task 整层删除**，job 改为 `collect_schedule` |
| `04-gateway简化与业务层缓存.md` | **采纳**——gateway 删除、缓存由 service 自己写 redis |

