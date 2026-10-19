# 03 collect 优化：采集任务上移到应用层

> 前置：[02底层采集优化](../02底层采集优化/README.md) P1–P6 已完成（取数统一走 `DataGateway`，定时走 `SchedulerPort`）。
> 本文只是方案，**尚未修改代码**。

## 1. 问题

`infrastructure/adapter/collect/` 里的采集任务，本质是应用层的用例编排（"把 X 采集入库"），却放在 infra。原因不是它本身属于 infra，而是它**直接依赖了一批 infra 实现**：

| 依赖 | 出现位置 |
| :-- | :-- |
| `get_data_gateway()` 单例 | `declarative.py`、`concept*.py` |
| ORM 模型列（`CapMoneyflowDB.trade_date` 等）做增量跳过 | `tushare_tasks.py` 的 `existing_column`、`base.py` 的 `existing_dates` / `existing_symbols` |
| 仓储实现 `XxxRepoImpl` + `AsyncSessionLocal` | `declarative.py`、`concept.py`、`daily_kline.py`、`stock_basic.py` |
| 直接写 SQL（`select(ConceptMemberDB)` / `session.add(ConceptSnapshotDB)` / `select(StockInfoDB)` / `select(TechKlineDailyDB)`） | `concept_reason.py`、`concept_snapshot.py`、`daily_kline.py`、`declarative.py` 的 `SymbolPlanner` |
| `SysCollectTaskDB` 任务行 + `get_redis()` 进度 | `base.py` 的 `execute_task` / `_finish_task` / `_update_progress` |
| `di.build_stock_info_service` 反向 import | `daily_kline.py`、`stock_basic.py` |
| `get_settings()` | `daily_kline.py` |
| `cancel_check` contextvar（定义在 `infrastructure/adapter/data/core/context.py`） | `base.py` |

连带问题：

- `CollectManageService`（应用层）import 了 `infrastructure.adapter.collect` 的 `execute_task` / `BaseCollectTask`，还直接读写 `SysCollectTaskDB`，违反 DDD.md §4（应用层只依赖 port）。
- 纯业务规则散落在编排代码里："任务最终状态判定"在 `base._decide_status`，"方案失败即停"写在 `run_plan` 的 if 里。

## 2. 分层原则

判断标准：**有没有 IO**。

| 层 | 放什么 | 判断 |
| :-- | :-- | :-- |
| `domain` | 纯业务规则 | 不依赖任何 port，给定输入算出结果，可脱离数据库单测 |
| `application` | 用例编排 | 按顺序调用多个 port（取数 / 入库 / 进度 / 任务状态），把领域规则串成一件完整的事 |
| `infrastructure` | port 的具体实现 | SQLAlchemy、Redis、SDK |

collect 内部的内容按此拆分：

| 内容 | 性质 | 改造后位置 |
| :-- | :-- | :-- |
| 清单缩量保护、成分股骤降保护（`ConceptCollectionPolicy`） | 纯规则 | `domain/service/`（已在，不动） |
| 定时规则（间隔 ≥ 30 秒、每天 ≤ 24 个时间点） | 纯规则 | `domain/entitys/collect_plan/vo.py`（02 P5 已放好，不动） |
| 任务最终状态判定（零成功且有失败 → failed） | 纯规则 | **新增** `domain/entitys/collect_task/vo.py` 的 `TaskOutcome`（01） |
| 方案"失败即停"判定 | 纯规则 | **新增** `domain/entitys/collect_plan/vo.py` 的 `PlanStopPolicy`（01） |
| 日 K 增量窗口裁剪、按交易日 / 按股票拆单元、增量跳过 | 编排策略（规则很薄） | `application/collect/` |
| 取数 → 转换 → 入库、进度、取消、并发、重试、任务状态 | 编排 | `application/collect/` |
| `task_type` 注册表、目录 | 应用层元数据 | `application/collect/registry.py` |
| 入库 / 查询 / 任务行 / 进度的具体实现 | IO | `infrastructure/persistence/collect/`、`infrastructure/adapter/cache/` |

## 3. 改造后的依赖方向

```
route/api/v1/collect_task.py
      │
      ▼
application/service/collect_manage_service.py   对外入口（不变）
      │
      ▼
application/collect/        采集用例子系统（新）
  task / runner / registry / declarative / planners / tasks/*
      │                     │
      ▼                     ▼
application/port/           domain/
  data/（已有）               collect_task/vo.py（新：TaskOutcome）
  collect_port.py（新）        collect_plan/vo.py（Schedule + PlanStopPolicy）
      ▲                       service/concept_collection_policy.py（已有）
      │ 实现
infrastructure/
  persistence/collect/*     入库 / 查询 / 任务行
  adapter/cache/collect_progress.py   Redis 进度
  adapter/data/*            Gateway（已有）
  config/di.py              组装 CollectContext
```

验收：`application/` 下 grep 不到 `infrastructure.`。

## 4. 关键决策

### 4.1 原始数据表入库：通用入库端口，实现先委托现有仓储

14 张原始数据表（资金面 6、基本面 4、基础面 4）由声明式任务写入。可选方案：

| 方案 | 做法 | 代价 |
| :-- | :-- | :-- |
| A 严格 DDD | 每张表补领域仓储接口方法（`existing_trade_dates` 等），任务声明领域接口，infra 做接口 → 实现映射 | 14 套"实体 + 接口 + 实现"全部要补齐和维护 |
| **B 通用入库端口（采用）** | 一个 `RawDataStorePort.save(port, items)` / `existing(port, units)`；infra 实现内部按 Port 名查表，**委托现有 `XxxRepoImpl.save_batch`** | 新增一张映射表；写入逻辑一行不改 |

选 B 的理由：

- 任务声明里不再出现 ORM 和仓储实现，只剩"用哪个 Port"。
- 写入语义零变化：各表 upsert 策略不同（`cap_top_inst` 是 `on_conflict_do_nothing`，其他是按唯一约束 upsert），委托现有实现可以完全保留。
- `route/api/v1/data_board.py` 仍在用这 14 个 `XxxRepoImpl` 的读方法，本次不动它们。

**本次不删**原始数据表的领域实体和 BO 的 `to_entity()`（`RawDataStore` 实现仍用它们转换）。是否删除见 §7。

### 4.2 端口实现自管 session

现在每个单元"自开 session、自 commit"。新端口保持这个语义：**每个端口方法是一个独立事务**，实现内部用 `AsyncSessionLocal` 开关 session。应用层不感知 session，不引入 Unit of Work。

个别现在在同一 session 里的"先查后写"（如成分股：先 `count_members` 再 `replace_members`）会拆成两次调用。`ConceptRepoImpl` 的写方法本来就各自 `commit`，事务边界实际不变；同一 `task_type` 有防重（`TaskConflict`），也不存在并发写（04 §5.1 逐个说明）。

### 4.3 依赖通过 CollectContext 注入

任务在启动时注册为单例。由 `di` 组装一个 `CollectContext`（gateway / 各端口 / Service 工厂 / 并发配置），注册表在 `setup` 时统一绑定到每个任务。声明式任务的类定义写法不变（03 §3）。

## 5. 文档目录

| 文档 | 内容 |
| :-- | :-- |
| [01-领域规则下沉](01-领域规则下沉.md) | `TaskOutcome`、`PlanStopPolicy` |
| [02-端口与基础设施实现](02-端口与基础设施实现.md) | `collect_port.py` 的 6 个端口；infra 实现；`cancel_check` 契约上移 |
| [03-应用层采集框架](03-应用层采集框架.md) | `task.py` / `runner.py` / `registry.py` / `context.py` / `planners.py` / `declarative.py`；`CollectManageService` 改动 |
| [04-任务迁移](04-任务迁移.md) | 23 个任务逐个迁移：声明式 14 个、日 K、股票清单、概念 5 个、占位 2 个 |

## 6. 实施阶段

| 阶段 | 内容 | 文档 | 验收 |
| :-- | :-- | :-- | :-- |
| C1 | 新增 `TaskOutcome` / `PlanStopPolicy`；`base._decide_status` 和 `run_plan` 改为调用它们。新增 `application/port/collect_port.py`；`cancel_check` 定义上移到 `application/port/data/context.py` | 01 / 02 §1–2 | 单测覆盖两条规则；行为不变 |
| C2 | infra 实现 6 个端口（`persistence/collect/*`、`cache/collect_progress.py`），**旧代码暂不切换** | 02 §3 | 脚本对比：同一交易日用新 `RawDataStore` 写入与旧 `collect_one` 行数一致；`existing` 结果一致 |
| C3 | 框架上移：`application/collect/{task,runner,registry,context,planners,declarative}.py`；`execute_task` → `CollectRunner`（用 `CollectTaskStorePort` + `CollectProgressPort`）；`CollectManageService` 改用新框架和端口；`di` 组装 `CollectContext` | 03 | 手动提交、进度、取消、重跑、方案执行、定时触发正常 |
| C4 | 任务迁移：14 个声明式任务改用 `RawDataStorePort`；日 K / 股票清单经 `ctx` 拿 Service 和查询端口；概念 5 个改用 `ConceptStorePort`；删除 `infrastructure/adapter/collect/` | 04 | 各任务抽样 `collect_one` 与改前写入行数、跳过数、汇总文案一致 |
| C5 | 清理与文档：`main.py` 注册改为 `all_collect_tasks()`；overview 文档更新 | — | `application/` grep 不到 `infrastructure.`；`/collect/catalog` 输出与改前一致 |

每阶段结束都做导入检查 + 启动验证（同 02 的做法，验证脚本放 `E:\codes\_backup\`，用完删）。

## 7. 不在本次范围

| 项 | 说明 |
| :-- | :-- |
| 删除 14 张原始数据表的领域实体 / 仓储接口 / BO 的 `to_entity()` | 这些实体没有任何业务方法。等 `data_board.py` 的读查询改走应用层 Service 后，再评估改为 `RawDataStore` 直接按 BO 入库、读侧直接返回 dict |
| `collect_plan` 聚合根（实体 + 仓储接口） | `CollectManageService` 仍直接使用 `CollectPlanDB` / `CollectPlanItemDB` / `CollectFetcherDB`（02 / 07 §9 已记录） |
| `route/api/v1/collect_task.py` 直接查 `SysCollectTaskDB` / Redis（任务列表、详情、进度、强制取消） | 路由越过应用层，属于另一类问题；本次只把它对 `infrastructure.adapter.collect` 的 import 改到应用层 |
| `StockInfoService.collect` 入参是 `route.dto.request.kline.KlineCollectRequest` | 应用层依赖 route DTO，属既有问题；日 K 任务沿用 |

## 8. 兼容性约束

对外全部不变：`task_type` 名称、默认参数 / 全量参数、汇总文案、`sys_collect_tasks` 表、Redis 进度 key `collect:progress:{task_id}` 及字段、`/api/v1/collect/*` 接口、`/collect/catalog` 结构、前端页面、`CollectManageService.run_one` 返回的 `UnitResult.data`（业务路由依赖）。
