# 08 · Session 注入修正方案

> 编制日期：2026-10-20
> 状态：**待评审**（本次只出方案，不改代码）
> 范围：`backend/src/contexts/collect` 全部 28 个 service + TaskRunner + CollectLogService + DI 工厂
> 触发事件：日 K 线采集"没反应"，日志卡在 `running`，后台抛 `InFailedSQLTransactionError`

---

## 一、事故现象与根因速览

### 1.1 现象

前端点"日 K 线采集"，任务派发后无任何进展，`GET /api/collect/logs/daily_kline` 持续返回 `status=running`，
后端日志刷出（自下而上）三层异常：

| 层级 | 异常 | 真实含义 |
|---|---|---|
| ① | `asyncpg.exceptions.UndefinedTableError`（**已被滚动出屏，仓库里查不到**） | `relation "tech_kline_daily" does not exist` |
| ② | `asyncpg.exceptions.InFailedSQLTransactionError` | ①把事务置为 aborted，后续所有 SQL 被拒 |
| ③ | `sqlalchemy.exc.IllegalStateChangeError` | session 在 `_connection_for_bind()` 进行中被 close |

### 1.2 根因一句话

> **`CollectTaskRunner` 绕过 DI 工厂，硬编码用业务库 session 构造 service，导致 raw_data 库的表被拿到 attribution 库里写。**

### 1.3 关键发现：不止日 K 一个坏了

排查后发现**注入错误是系统性的**，全模块 28 个 service 中：

- **24 个 service 的日志写入是错的**（日志 session 指向 raw_data 库）
- **1 个 service 的数据写入是错的**（日 K，session 指向 attribution 库）
- **只有 1 个 service（`stock_basic`）是全对的** —— 这正是"股票基本信息跑通了"的原因，它是唯一显式区分了两个 session 的工厂

> ⚠️ 这意味着其余 24 个 service 很可能**在 `create_pending()` 这一步就已经 500 了**，只是尚未被触发测试到。

---

## 二、事实基础：表 → 数据库归属对照表

### 2.1 双库物理隔离

项目有两个 PostgreSQL 库，由 `backend/src/shared/infrastructure/persistence/orm_base.py` 的两个声明基类区分：

| 基类 | 物理库 | URL 配置项 | 环境变量实际值 |
|---|---|---|---|
| `AttribBase`（别名 `Base`） | attribution_db | `DATABASE_URL` | `postgresql+asyncpg://zhouch:***@8.148.204.54:5432/attribution` |
| `RawBase` | raw_data_db | `RAW_DATABASE_URL` | `postgresql+asyncpg://zhouch:***@8.148.204.54:5432/raw_data` |

**两个库物理隔离，不是同一实例的 schema。** 表在 A 库，B 库的 session 绝对访问不到。

### 2.2 全量 ORM 归属清单（代码实测）

用 `grep '^class \w+\((RawBase|AttribBase)'` 全量扫描 `contexts/` 得到：

#### 业务库（attribution_db）— collect 模块只有 1 张表

| 表名 | ORM 类 | 文件 |
|---|---|---|
| `collect_logs` | `CollectLogDB` | `collect/infrastructure/persistence/models/collect_log.py` |

其余 9 张（`sys_users` / `sys_roles` / `sys_permissions` / `stock_pools` / `stock_pool_members` /
`pool_operations` / `collect_schedule` / `collect_run_log` / `sys_user_roles` / `sys_role_permissions`）
属于 auth / user / scheduler 模块，不在本次范围。

#### 采集库（raw_data_db）— 28 张表，全部属于 collect 写入目标

| 表名 | ORM 类 | 归属模块 |
|---|---|---|
| `tech_kline_daily` | `TechKlineDailyDB` | market |
| `tech_adj_factor` | `BaseAdjFactorDB` | market |
| `tech_suspend` | `BaseSuspendDB` | market |
| `tech_name_change` | `BaseNameChangeDB` | market |
| `tech_calendar` | `MktCalendarDB` | market |
| `capital_moneyflow` | `CapMoneyflowDB` | market |
| `capital_moneyflow_hsgt` | `CapitalMoneyflowHsgtDB` | collect |
| `capital_top_list` | `CapTopListDB` | market |
| `capital_top_inst` | `CapTopInstDB` | market |
| `capital_block_trade` | `CapBlockTradeDB` | market |
| `capital_margin` | `CapMarginDB` | market |
| `capital_margin_detail` | `CapMarginDetailDB` | market |
| `capital_holder_num` | `CapHolderNumDB` | market |
| `capital_hsgt_top10` | `CapitalHsgtTop10DB` | collect |
| `capital_limit_list_d` | `CapitalLimitListDDB` | collect |
| `fundamental_stock_info` | `StockInfoDB` | market |
| `fundamental_daily_basic` | `FinDailyBasicDB` | market |
| `fundamental_report` | `FinReportDB` | market |
| `fundamental_top10` | `FinTop10HolderDB` | market |
| `fundamental_top10_float` | `FinTop10FloatHolderDB` | market |
| `fundamental_dividend` | `BaseDividendDB` | market |
| `fundamental_market_daily` | `MktMarketDailyDB` | market |
| `fundamental_sector_daily` | `MktSectorDailyDB` | market |
| `fundamental_index_member` | `MktIndexMemberDB` | market |
| `fundamental_concept` | `ConceptsDB` | concept |
| `fundamental_concept_member` | `ConceptMemberDB` | concept |
| `fundamental_concept_snapshot` | `ConceptSnapshotDB` | concept |
| `fundamental_concept_index` | `ConceptIndexTHDB` | concept |
| `fundamental_stock_concept` | `FundamentalStockConceptDB` | collect |
| `news_article` | `NewsArticleDB` | collect |

**dump 文件交叉验证**（`backend/*.sql`）：

- `raw_data-2026-10-18_150731-dump.sql` → 24 张 `CREATE TABLE`，含全部 `tech_*` / `capital_*` / `fundamental_*`
- `attribution-2026-10-19_130507-dump.sql` → 10 张，全是 `sys_*` / `stock_pool*` / `collect_schedule`
- `collect_logs` 两个 dump 里都没有 → 它由 `main.py` 启动时 `ensure_attrib_tables()` 在 attribution 库动态创建

> ✅ **结论：collect 模块的"采集数据 100% 在 raw_data 库，日志 100% 在 attribution 库"，没有例外。**

### 2.3 session 工厂语义

`backend/src/shared/infrastructure/di/db_session.py` 提供 4 个入口：

| 工厂 | 绑定库 | 生命周期 | 用途 |
|---|---|---|---|
| `get_db()` | attribution | Depends 请求级 | Route 层业务查询 |
| `get_raw_db()` | raw_data | Depends 请求级 | Route 层采集查询 |
| `get_db_context()` | attribution | `async with` 独立事务 | Service 层独立事务 |
| `get_raw_db_context()` | raw_data | `async with` 独立事务 | Service 层独立事务 |

**两者互不干扰，各自一个 session 各自一个事务。**

---

## 三、Bug 清单（按严重度）

### 🔴 BUG-1（P0）TaskRunner 绕过 DI，硬编码业务库 session

**位置**：`infrastructure/adapter/background/collect_task_runner.py:98-116`

```python
async with get_db_context() as session:          # ← 永远是 attribution_db
    log_service = CollectLogService(session=session, redis_client=redis)
    svc = service_class(
        session=session,                        # ← 无视 DI 配置，传给 service
        log_service=log_service,
        task_runner=self,
    )
```

**问题**：Runner 完全不经过 FastAPI 的 `Depends` 体系，自己开一个 session 传给 service。
DI 工厂里写的 `Depends(get_raw_db)` 对后台任务**完全无效**。

**影响**：**全部 25 个持 session 的 service**，后台执行时数据写入全部打到 attribution 库 → `UndefinedTableError`。

**为什么 stock_basic 幸免**：它在 `_run_collect` 内部自己开 raw session，绕过了注入的 session：

```218:221:backend/src/contexts/collect/application/service/fundamental/stock_basic_service.py
            from shared.infrastructure.di.db_session import get_raw_db_context
            async with get_raw_db_context() as raw_session:
                saved = await self._stock_repo.replace_all(
```

**讽刺之处**：TaskRunner 类注释第 4 行明确写着"**不持有父请求的 session！后台任务必须自己创建独立 session**"，
但实现恰恰相反——它创建的是**写死的、错库的** session。

---

### 🔴 BUG-2（P0）24 个 DI 工厂把 raw_data session 注入给了日志服务

**位置**：`infrastructure/di/collect_service.py` 中 `_make_log_service(session, redis)` 的 24 处调用

```32:37:backend/src/contexts/collect/infrastructure/di/collect_service.py
def _make_log_service(session: AsyncSession, redis) -> CollectLogService:
    """构造日志服务（统一 helper）

    99% 场景下 session = log_session；只有 stock_basic 例外（session=raw_db, log_session=attribution_db）。
    """
    return CollectLogService(session=session, redis_client=redis)
```

**问题**：24 个工厂的 `session` 来自 `Depends(get_raw_db)`，然后原样传给 `_make_log_service`。
`CollectLogService` 用它执行 `INSERT INTO collect_logs` / `UPDATE collect_logs`，
而 `collect_logs` **在 attribution 库**，raw_data 库没有这张表。

**影响**：这 24 个 service 调用 `collect()` → `create_pending()` 时**第一步就抛 `UndefinedTableError`**，
HTTP 端点直接 500，任务根本派发不出去。

**工厂统计实测**：

| 工厂传入的 session | 数量 | 正确性 |
|---|---|---|
| `session`（来自 `get_raw_db`） | **24** | ❌ 日志写错库 |
| `log_session`（来自 `get_db`） | **1**（`get_stock_basic_service:448`） | ✅ 唯一正确 |
| `session`（来自 `get_db`） | **1**（`get_daily_kline_service:54`） | ⚠️ 日志对、数据错库 |

---

### 🟠 BUG-3（P1）日 K 线 DI 工厂用了业务库 session

**位置**：`infrastructure/di/collect_service.py:44-56`

```44:56:backend/src/contexts/collect/infrastructure/di/collect_service.py
def get_daily_kline_service(
    session: AsyncSession = Depends(get_db),      # ← 全模块唯一用 get_db 的
    redis=Depends(get_redis),
):
    """日 K 线 service（写业务库 kline，用 get_db）— ★ Phase 2 已升级"""
```

**问题**：28 个工厂里**只有它**用 `Depends(get_db)`。docstring 里的"写业务库 kline"是错的——
`tech_kline_daily` 是 `RawBase`，在 raw_data 库。

**注意**：这个错误和 BUG-2 方向**相反**，所以日 K 反而是唯一能成功建日志的（只是数据写不进去）。
这就是为什么"日志能创建、但数据没反应"。

---

### 🟠 BUG-4（P1）9 个 service 并发共享同一个 AsyncSession

**位置**：`ServiceMeta.concurrency > 1` 但所有协程共用 `self._session`

| service | concurrency |
|---|---|
| `daily_kline` | 5 |
| `adj_factor` | 5 |
| `holder_number` | 5 |
| `dividend` | 5 |
| `fin_income` | 5 |
| `top10_holders` | 5 |
| `top10_floatholders` | 5 |
| `stock_concepts` | 5 |
| `concept_members` | 3 |

典型写法（`daily_kline_service.py:152-163`）：

```python
sem = asyncio.Semaphore(self.META.concurrency)   # 5
tasks = [asyncio.create_task(one(s)) for s in symbols]
for coro in asyncio.as_completed(tasks):
    yield await coro
    # one() 内部：await self._repo.save(bos, self._session)   ← 5 个协程抢 1 个 session
```

**问题**：`AsyncSession` **不是并发安全的**。单条 asyncpg 连接上的多条 SQL 无法真正并行；
更严重的是事务边界被多个协程交错污染，一条失败会 abort 掉其他协程正在进行的语句。

**这就是 BUG-5 的放大器**。

---

### 🟠 BUG-5（P1）日 K 重试循环不 rollback，掩盖首个真实错误

**位置**：`application/service/tech/daily_kline_service.py:175-186`

```python
for attempt in range(3):
    try:
        ...
        return await self._save(symbol, klines)
    except Exception as e:
        if attempt < 2:
            await asyncio.sleep(1)      # ← 在同一段已 abort 的事务上重试
        else:
            raise
```

**问题**：第 1 次 `_save` 抛 `UndefinedTableError`（事务 abort）→ 第 2、3 次重试
在同一段已 abort 的事务上执行 → 全部变成 `InFailedSQLTransactionError`。
**真正有用的错误信息被 2 次噪音覆盖并滚出屏幕**。

---

### 🟡 BUG-6（P1）`mark_failed` 复用被污染的 session，导致状态永久卡死

**位置**：`infrastructure/adapter/background/collect_task_runner.py:160-172`

```python
except Exception as e:
    await log_service.mark_failed(...)   # ← 用同一段已被 abort 的 session
```

**级联**：
1. 数据写入失败 → 事务 abort
2. `mark_failed` 在同一 session 上执行 → 又抛 `InFailedSQLTransactionError`
3. 异常逃出 `except` 块 → 抛给 `get_db_context.__aexit__`
4. `session.close()` 撞上 `_connection_for_bind()` 进行中 → `IllegalStateChangeError`
5. **`collect_logs.status` 永久停留在 `running`**（`mark_running` 早已 commit 成功，`mark_failed` 没 commit 成功）

**这就是"日 K 没反应"的直接成因** —— 前端拿到的是一个永远不会结束的 `running`。

---

### 🟡 BUG-7（P2）`base.py` 全量概念查询：用错库 + 类名错误 + 静默吞异常

**位置**：`application/service/base.py:225-246`

```python
from shared.infrastructure.connection.db_factory import db_session_factory   # ← 业务库
from contexts.concept.infrastructure.persistence.models.concept import ConceptDB   # ← 类名不存在
async with db_session_factory() as session:
    rows_db = (await session.execute(select(ConceptDB.index_code))).scalars().all()
    ...
except Exception as e:
    logger.warning("list_all_concept_codes 失败: %r", e)
    return []      # ← ImportError 被吞掉，静默返回空
```

三重问题：

1. **用错库**：`db_session_factory` 是 attribution 库，`ConceptsDB` 是 `RawBase`（在 raw_data 库）
2. **类名不存在**：实际类名是 `ConceptsDB`（多个 `s`），不是 `ConceptDB` → `ImportError`
3. **静默吞异常**：`except Exception` 兜底返回 `[]`，只打一条 warning

**影响**：`concept_members` / `concept_index_daily` 的"全量模式"永远拿不到 concept 列表，
用户不传 `index_codes` 时静默采集 0 条，**没有任何报错**。

---

### 🟡 BUG-8（P2）`concept_snapshot` 类型不一致

**位置**：`application/service/fundamental/concept_snapshot_service.py`

`META.kind = ServiceKind.REALTIME`，但却完整注入了 `session` + `log_service` + `task_runner`，
且实现了 `_run_collect()` 走采集入库路径。

其他 2 个 REALTIME service（`minute_kline` / `concept_minute`）都没有这些注入。
按 `base.py` 的 Protocol 注释，REALTIME service "可以 noop yield，主要走 `get()`"。
这导致 CatalogService 的 `supports_query` 语义和实际行为不符。

---

## 四、目标架构

### 4.1 核心原则：谁的数据谁开 session

```
┌──────────────────────────────────────────────────────────────┐
│  组件              持有 session？   库            职责          │
├──────────────────────────────────────────────────────────────┤
│  CollectLogService     ✅ 自管      attribution   日志 CRUD     │
│  CollectTaskRunner     ❌ 完全不持有  —            纯调度       │
│  XxxCollectService     ✅ 注入      raw_data      采集数据读写  │
└──────────────────────────────────────────────────────────────┘
```

三条铁律：

1. **TaskRunner 不持有任何 session** —— 回归纯调度器（`create_task` + 进度聚合）
2. **service 的 `session` 语义统一为"raw_data 库"** —— 28 个工厂签名一致，无特例
3. **CollectLogService 自管 attribution 库 session** —— 每个写方法一个短事务

### 4.2 为什么 TaskRunner 可以不持有 session

关键依据：`CollectLogRepository` 的**每个写方法都自己 commit**：

| 方法 | commit？ | 用在哪 |
|---|---|---|
| `create()` | ✅ `repository.py:63` | `create_pending` |
| `update_status()` | ✅ `repository.py:87` | `mark_running` |
| `finish()` | ✅ `repository.py:122` | `mark_finished` / `mark_failed` |
| `update_progress()` | ❌ 只写 Redis，不碰 DB | 实时进度 |

**日志写入和业务数据写入本来就不在同一个事务里**（物理上是两个库，天然不可能同事务）。
既然如此，TaskRunner 持有 session 没有任何事务语义上的收益，纯粹是"为了传而传"的中转。

### 4.3 改造后的调用链

```
HTTP: svc.collect(params)
  └─ log_service.create_pending()          → 内部开 attribution session，写完即关
  └─ task_runner.dispatch(...)             → create_task，立即返回

后台: TaskRunner._run()
  └─ log_service = CollectLogService(redis)        ← 不传 session
  └─ async with get_raw_db_context() as raw_session:
       svc = service_class(
           session=raw_session,                    ← raw_data 库
           log_service=log_service,
           task_runner=self,
       )
       await log_service.mark_running()           → 内部开 attribution session
       async for batch in svc._run_collect(...):
           await log_service.update_progress()    → 只写 Redis
       await log_service.mark_finished()          → 内部开 attribution session
  └─ except:
       await log_service.mark_failed()            → 内部开 attribution session（永远干净）
```

### 4.4 职责边界对照

| 依赖 | 类型 | 库归属 | 是否必要 |
|---|---|---|---|
| `session` | `AsyncSession` | **raw_data** | 采集数据读写 |
| `log_service` | `CollectLogService` | attribution（内部自管） | 建日志 + 失败回滚 |
| `task_runner` | `CollectTaskRunner` | — （纯内存） | 后台派发 |
| `repo` / `fetcher` | — | — | 由 service 默认构造 |

---

## 五、改造方案（逐文件）

> ⚠️ 以下为**方案描述**，本次不改代码。

### 5.1 `CollectLogService` — 自管 session

**文件**：`application/service/manage/collect_log_service.py`

**改前**：
```python
def __init__(self, session: AsyncSession, redis_client) -> None:
    self._session = session
    self._redis = redis_client
    self._repo = CollectLogRepository(session)
```

**改后**：移除 `session` 参数，改为方法内自开短事务。

```python
def __init__(self, redis_client) -> None:
    self._redis = redis_client
    # 不再持有 session / repo

# 内部 helper
@asynccontextmanager
async def _ctx(self):
    """每次日志写入开一个独立的 attribution 库短事务"""
    from shared.infrastructure.di.db_session import get_db_context
    async with get_db_context() as s:
        yield s
```

每个 DB 写方法改为：
```python
async def create_pending(self, ...) -> str:
    log_id = str(uuid.uuid4())
    async with self._ctx() as s:                    # ← 独立事务
        await CollectLogRepository(s).create(...)
    await self._redis.hset(...)                     # ← Redis 部分照旧
    return log_id
```

涉及方法：`create_pending` / `mark_running` / `mark_finished` / `mark_failed` / `recover_orphan_logs`
（`list_logs` / `get_log` / `update_progress` 也要走 `_ctx()` 或改为方法内开 session）

> ⚠️ `recover_orphan_logs` 内部有 `select` → 循环 `finish` → `commit` 的多步操作，
> 需保持单事务语义（开一个 session 走完整个流程）。

---

### 5.2 `CollectTaskRunner` — 去掉业务库 session，改为 raw session

**文件**：`infrastructure/adapter/background/collect_task_runner.py`

**改前**：
```python
from shared.infrastructure.di.db_session import get_db_context
async with get_db_context() as session:              # ← attribution
    redis = await get_redis()
    log_service = CollectLogService(session=session, redis_client=redis)
    svc = service_class(session=session, log_service=log_service, task_runner=self)
```

**改后**：
```python
from shared.infrastructure.di.db_session import get_raw_db_context
redis = await get_redis()
log_service = CollectLogService(redis_client=redis)   # ← 不传 session

async with get_raw_db_context() as raw_session:        # ← raw_data
    svc = service_class(
        session=raw_session,
        log_service=log_service,
        task_runner=self,
    )
    ...                                                # 原有逻辑不变
```

**额外改动**：`except` 分支里给 `mark_failed` 加保护，杜绝状态再次卡死：

```python
except Exception as e:
    logger.exception(...)
    try:
        await log_service.mark_failed(...)     # 现在内部开新 session，一定干净
    except Exception as e2:
        # 兜底：连日志都写不进去时，至少不能让它逃逸导致 IllegalStateChangeError
        logger.error("mark_failed 失败: %r", e2)
```

---

### 5.3 28 个 DI 工厂 — 签名统一

**文件**：`infrastructure/di/collect_service.py`

| 改动项 | 现状 | 目标 |
|---|---|---|
| `_make_log_service` | `(session, redis)` | 删除该 helper，改为 `CollectLogService(redis_client=redis)` |
| `session` 来源 | 24 个 `get_raw_db` + 1 个 `get_db`（日K） | **28 个全部 `get_raw_db`** |
| `log_session` 参数 | `get_stock_basic_service` 独有 | **删除**（不再需要区分） |
| 工厂 docstring | 提到"双 session 架构" | 删除该描述 |

**改造后的标准工厂模板**：
```python
def get_xxx_service(
    repo=Depends(...),
    session: AsyncSession = Depends(get_raw_db),   # ← 统一
    redis=Depends(get_redis),
):
    return XxxService(
        repo=repo,
        session=session,
        log_service=CollectLogService(redis_client=redis),   # ← 不传 session
        task_runner=get_collect_task_runner(),
    )
```

**3 个无 session 的工厂保持不变**：`get_minute_kline_service` / `get_concept_minute_service` / `get_sentiment_service`

---

### 5.4 `get_stock_basic_service` — 删除双 session 特例

**文件**：`infrastructure/di/collect_service.py:428-451`

- 删除 `log_session: AsyncSession = Depends(get_db)` 参数
- `log_service=_make_log_service(log_session, redis)` → `CollectLogService(redis_client=redis)`
- 删除 12 行 docstring 中的"双 session 架构"说明

**同时**：`application/service/fundamental/stock_basic_service.py:194, 218` 的
`get_raw_db_context()` 内部兜底可以删掉，回归使用 `self._session`（此时已是正确的 raw session）。
不过保留也无害，**建议保留**作为过渡，等全部改完验证通过后再清理。

---

### 5.5 `daily_kline_service.py` — 补 rollback，修并发

**文件**：`application/service/tech/daily_kline_service.py`

**改动 1**：`_collect_one` 重试前 rollback（`:175-186`）
```python
except Exception as e:
    if attempt < 2:
        await self._session.rollback()      # ← 新增：清掉 abort 状态
        await asyncio.sleep(1)
    else:
        raise
```

**改动 2**：`_save` 里移除误导性的 `ImportError` 兜底（`:195-201`）。
当前写法在模型 import 失败时静默 `return 0`，会让"表不存在"变成"采到 0 条"，
反而更难排查。应改为显式抛错。

---

### 5.6 `base.py` — 修全量概念查询

**文件**：`application/service/base.py:225-246`

```python
async def list_all_concept_codes() -> list[str]:
    from sqlalchemy import select
    from shared.infrastructure.connection.db_factory import raw_session_factory   # ← raw_data
    from contexts.concept.infrastructure.persistence.models.concept import ConceptsDB  # ← 补 s

    try:
        async with raw_session_factory() as session:
            rows = (await session.execute(
                select(ConceptsDB.index_code)
            )).scalars().all()
            return [str(c) for c in rows if c]
    except Exception as e:
        logger.error("list_all_concept_codes 失败: %r", e)   # ← warning → error
        raise                                                # ← 不再静默返回 []
```

**语义变更**：全量模式拿不到 concept 列表时**应该抛错**（用户明确要求全量却失败了），
而不是静默采集 0 条。

---

### 5.7 并发策略（需决策，见 §七）

三选一，**推荐方案 A**：

| 方案 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| **A（推荐）** | service 持 1 个 raw session，9 个 service 的 `concurrency` 改 1 | 改动最小，完全匹配"注入 raw session"设计 | 采集串行，速度变慢 |
| B | service 不持 session，`_save()` 每次 `async with get_raw_db_context()` | 每 symbol 独立事务，并发安全 | 每 symbol 一次连接（`NullPool` 下有握手开销） |
| C | 建 size=concurrency 的 session 池，每协程 checkout 一个 | 性能与安全兼得 | 改动最大，需引入池抽象 |

> 📌 补充事实：两个 engine 都配了 `poolclass=NullPool`，**没有连接池复用**。
> 方案 A 复用单连接，实际**比**方案 B 少很多次 TCP+认证握手，对 5000 只股票的全量采集影响不小。
> tushare 侧限流是 200 次/60 秒，串行采集本来也打不满配额，所以方案 A 的性能损失可接受。

---

## 六、改造清单

| # | 文件 | 改动类型 | 影响面 |
|---|---|---|---|
| 1 | `application/service/manage/collect_log_service.py` | 重构：自管 session | 日志子系统全部 |
| 2 | `infrastructure/adapter/background/collect_task_runner.py` | 改：`get_db_context`→`get_raw_db_context`；`mark_failed` 加保护 | 全部后台任务 |
| 3 | `infrastructure/di/collect_service.py` | 改：删 `_make_log_service` + `log_session`；28 工厂统一 `get_raw_db` | 全部 service 装配 |
| 4 | `infrastructure/di/log_service.py` | 改：去掉 `session` Depends | 日志查询端点 |
| 5 | `main.py` | 改：`recover_orphan_logs` 调用处去掉 session 传参 | 启动流程 |
| 6 | `application/service/tech/daily_kline_service.py` | 改：重试前 rollback；清理误导性兜底 | 日 K |
| 7 | `application/service/base.py` | 改：修 `list_all_concept_codes` 库/类名/异常语义 | concept 系 |
| 8 | 9 个 service 的 `ServiceMeta` | 改：`concurrency` → 1（方案 A） | 并发采集 |
| 9 | `application/service/fundamental/stock_basic_service.py` | 可选：删内部 raw session 兜底 | 建议延后 |

**不需要改动**：全部 route 层（`_run()` 只调 `svc.collect()`，与 session 无关）、全部 fetcher、全部 ORM 模型。

---

## 七、待决策项

| # | 决策点 | 选项 | 建议 |
|---|---|---|---|
| D1 | 并发策略 | A(并发=1) / B(每次开session) / C(池化) | **A**，见 §5.7 |
| D2 | `CollectLogService` 是否保留 `session` 构造参数作为可选覆盖 | 保留(默认None时自开) / 删除 | **删除**，签名干净；如需测试可另加测试 fixture |
| D3 | `list_all_concept_codes` 失败时抛错还是返回 `[]` | 抛错 / 返回空 | **抛错**（当前静默是隐性 bug 源） |
| D4 | `stock_basic` 内部 `get_raw_db_context` 兜底何时清理 | 本次清 / 下一轮清 | **下一轮**，先验证主链路 |
| D5 | `concept_snapshot`（REALTIME 但有完整采集注入）如何处理 | 改判 INCREMENTAL / 移除 log+runner 注入 | 需产品语义确认，**本次不动** |

---

## 八、验证清单

### 8.1 前置：确认两个库的表分布

```sql
-- attribution 库：应只有 collect_logs（+ sys_* / stock_pool*）
\connect attribution
\dt collect_logs
\dt tech_kline_daily      -- 期望：does not exist

-- raw_data 库：应有 28 张 tech_/capital_/fundamental_/news_ 表
\connect raw_data
\dt collect_logs          -- 期望：does not exist
\dt tech_kline_daily      -- 期望：存在
```

### 8.2 改造后逐 service 冒烟（28 个）

对每个 `POST /api/collect/{facet}/{name}`：

| 检查项 | 期望 |
|---|---|
| HTTP 状态码 | 200（非 500）——验证 BUG-2 已修 |
| 响应 `log_id` | 非空 UUID |
| `GET /api/collect/logs/{name}` 首查 | `status=running` |
| 日志 `error_message` | 空 |
| raw_data 库目标表 | 新增行数 > 0 |
| attribution 库 `collect_logs.status` | 终态 `success` / `partial_fail`，**非 running** |
| 后端日志 | 无 `UndefinedTableError` / `InFailedSQLTransactionError` |

### 8.3 专项回归

| 场景 | 命令/操作 | 期望 |
|---|---|---|
| **原始 bug 复现验证** | `POST /api/collect/tech/daily_kline` | 有进展，终态 success |
| **并发安全** | 临时把日 K `concurrency` 设回 5，跑全量 | 不再出现事务 abort 交织（方案 A 下应改回 1） |
| **全量模式** | `POST /api/collect/fundamental/concept_members` 不传 `index_codes` | 能拉到 concept 列表（验证 BUG-7 修复） |
| **异常路径** | 手工断网/改坏 token 触发 fetch 失败 | `status=failed` + `error_message` 非空，**不卡 running** |
| **进程重启** | 采集中途 `Ctrl+C` 再启动 | `recover_orphan_logs` 把 orphan 标记 failed |
| **日志查询** | `GET /api/collect/logs/daily_kline?limit=50` | 正常返回，含 Redis 合并进度 |

### 8.4 建议加的自动化断言（防止回归）

1. **静态检查**：加一条测试断言"28 个工厂的 `session` 依赖全部是 `get_raw_db`"
2. **契约检查**：遍历 `CatalogService` 的 28 个 class，断言 `META.kind != REALTIME` 的都有 `_run_collect`
3. **表归属检查**：遍历 `RawBase.metadata` 与 `AttribBase.metadata` 的表名，断言无交集

---

## 九、风险与影响面

| 风险 | 等级 | 说明 | 缓解 |
|---|---|---|---|
| **改造面广** | 高 | 触及 28 个工厂 + 日志子系统 + Runner | 已提供统一模板（§5.3），机械替换 |
| **性能回退** | 中 | 并发降为 1（方案 A） | tushare 限流 200/60s 本就限制并发；建议实测对比 |
| **NullPool 连接开销** | 中 | 方案 B 下每 symbol 一次握手 | 推荐方案 A 规避 |
| **日志写入频率** | 低 | 每次 `mark_*` 开一个短事务 | 频率极低（pending/running/终态各一次 + Redis 进度） |
| **stock_basic 清理时机** | 低 | 内部兜底与新注入并存 | 延后清理，先跑通主链路 |
| **`collect_logs` 动态建表** | 低 | 由 `ensure_attrib_tables()` 在 attribution 库建 | 已有，不受影响 |

---

## 十、附录：现状快照（供评审对照）

### 10.1 28 个 factory 的 session 注入现状

| # | 工厂 | `session` 来源 | `_make_log_service` 实参 | 数据写入 | 日志写入 |
|---|---|---|---|---|---|
| 1 | `get_daily_kline_service:44` | `get_db` ❌ | `session` | ❌ attribution | ✅ attribution |
| 2 | `get_minute_kline_service:59` | 无 | — | — | — |
| 3 | `get_adj_factor_service:66` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 4 | `get_suspend_service:88` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 5 | `get_name_change_service:110` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 6 | `get_moneyflow_service:130` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 7 | `get_moneyflow_hsgt_service:152` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 8 | `get_top_list_service:174` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 9 | `get_top_inst_service:196` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 10 | `get_block_trade_service:218` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 11 | `get_margin_service:240` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 12 | `get_hsgt_top10_service:262` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 13 | `get_limit_list_service:284` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 14 | `get_holder_number_service:306` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 15 | `get_daily_basic_service:325` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 16 | `get_fin_income_service:347` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 17 | `get_top10_holders_service:369` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 18 | `get_top10_float_holders_service:391` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 19 | `get_dividend_service:413` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 20 | `get_stock_basic_service:430` | `get_raw_db` ✅ | `log_session` ✅ | ✅ raw（内部兜底） | ✅ attribution |
| 21 | `get_stock_concepts_service:455` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 22 | `get_concept_list_service:487` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 23 | `get_concept_members_service:511` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 24 | `get_concept_index_daily_service:539` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 25 | `get_concept_minute_service:566` | 无 | — | — | — |
| 26 | `get_concept_snapshot_service:588` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 27 | `get_news_service:615` | `get_raw_db` ✅ | `session` ❌ | ✅ raw | ❌ raw |
| 28 | `get_sentiment_service:637` | 无 | — | — | — |

> 注：行号为 `collect_service.py` 当前值；且**后台路径下 BUG-1 会把 2/20 的"正确"也覆盖成错误**
> （Runner 统一传 `get_db_context()`），只有 `stock_basic` 因内部兜底幸存。

### 10.2 错误传播时序（现状）

```
create_pending()          ── 对 stock_basic 而言正确；对其余 24 个 → ❌ UndefinedTable（HTTP 500）
   ↓
dispatch() → TaskRunner._run()
   ↓
get_db_context()          ← attribution_db（BUG-1）
   ↓
mark_running()            ✅ commit 成功 → status=running 落库
   ↓
_run_collect() → _save()  ← 用 attribution session 写 RawBase 表
   ↓
                         ❌ UndefinedTableError  ← 真实的第一个错（已滚出屏幕）
   ↓
重试 ×2（无 rollback）     ❌ InFailedSQLTransactionError ×2  ← 掩盖根因（BUG-5）
   ↓
mark_failed()             ❌ 同一 abort session → InFailedSQLTransactionError（BUG-6）
   ↓
session.close()           ❌ IllegalStateChangeError
   ↓
                    ★ status 永久 running ★ → 前端"没反应"
```

---

## 十一、结论

1. **本次事故的根因是 BUG-1 + BUG-2 的组合**，不是单点问题：
   DI 工厂给日志服务喂了 raw 库 session（24 处），同时 TaskRunner 又绕过 DI 给 service 喂了业务库 session。
   两者方向相反，导致 28 个 service 里**只有 `stock_basic` 一个是对的**。

2. **用户提出的方案（service 注入 raw session + log_service，TaskRunner 只注入 log_service，
   log_service 自管业务库 session）经代码验证完全成立**，且能一次性消除全部 8 个 bug。
   关键支撑证据：`CollectLogRepository` 每个写方法都独立 commit，日志与数据本就不共享事务。

3. **改造是机械且可控的**：`collect_service.py` 的 28 个工厂可用统一模板批量替换，
   route / fetcher / ORM 全部无需改动。

4. **建议实施顺序**：① CollectLogService → ② TaskRunner → ③ DI 工厂 → ④ daily_kline 细节 → ⑤ base.py → ⑥ 并发收敛。

---

*文档结束。请评审 §七 待决策项，确认后进入实施。*