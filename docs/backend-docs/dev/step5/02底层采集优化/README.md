# 底层采集优化（总览）

## 1. 要解决什么

现在 `infrastructure/adapter/{fetcher, realtime, scheduler}` 三处各管一摊，问题集中在：

| 问题 | 现状 |
| :-- | :-- |
| 同一份数据三套"接口" | `collector_port.py` 18 个 `XxxFetcher` Protocol、`scheduler/collect/` 21 个 `BaseCollectTask`、`realtime/` 2 个 `BaseRealtimeQuery`，元数据（facet / label / description）各写一遍 |
| 实现按 SDK 堆成大类 | `TushareFetcher` 约 1050 行实现 16 个协议；`ConceptFetcher` 一个协议塞了 5 种数据，`concept_snapshot` 还调用了协议外的 `fetch_current_snapshot` |
| 签名不统一 | `fetch(params)` / `fetch_daily_basic(trade_date)` / `async fetch_minute_klines(...)`，返回 `list[Any]`，无法按"接口名 + 参数"统一调用 |
| 工具和数据源混在一起 | `AdataConceptFetcher` = adata × 同花顺；无法表达"akshare 取东财数据" |
| 一个协议只能有一个实现 | `FetcherRegistry.get(Port)` 只返回一个实例，无法选源、无法失败换源 |
| 横向逻辑到处复制 | 13 个任务文件各有一份 `RATE_LIMIT_WAIT` / `_fetch_with_rate_limit` / `_sleep_cancellable`；实时框架另有一套 `SOURCE_CONCURRENCY` |
| realtime 职责混杂 | 一个实时接口类里同时有数据定义、取数、缓存配置、业务降级、结果组装 |
| scheduler 依赖方向反了 | 调度器启动时自己读方案表，到点反向 import `di` 调 `CollectManageService`；Service 又直接 import 调度器的 `get_collect_scheduler` / `validate_schedule`；池操作的后台任务管理也放在 `scheduler/` 下 |

## 2. 目标

1. 业务、采集管理、Agent、其他服务都通过**同一个入口**按"接口名 + 参数"或类型化方式取数。
2. 一份数据（日 K、资金流向…）只定义一次接口约束；可有多个底层实现，按优先级选源、失败换源。
3. 采集入库、实时查询、定时编排是**使用方式**，不再各自定义数据：
   - 实时查询 = 应用层 Service 带缓存策略调用统一入口，`realtime/` 目录取消；
   - 定时编排 = `CollectManageService` 通过调度端口创建 / 删除定时任务，基础设施只负责到点回调。
4. 限流 / 重试 / 统计 / 缓存只写一处。

**不变的东西**：对外 HTTP 接口 URL、`task_type` 名称、`sys_collect_tasks` / `collect_fetchers` / 采集方案表结构、前端页面、采集进度 Redis 键 —— 全部保持兼容（个别返回字段的变化在 05 中列出）。

## 3. 分层、命名与设计模式

### 3.1 命名约定

| 层 | 命名 | 示例 | 含义 |
| :-- | :-- | :-- | :-- |
| 第一层 根约束 | `DataPort` | — | 所有数据接口的抽象基类 |
| 第二层 接口约束 | `XxxPort` + `XxxParams` + `XxxBO` | `MoneyflowPort`、`MoneyflowParams`、`CapMoneyflowBO` | 描述"取什么"：名称、元数据、参数模型、返回类型；仍是抽象类。不含任何数据源字段 |
| 实现方属性 | `AdapterBase` | — | infrastructure 侧：`tool` / `origin` / `priority` / `throttle_group` |
| 第三层 底层实现 | `<工具>XxxAdapter` | `TushareDailyKlineAdapter` | 继承对应 Port 和 `AdapterBase`，描述"怎么取" |
| SDK 连接 | `<工具>Client` | `TushareClient` | 鉴权、连接、错误翻译 |
| 横向增强 | `XxxDecorator` | `RetryDecorator`、`CacheDecorator` | 接口不变，在外面叠加能力 |
| 统一入口 | `DataGateway` | — | 门面：按名或按类型调用 |
| 调用 / 结果 | `DataCommand` / `DataResult` | — | 一次调用的请求与结果 |
| 按名调用入口 | `DataQueryService` | — | 应用层：HTTP / Agent / "试查"按名调用，带条数上限和日志 |

Port / Adapter 沿用项目现有的 `application/port`、`infrastructure/adapter` 词汇，分层规则以 [DDD.md](../../../config/DDD.md) 为准（§2.2 "port 的组成"）。

### 3.2 调用流程

```
启动期     ⓪ 注册表式工厂：注册 Adapter（自动归到所属 Port）、Client，装配装饰器
──────────────────────────────────────────────────────────────────
调用方     ① 类型化：fetch(XxxPort, XxxParams)                  ← 业务 Service / 采集任务
           ① 按名：DataCommand{name, params, source?, policy}    ← DataQueryService（HTTP / Agent / 试查）
入口       ② 门面：DataGateway.fetch / fetch_many / invoke
查接口     ③ 注册表按 name 找到 Port + Params 校验（pydantic）
缓存       ④ CacheDecorator：policy=QUERY 且 Port 声明了 cache 时启用（缓存 / 单飞）
选数据源   ⑤ 策略（指定 source）/ 责任链（按 priority 逐个尝试）
横向增强   ⑥ 装饰器链：MetricsDecorator → RetryDecorator → ThrottleDecorator
底层实现   ⑦ XxxAdapter：入参转换 → 调 Client → 结果转 BO
底层连接   ⑧ XxxClient：token / 连接 / 同源共享限流配额
```

三种使用方式都在 ① 之前，由应用层决定：

| 使用方式 | 谁来做 | 怎么调 |
| :-- | :-- | :-- |
| 实时查询（不入库） | 业务 Service（`concept_service`、`stock_info_service`） | `gateway.fetch(XxxPort, params, policy=QUERY)`，失败降级由 Service 自己处理 |
| 采集入库 | 采集任务（模板方法 `execute_task`） | 每个单元 `gateway.fetch(...)` 后落库 |
| 定时编排 | `CollectManageService` | 通过 `SchedulerPort` 注册方案定时，到点回调 `run_plan` |

### 3.3 各部分的模式与作用

| 部分 | 模式 | 作用 | 详见 |
| :-- | :-- | :-- | :-- |
| `DataPort` / `XxxPort` | 端口 | 接口约束：一份数据只定义一次 | [01](./01-核心骨架.md) |
| `DataPortRegistry` | 注册表式工厂 | 一个 Port → 多个 Adapter，新增只需注册 | [01](./01-核心骨架.md) |
| `DataGateway` + `DataCommand` | 门面 + 命令 | 统一入口，调用可存储、可重放 | [01](./01-核心骨架.md) |
| 选源 | 策略 + 责任链 | 指定源，或按优先级失败换源 | [01](./01-核心骨架.md) |
| `XxxAdapter` + `XxxClient` | 适配器 | 把各家 SDK 统一成 Port 约束 | [02](./02-底层实现拆分.md) |
| `XxxDecorator` | 装饰器 | 统计、重试、限流、缓存只写一处 | [03](./03-横向装饰器.md) |
| 采集任务 | 模板方法 + 注入的规划器 | 14 个按日 / 按股票任务改成声明式，其余 7 个只换取数方式 | [04](./04-采集任务改造.md) |
| 实时查询 | 缓存装饰器 + 应用层降级 | 取消 `realtime/`，业务直接调统一入口 | [05](./05-实时查询并入统一入口.md) |
| 对外暴露 | 门面 + 命令 | 业务 Service 类型化接入；HTTP、Agent 经 `DataQueryService` 按名接入 | [06](./06-统一入口与对外暴露.md) |
| 定时调度 | 端口 + 回调 | 应用层决定"何时跑什么"，基础设施只负责"到点叫醒" | [07](./07-定时调度改造.md) |

三种"再试一次"不要混：

| 场景 | 模式 | 位置 |
| :-- | :-- | :-- |
| 同一数据源偶发超时 / 限频，等一会儿再试 | `RetryDecorator` | ⑥ |
| 数据源不可用，换下一个数据源 | 责任链 | ⑤ |
| 一批单元跑完，失败单元再补采一轮 | 模板方法固定步骤（`run_units`） | 采集任务 |

## 4. 修改前后目录

### 修改前

```
application/
  port/
    collector_port.py          18 个 XxxFetcher Protocol + CollectParams + RateLimitError
    registry.py                FetcherRegistry（协议 → 单实例 / 工厂）
    realtime_query_port.py     RealtimeQueryPort
  service/
    collect_manage_service.py  直接 import scheduler.collect / collect_scheduler
infrastructure/
  config/di.py                 setup_default_registry：TushareFetcher 一个实例注册 16 个协议
  adapter/
    fetcher/
      base.py                  BaseCollector（logger / source_name）
      tushare.py               TushareFetcher（~1050 行，16 个 fetch_*）+ TushareKlineParser
      adata.py                 AdataConceptFetcher（5+1 个 fetch_*）
      pytdx.py                 PytdxFetcher + MinuteKlineBO
    realtime/
      base.py                  BaseRealtimeQuery（元数据 + fetch + 缓存键 + 降级）
      framework.py             缓存 / 单飞 / 同源并发 / 超时 / 降级 / 统计
      registry.py
      stock_minute_kline.py  concept_minute.py
    scheduler/
      collect/
        base.py                BaseCollectTask + execute_task + run_units + 增量工具
        registry.py            CollectTaskRegistry + catalog（合并实时接口）
        daily_kline.py daily_basic.py stock_basic.py fin_report.py
        cap_*.py ×6  fin_top10_*.py ×2  base_*.py ×4
        concept.py concept_reason.py concept_snapshot.py planned.py
      collect_scheduler.py     APScheduler + 读方案表 + 反向调 Service + 定时规则校验
      operation_dispatcher.py  task_registry.py（池操作后台任务，与定时无关）
```

### 修改后

```
domain/entitys/collect_plan/
  vo.py                        Schedule 值对象：定时配置 + 校验规则（间隔下限、每日时间点上限）
application/
  port/
    data/                      ← 第一层根约束 + 第二层接口约束（每个面文件含 Port + Params + BO）
      base.py                  DataPort、DataCommand、DataResult、CachePolicy、错误类型、DataGatewayPort
      types.py                 公共参数类型：Symbol、TradeDate、IndexCode
      tech.py                  DailyKlinePort、MinuteKlinePort、MinuteInterval
      capital.py               MoneyflowPort、MarginDetailPort、TopListPort、TopInstPort、BlockTradePort、HolderNumberPort
      fundamental.py           DailyBasicPort、FinIncomePort、Top10HoldersPort、Top10FloatHoldersPort
      reference.py             StockBasicPort、AdjFactorPort、SuspendPort、NameChangePort、DividendPort
      concept.py               ConceptListPort、ConceptMembersPort、StockConceptsPort、ConceptIndexDailyPort、ConceptSnapshotPort、ConceptMinutePort
    scheduler_port.py          SchedulerPort
    (collector_port.py / registry.py / realtime_query_port.py 迁移完成后删除)
  service/
    collect_manage_service.py  只依赖端口：方案增删改时注册定时、到点执行 run_plan
    concept_realtime.py        ConceptRealtimeReader：概念实时行情 + 失败降级（见 05）
    data_query_service.py      DataQueryService：按名调用入口（见 06）
    concept_service.py  stock_info_service.py   注入 Gateway；结果组装
infrastructure/
  config/di.py                 setup_default_registry 改为调用 data.setup
  adapter/
    data/                      ← 统一入口 + 横向装饰器 + 第三层底层实现
      core/
        base.py                AdapterBase（实现方属性）
        registry.py            DataPortRegistry（一个 Port → 多个 Adapter）
        gateway.py             DataGateway（门面 + 选源 + 责任链）
        decorators.py          MetricsDecorator / RetryDecorator / ThrottleDecorator
        cache.py               CacheDecorator（原 realtime/framework 的缓存 / 单飞）
        context.py             调用策略、取消检查
      tushare/  client.py parser.py tech.py capital.py fundamental.py reference.py
      adata/    client.py concept.py
      pytdx/    client.py tech.py
      (akshare/ 后续接入)
      setup.py                 启动注册
    collect/                   ← 原 scheduler/collect，整体上移（纯搬迁，最后一步做）
      base.py                  不变：BaseCollectTask / execute_task / run_units / 增量工具
      declarative.py           新增：DeclarativeCollectTask + 规划器
      registry.py              catalog 改为读 Port 元数据
      tasks/
        tushare_tasks.py       14 个按日 / 按股票任务的声明
        daily_kline.py stock_basic.py
        concept.py concept_reason.py concept_snapshot.py planned.py
    scheduler/
      apscheduler_adapter.py   纯 APScheduler 封装：不读仓储、不 import Service
    background/                ← 原 scheduler/ 下的池操作后台任务
      operation_dispatcher.py  task_registry.py
    (fetcher/ 和 realtime/ 删除)
route/
  api/v1/data.py               新增：POST /data/{name}、GET /data/catalog（经 DataQueryService）
  dto/request/*.py             21 个 BO 搬到 application/port/data/，过渡期保留 re-export，P4 删除
```

## 5. 实施阶段

每个阶段都可独立上线。P5 与其他阶段无依赖，可以任意时间做。

| 阶段 | 内容 | 涉及文档 | 完成标志 |
| :-- | :-- | :-- | :-- |
| P1 | 建 `application/port/data` 与 `adapter/data/core`；21 个 BO 搬到 `application/port/data/`（原位置留 re-export）；Tushare 拆成 Client + Adapter；装饰器；Gateway 可用。旧 `TushareFetcher` 保留 | 01 / 02 / 03 | 脚本用 Gateway 取到与旧 fetcher 一致的数据；`application/port/data/` 不 import `route` |
| P2 | 14 个按日 / 按股票任务（含 `fin_report`）改成 `DeclarativeCollectTask`；`daily_kline` / `stock_basic` 改走 Gateway | 04 | 各任务抽样采集写入行数与改前一致；删掉重复的限流代码 |
| P3 | adata / pytdx 拆 Adapter；概念任务改走 Gateway；实时查询并入 Gateway（`CacheDecorator`）；新增 `ConceptRealtimeReader`、`stock_info_service.get_minute_klines`、`DataQueryService` 并替换实时调用方；删除 `realtime/` | 02 / 04 / 05 / 06 §4.1 | 概念采集、分 K、概念分时页面、采集管理"试查"正常 |
| P4 | 业务 Service 改走 Gateway；删除 `collector_port.py`、`FetcherRegistry`、`adapter/fetcher/` | 06 | 全局 grep 不到 `XxxFetcher` / `get_registry()` |
| P5 | 定时调度改造：规则收进 domain 的 `Schedule` 值对象、`SchedulerPort`、`ApschedulerAdapter`；池操作移到 `background/` | 07 | 方案定时触发、下次触发时间显示正常；Service 不再 import 调度器实现 |
| P6 | 新增 `/api/v1/data/*` 与 Agent 工具目录；`scheduler/collect` 上移到 `adapter/collect` | 04 / 06 | 接口可按名调用任意 Port |

## 6. 文档索引

- [00-当前实现总结.md](./00-当前实现总结.md)：P1–P6 完成后代码的实际结构（**先看这篇**；下列 01–07 为设计方案）
- [01-核心骨架.md](./01-核心骨架.md)：DataPort / XxxPort / AdapterBase / Registry / Gateway / DataCommand / 参数约定与时间参数 / BO 位置 / 错误分类 / 选源规则
- [02-底层实现拆分.md](./02-底层实现拆分.md)：Client + Adapter 拆分，18 个协议到 23 个 Port 的对照表
- [03-横向装饰器.md](./03-横向装饰器.md)：Metrics / Retry / Throttle 的顺序、限流分组、可取消等待
- [04-采集任务改造.md](./04-采集任务改造.md)：`DeclarativeCollectTask`、规划器、哪些任务声明式、哪些保留子类
- [05-实时查询并入统一入口.md](./05-实时查询并入统一入口.md)：`CacheDecorator`、降级移到应用层、`realtime/` 删除
- [06-统一入口与对外暴露.md](./06-统一入口与对外暴露.md)：业务 Service 接入、`DataQueryService`、HTTP / Agent、目录统一、旧代码删除清单
- [07-定时调度改造.md](./07-定时调度改造.md)：`Schedule` 值对象、`SchedulerPort`、`ApschedulerAdapter`

## 7. 不在本次范围

- 应用服务 import `route/dto` 的问题（`stock_info_service`、`concept_service`、`stock_pool_service` 等引用请求 / 响应 DTO）。本次只搬 Port 用到的 21 个 BO，其余 DTO 另开文档。
- `collect_plan` 聚合根实体化（`CollectManageService` 仍直接用 ORM 模型），见 07 §9。
- 新数据源（akshare / 东财）只预留结构，实际接入另开文档。
- 多副本部署下的分布式限流和调度互斥，本次不做（与现在一样按单进程设计）。
- 分 K 入库、新闻采集（`planned.py` 里的占位）不变。
