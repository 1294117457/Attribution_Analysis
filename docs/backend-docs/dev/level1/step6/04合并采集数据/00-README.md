# 合并采集数据 · 方案文档

> 本目录是 step6 阶段的"采集子上下文重构"方案。**目标**：把当前"market + realtime + quote + data + collect 五个上下文、6 套 port 装配"**合并为单个 `collect` 上下文**——`fetcher` 按数据源命名（`KlineTushareFetcher`）、`client` 放 SDK 封装、限流/并发/缓存分散到 task 与 service 的具体位置。**调度 → job → task → fetcher → repo** 5 层清晰协作，**采集与实时查询都在 `collect` 内**。

## 0. 一句话目标

```
schedule 查 collect_jobs 触发
  → task（限流 + 并发 + 调 fetcher + 写 repo）   ← 入库类采集
  → fetcher（如 KlineTushareFetcher）             ← 纯 SDK 调用

service（HTTP 入口）
  → 直接调 fetcher + 自己的 redis 缓存             ← 实时查询（分 K / 实时资金流）
  → 不经 task
```

**5 份文档**：

| 文件 | 主题 |
|:--|:--|
| [00-README.md](./00-README.md) | 目录入口 + 单 `collect` 架构 + 现状 vs 目标对照 |
| [01-回退硬编码清单.md](./01-回退硬编码清单.md) | 23 个 task 类清单 + fetcher 重命名（`KlineTushareFetcher`）+ `infra/sdk/` 拆分 |
| [02-去掉data_port表.md](./02-去掉data_port表.md) | `collect_data_ports` 表删除 + 去掉 `DataGateway`（取消 5 装饰器链） |
| [03-job_task_fetcher设计.md](./03-job_task_fetcher设计.md) | job / task / fetcher 4 层架构（去掉 gateway 层） + task 内置限流并发 |
| [04-gateway简化与业务层缓存.md](./04-gateway简化与业务层缓存.md) | 实时查询 service + 业务层 redis 缓存 + market 调 collect 内的"分 K 查询 service" |

## 1. 现状 vs 目标对照

| 维度 | 现状（D3 阶段，5 个上下文） | 目标（合并后，单 `collect`） |
|:--|:--|:--|
| 上下文划分 | `market` / `realtime` / `quote` / `data` / `collect` 5 个 | **只剩 `collect`**（其余 4 个的职责合并进来） |
| 任务元数据存哪 | `collect_data_ports` 表（DB） | `_collect_registry`（内存） |
| 任务类怎么生成 | 14 个声明式 task + 1 个 `DynamicCollectTask` | **23 个具体 task 类** |
| Fetcher 命名 | `TushareDailyKlineAdapter`（adapter 后缀 + 业务名前缀） | **`KlineTushareFetcher`**（`业务 + 数据源 + Fetcher`） |
| Fetcher 放哪 | `data/infrastructure/fetcher/kline.py` | **`collect/infrastructure/fetcher/kline_tushare.py`** |
| SDK 客户端 | `data/infrastructure/client/tushare.py`（与 fetcher 同上下文） | **`collect/infrastructure/sdk/tushare.py`**（`TushareClient`） |
| Gateway 选源 | `_select` 按 `priority` 循环 | **去掉**——`source` 一传定 = 单 fetcher |
| 缓存（分 K / 实时） | `CacheDecorator` 在 gateway 内 | **业务 service 自己用 `redis.set/get`** |
| 限流 | `ThrottleDecorator` 跨 task 共享 Redis ZSET | **task 内 `RedisCache.rate_limit`（滑动窗口） + 进程内 `Semaphore`（THROTTLE_GROUPS）** |
| 统计 | `MetricsDecorator` + `read_stats` | **task 内 Redis HASH pipeline**（沿用 `stats_key` 模式） |
| 业务 service 与 task 关系 | `stock_info_service.collect` 调 gateway + repo；`DailyKlineCollectTask` 调 service | **`stock_info_service.collect` 合并到 `DailyKlineCollectTask.collect_one`**；service 只保留 HTTP 入口 |
| 实时分 K 查询 | `market_service.get_minute_klines` 调 `gateway.fetch(MinuteKlinePort, QUERY)` | **`MinuteKlineQueryService` 调 `KlineTushareFetcher` + 自己的 `redis.get/set`** |

## 2. 合并后单 `collect` 上下文全貌

```
src/contexts/collect/                    ← 单 collect 上下文
├── domain/                              ← 领域
│   ├── entitys/collect_job/             ← 1 个聚合根
│   │   ├── entity.py                    ← CollectJobEntity（task_type / params / status / ...）
│   │   ├── repository.py                ← CollectJobRepository
│   │   └── vo.py                        ← TaskType / JobStatus / ScheduleVO
│   ├── entitys/collect_log/             ← 1 个聚合根
│   │   ├── entity.py                    ← CollectLogEntity（task_id / unit / level / message / ...）
│   │   ├── repository.py
│   │   └── vo.py                        ← LogLevel / LogKind
│   └── service/                         ← 跨聚合的领域服务（极少）
│       └── schedule_resolver.py         ← mode=time / interval → 下次触发时间
│
├── application/                         ← 应用层
│   ├── service/                         ← 业务 service（按业务域分）
│   │   ├── job_service.py               ← CollectJobService（创建/启动/取消/重跑 job）
│   │   ├── kline_query_service.py       ← MinuteKlineQueryService（实时分 K 查询 + redis 缓存）
│   │   ├── concept_query_service.py     ← ConceptQueryService（实时概念查询 + redis 缓存）
│   │   ├── moneyflow_query_service.py   ← 实时资金流
│   │   ├── quote_query_service.py       ← 实时盘口
│   │   ├── news_query_service.py        ← 实时新闻
│   │   └── ...
│   ├── fetcher/                         ← task 用的"采集用例"
│   │   ├── base.py                      ← BaseCollectTask + UnitResult + TaskSummary + run_units
│   │   ├── runner.py                    ← CollectRunner.execute（状态机 + 进度）
│   │   ├── context.py                   ← CollectContext（fetcher 集合 + raw_store + universe + ...）
│   │   ├── registry.py                  ← CollectTaskRegistry
│   │   └── tasks/                       ← 23 个 task 类
│   │       ├── daily_kline.py
│   │       ├── stock_basic.py
│   │       ├── concept.py
│   │       ├── concept_membership.py
│   │       ├── concept_reason.py
│   │       ├── moneyflow.py
│   │       └── ...
│   ├── port/                            ← 对外抽象
│   │   ├── fetcher_port.py              ← IFetcher / FetchResult
│   │   ├── job_store_port.py            ← CollectJobStorePort
│   │   ├── progress_port.py             ← CollectProgressPort
│   │   ├── scheduler_port.py            ← SchedulerPort
│   │   └── cache_port.py                ← ICache（redis 抽象，业务 service 用）
│   └── dto/...
│
├── interface/                           ← HTTP 入口
│   ├── route/
│   │   ├── collect.py                   ← /collect/jobs /collect/catalog
│   │   ├── kline.py                     ← /klines/minute 等
│   │   ├── concept.py                   ← /concepts/...
│   │   └── ...
│   └── dto/...
│
└── infrastructure/                      ← 基础设施
    ├── fetcher/                         ← Fetcher 实现（按"业务 + 数据源"命名）
    │   ├── kline_tushare.py             ← KlineTushareFetcher
    │   ├── kline_adata.py               ← KlineAdataFetcher
    │   ├── stock_basic_tushare.py       ← StockBasicTushareFetcher
    │   ├── concept_tushare.py
    │   ├── concept_membership_adata.py
    │   ├── concept_reason_adata.py
    │   ├── moneyflow_tushare.py
    │   ├── news_adata.py
    │   ├── minute_kline_tushare.py      ← 实时分 K（直接给 service 用）
    │   └── ...
    ├── sdk/                             ← 第三方 SDK 客户端封装
    │   ├── tushare.py                   ← TushareClient（init + 调用 + 限频参数）
    │   ├── adata.py                     ← AdataClient
    │   └── tdx.py                       ← TdxClient
    ├── throttle/                        ← 限流基础设施（复用工程已有）
    │   ├── config.py                   ← ThrottleConfig / THROTTLE_GROUPS（搬自 decorators.py）
    │   └── group_state.py              ← _GroupState（进程内 Semaphore + min_interval）
    ├── stats/                          ← 统计常量（搬自 decorators.py）
    │   └── keys.py                    ← stats_key / cache_stats_key / STATS_KEEP_DAYS
    ├── persistence/                     ← 仓储实现
    │   ├── collect_job_store.py
    │   ├── collect_log_store.py
    │   ├── progress_store.py
    │   ├── kline_repo.py
    │   ├── stock_repo.py
    │   ├── concept_repo.py
    │   └── ...
    └── adapter/
        └── scheduler/
            └── apscheduler_adapter.py   ← ApschedulerAdapter
```

## 3. 与外部上下文的关系

| 外部上下文 | 保留？ | 关系 |
|:--|:--|:--|
| `data` | ❌ **删除** | fetcher 全部移入 `collect/infrastructure/fetcher/`；SDK 全部移入 `collect/infrastructure/sdk/` |
| `market` | ⚠️ **合并进来** | 业务查询（K 线、股票）作为 `collect/application/service/` 下的 service；HTTP route 移入 `collect/interface/route/` |
| `realtime` | ⚠️ **合并进来** | 实时查询（分 K、实时资金流）作为 `collect/application/service/` 下的 query service |
| `quote` | ⚠️ **合并进来** | 行情盘口作为 `QuoteQueryService` |
| `user` | ✅ **保留** | 用户、权限、股票池——独立 |
| `shared` | ✅ **保留** | 跨上下文共享 |

**合并后只有 3 个上下文**：`collect` / `user` / `shared`。
