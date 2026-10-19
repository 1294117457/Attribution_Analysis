# 04-Session 依赖注入优化方案

> 位置：`docs/backend-docs/dev/level2/step1采集模块优化/03整体同步/04-Session依赖注入优化方案.md`
> 上游文档：`01-interface-service-repo同步方案.md`（Phase 1-4 已落地）
> 配套文档：
> - `../config/depend管理.md`（DB Session 依赖注入规范）
> - `shared/infrastructure/di/db_session.py`（session 注入入口）
> 更新日期：2026-10-19
> 状态：**待评审（暂不修改代码）**

---

## 〇、决策与方向（评审前先看）

### 0.1 本次优化目标

在 Phase 1-4 "三层同步" 基础上，进一步规范化 **DB session 的注入路径**：

> **session 在 service 工厂的形参里收（`Depends(get_db)` 或 `Depends(get_raw_db)`），route 不收、也不透传，repo 不再自己 `async with db_session_factory()`。**

### 0.2 当前现状问题

| 现状 | 问题 |
|---|---|
| **27 个 repo 各自在 `save()` 内部 `async with db_session_factory()` + `await session.commit()`** | 每个 repo 方法独立开 session、独立 commit，**无事务边界**；一次 `svc.collect()` 跑 N 个 symbol 时，N 次 save 各开各事务，前面已 commit 的无法回滚 |
| **`collect_service.py` 的 25 个 service 工厂只注入了 repo，没有 session`** | service 持有 repo，但 repo 自己管 session；service 无法控制事务范围 |
| **route 完全不感知 session**（✅ 正确） | 保持现状 |

### 0.3 根因

Phase 1-4 落地了"service → repo 依赖注入"，但 **repo 内部跳过了 Depends 入口**：

```
Phase 1-4 做到的事：
  route → Depends(get_xxx_service) → service.__init__(repo=repo)
                                              ↓
                                      self._repo.save(bos)    ← repo 内部自己开 session

本次要补的事：
  route → Depends(get_xxx_service) + Depends(get_raw_db)
                                        ↓
                              service.__init__(repo=repo, session=session)
                                        ↓
                              self._repo.save(bos, session)  ← repo 用入参 session
```

### 0.4 三项决策（user 拍板）

| # | 决策 | 选择 |
|---|---|---|
| **S1** | session 注入层 | **A：service 工厂形参收 `Depends(get_db/raw_db)`**（route 不感知） |
| **S2** | repo `save()` 签名 | **A：接受 `session: AsyncSession` 入参**（不再自己开 session） |
| **S3** | commit/rollback 收尾 | **A：由 `get_db/get_raw_db` 的 Depends 统一收尾**（`try/except/yield` 后自动 commit） |

---

## 一、现有设计：db_session.py 已为这条路铺好

### 1.1 db_session.py 提供的 4 个工具

```python
# shared/infrastructure/di/db_session.py

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends 注入用（业务库 attribution_db）"""
    async with db_session_factory() as session:
        try:
            yield session           # ← FastAPI 把 session 注入给调用方
            await session.commit() # ← 正常结束 → commit
        except Exception:
            await session.rollback()  # ← 异常 → rollback
            raise
        finally:
            await session.close()

async def get_raw_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends 注入用（采集库 raw_data_db）"""
    async with raw_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Service 层独立事务用（业务库）—— scheduler / 后台任务用"""
    ...

@asynccontextmanager
async def get_raw_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Service 层独立事务用（采集库）"""
    ...
```

### 1.2 两个场景分清楚

| 场景 | 工具 | 说明 |
|---|---|---|
| **route 触发 → service → repo**（HTTP 请求） | `Depends(get_raw_db)` | FastAPI Depends 注入，commit/rollback 由 Depends 自动收尾 |
| **scheduler / APScheduler / 后台任务** | `async with get_raw_db_context()` | contextmanager 手动控制生命周期 |

> **collect 模块的 25 个写库 service 走 route 触发路线**，用 `Depends(get_raw_db)`。

### 1.3 项目内已有先例（形态 A）

以下 service 工厂**已经在用这个模式**（和本次要改的 25 个 collect service 结构完全一致）：

| 文件 | 写法 |
|---|---|
| `contexts/user/infrastructure/di/stock_pool.py:51` | `session: AsyncSession = Depends(get_db)` |
| `contexts/market/infrastructure/di/stock_info.py:18-19` | `attr_session: AsyncSession = Depends(get_db)` + `raw_session: AsyncSession = Depends(get_raw_db)` |
| `contexts/concept/infrastructure/di/concept_service.py:17-18` | 同上（两个 session） |
| `contexts/auth/infrastructure/di/auth_service.py:53` | `session: AsyncSession = Depends(get_db)` |

**这 4 个模块的 service 工厂是"形态 A"（session 在 service 工厂收），而 collect 25 个 service 工厂是"形态 B"（缺 session）**。本次改造让 collect 模块向形态 A 看齐。

---

## 二、目标架构（改造后状态）

### 2.1 完整链路（HTTP 请求）

```
FastAPI 请求进入
    ↓
route: Depends(get_xxx_service)      ← route 只感知 service，不感知 session
    ↓
service 工厂：
  repo = Depends(get_xxx_repository)  ← repo 注入（Phase 1-4 已有）
  session = Depends(get_raw_db)        ← session 注入（本次新增）
    ↓
service.__init__(repo, session)       ← service 持有 session
    ↓
service.collect(params)
    ↓
self._repo.save(bos, session=session)  ← repo 用入参 session（不自己开）
    ↓
session.execute(stmt)                  ← repo 内部只做 DB 操作，不 commit
    ↓
（Depends(get_raw_db) 收尾：
    try → yield 后自动 commit
    except → 自动 rollback
    finally → 自动 close）
```

### 2.2 与现有设计的对照

| 层级 | 改造前 | 改造后 |
|---|---|---|
| **route** | `Depends(get_xxx_service)` | **不变**（不感知 session） |
| **service 工厂** | `repo=Depends(get_repo)` | **新增** `session=Depends(get_raw_db)` |
| **service `__init__`** | `self._repo = repo` | **新增** `self._session = session` |
| **service `collect()`** | `await self._repo.save(bos)` | `await self._repo.save(bos, self._session)` |
| **repo `save()`** | `async with db_session_factory() as session:` + `await session.commit()` | `session: AsyncSession` 入参 + 不再 commit |
| **commit/rollback** | 各 repo 各自 commit | **统一由 `Depends(get_raw_db)` 收尾** |

---

## 三、详细改造方案

### 3.1 Layer 1：collect_service.py（25 个 service 工厂）

#### 3.1.1 改造前（adj_factor 示例）

```python
def get_adj_factor_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_adj_factor_repository"],
        ).get_adj_factor_repository
    ),
):
    from contexts.collect.application.service.tech.adj_factor_service import AdjFactorService
    return AdjFactorService(repo=repo)     # ← 缺 session
```

#### 3.1.2 改造后

```python
def get_adj_factor_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_adj_factor_repository"],
        ).get_adj_factor_repository
    ),
    session: AsyncSession = Depends(get_raw_db),   # ← 新增（采集库用 get_raw_db）
):
    from contexts.collect.application.service.tech.adj_factor_service import AdjFactorService
    return AdjFactorService(repo=repo, session=session)
```

#### 3.1.3 25 个 factory 改动清单

**tech（5 个）**：

| service 工厂 | 注入 session | 说明 |
|---|---|---|
| `get_daily_kline_service` | `get_db`（业务库 kline） | `daily_kline` 写业务库，用 `get_db` |
| `get_minute_kline_service` | — | 实时查询，无 repo，保持现状 |
| `get_adj_factor_service` | `get_raw_db` | 采集库 |
| `get_suspend_service` | `get_raw_db` | 采集库 |
| `get_name_change_service` | `get_raw_db` | 采集库 |

**capital（9 个）**：

| service 工厂 | 注入 session |
|---|---|
| `get_moneyflow_service` | `get_raw_db` |
| `get_moneyflow_hsgt_service` | `get_raw_db` |
| `get_top_list_service` | `get_raw_db` |
| `get_top_inst_service` | `get_raw_db` |
| `get_block_trade_service` | `get_raw_db` |
| `get_margin_detail_service` | `get_raw_db` |
| `get_hsgt_top10_service` | `get_raw_db` |
| `get_limit_list_service` | `get_raw_db` |
| `get_holder_number_service` | `get_raw_db` |

**fundamental（12 个）**：

| service 工厂 | 注入 session |
|---|---|
| `get_fin_daily_basic_service` | `get_raw_db` |
| `get_fin_income_service` | `get_raw_db` |
| `get_top10_holders_service` | `get_raw_db` |
| `get_top10_float_holders_service` | `get_raw_db` |
| `get_dividend_service` | `get_raw_db` |
| `get_stock_basic_service` | `get_db`（业务库 stock_info） |
| `get_stock_concepts_service` | `get_raw_db` |
| `get_concept_list_service` | `get_db`（concept 库） |
| `get_concept_members_service` | `get_raw_db` |
| `get_concept_index_daily_service` | `get_raw_db` |
| `get_concept_minute_service` | — | 实时查询，保持现状 |
| `get_concept_snapshot_service` | `get_raw_db` |

**news（1 个）**：

| service 工厂 | 注入 session |
|---|---|
| `get_news_service` | `get_raw_db` |

**sentiment（1 个）**：

| service 工厂 | 说明 |
|---|---|
| `get_sentiment_service` | 空壳，保持现状 |

> `get_daily_kline_service`（业务库 kline）和 `get_stock_basic_service`（业务库 stock_info）用 `get_db`（`attribution_db`），其余 22 个 service 用 `get_raw_db`（`raw_data_db`）。
> `get_concept_list_service` 写的是 `concept_db`（index_code 表），目前需要确认该库是否走 `get_db` 路径。

#### 3.1.4 改完后 collect_service.py 顶部 import 变更

```python
# 顶部新增一个 import
from sqlalchemy.ext.asyncio import AsyncSession
from shared.infrastructure.di.db_session import get_db, get_raw_db
```

---

### 3.2 Layer 2：service 类（25 个写库 service）

#### 3.2.1 改造前（AdjFactorService）

```python
class AdjFactorService:
    name = "adj_factor"
    RATE_LIMIT = ("tushare", 200, 60)

    def __init__(
        self,
        fetcher: AdjFactorTushareFetcher | None = None,
        repo: "AdjFactorRepository" | None = None,
    ) -> None:
        self._fetcher = fetcher or AdjFactorTushareFetcher()
        self._repo = repo

    async def collect(self, params: dict) -> CollectResult:
        ...
        saved = await self._repo.save(bos)    # ← 无 session 透传
```

#### 3.2.2 改造后

```python
from sqlalchemy.ext.asyncio import AsyncSession  # 新增

class AdjFactorService:
    name = "adj_factor"
    RATE_LIMIT = ("tushare", 200, 60)

    def __init__(
        self,
        fetcher: AdjFactorTushareFetcher | None = None,
        repo: "AdjFactorRepository" | None = None,
        session: AsyncSession | None = None,    # ← 新增
    ) -> None:
        self._fetcher = fetcher or AdjFactorTushareFetcher()
        self._repo = repo
        self._session = session                 # ← 新增

    async def collect(self, params: dict) -> CollectResult:
        ...
        saved = await self._repo.save(bos, self._session)  # ← 透传 session
```

> **`session` 参数命名为 `_session`**（与 `_repo` / `_fetcher` 对齐）。`None` 时可降级兼容（如 scheduler 场景走 `get_db_context()`），但 **25 个 route 触发路径永远有值**（Depends 保证）。

#### 3.2.3 25 个 service 改动清单（只列 `__init__` 签名变更）

| service | `__init__` 变更 | session 来源 |
|---|---|---|
| `AdjFactorService` | + `session: AsyncSession` | `get_raw_db` |
| `SuspendService` | + `session: AsyncSession` | `get_raw_db` |
| `NameChangeService` | + `session: AsyncSession` | `get_raw_db` |
| `DailyKlineService` | + `session: AsyncSession` | `get_db` |
| `MoneyflowService` | + `session: AsyncSession` | `get_raw_db` |
| `MoneyflowHsgtService` | + `session: AsyncSession` | `get_raw_db` |
| `TopListService` | + `session: AsyncSession` | `get_raw_db` |
| `TopInstService` | + `session: AsyncSession` | `get_raw_db` |
| `BlockTradeService` | + `session: AsyncSession` | `get_raw_db` |
| `MarginDetailService` | + `session: AsyncSession` | `get_raw_db` |
| `HsgtTop10Service` | + `session: AsyncSession` | `get_raw_db` |
| `LimitListService` | + `session: AsyncSession` | `get_raw_db` |
| `HolderNumberService` | + `session: AsyncSession` | `get_raw_db` |
| `FinDailyBasicService` | + `session: AsyncSession` | `get_raw_db` |
| `FinIncomeService` | + `session: AsyncSession` | `get_raw_db` |
| `Top10HoldersService` | + `session: AsyncSession` | `get_raw_db` |
| `Top10FloatHoldersService` | + `session: AsyncSession` | `get_raw_db` |
| `DividendService` | + `session: AsyncSession` | `get_raw_db` |
| `StockBasicService` | + `session: AsyncSession` | `get_db` |
| `StockConceptsService` | + `session: AsyncSession` | `get_raw_db` |
| `ConceptListService` | + `session: AsyncSession` | 待确认 |
| `ConceptMembersService` | + `session: AsyncSession` | `get_raw_db` |
| `ConceptIndexDailyService` | + `session: AsyncSession` | `get_raw_db` |
| `ConceptSnapshotService` | + `session: AsyncSession` | `get_raw_db` |
| `NewsService` | + `session: AsyncSession` | `get_raw_db` |

> 3 个不改动：`MinuteKlineService`（实时查询）、`ConceptMinuteService`（实时查询）、`SentimentService`（空壳）。

---

### 3.3 Layer 3：repo 类（25 个写库 repo）

#### 3.3.1 改造前（adj_factor_repo.py）

```python
# ❌ 当前写法
from shared.infrastructure.connection.db_factory import db_session_factory  # ← 不应直接用

class AdjFactorRepository:
    async def save(self, bos: list[BaseAdjFactorBO]) -> int:
        rows = [self._to_row(b) for b in bos]
        async with db_session_factory() as session:      # ← repo 自己开 session（问题）
            stmt = pg_insert(BaseAdjFactorDB).values(rows)
            stmt = stmt.on_conflict_do_update(...)
            r = await session.execute(stmt)
            await session.commit()                       # ← repo 自己 commit（问题）
            return r.rowcount or len(rows)
```

#### 3.3.2 改造后

```python
# ✅ 改造后写法
from sqlalchemy.ext.asyncio import AsyncSession  # 新增
# from shared.infrastructure.connection.db_factory import db_session_factory  # ← 删除

class AdjFactorRepository:
    async def save(self, bos: list[BaseAdjFactorBO], session: AsyncSession) -> int:
        """入参 session 来自 service 透传，由 Depends(get_raw_db) 统一收尾"""
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        # ← 不再 async with db_session_factory()
        stmt = pg_insert(BaseAdjFactorDB).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in BaseAdjFactorDB.__table__.columns
            if c.name not in ("id", "created_at", "updated_at", "symbol", "trade_date")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "trade_date"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        # ← 不再 await session.commit() —— 由 Depends(get_raw_db) 统一收尾
        return r.rowcount or len(rows)
```

#### 3.3.3 25 个 repo 改动清单

| repo | 签名变更 | 内部变更 |
|---|---|---|
| `AdjFactorRepository` | `save(self, bos, session: AsyncSession)` | 删 `async with db_session_factory()`，删 `await session.commit()` |
| `SuspendRepository` | 同上 | 同上 |
| `NameChangeRepository` | 同上 | 同上 |
| `KlineRepository` | 同上（`get_db`） | 同上 |
| `MoneyflowRepository` | 同上 | 同上 |
| `MoneyflowHsgtRepository` | 同上 | 同上 |
| `TopListRepository` | 同上 | 同上 |
| `TopInstRepository` | 同上 | 同上 |
| `BlockTradeRepository` | 同上 | 同上 |
| `MarginDetailRepository` | 同上 | 同上 |
| `HsgtTop10Repository` | 同上 | 同上 |
| `LimitListRepository` | 同上 | 同上 |
| `HolderNumberRepository` | 同上 | 同上 |
| `FinDailyBasicRepository` | 同上 | 同上 |
| `FinReportRepository` | 同上 | 同上 |
| `FinTop10HoldersRepository` | 同上 | 同上 |
| `FinTop10FloatHoldersRepository` | 同上 | 同上 |
| `DividendRepository` | 同上 | 同上 |
| `StockInfoRepository` | 同上（`get_db`） | 同上 |
| `StockConceptRepository` | 同上 | 同上 |
| `ConceptRepository` | 同上 | 同上 |
| `ConceptMemberRepository` | 同上 | 同上 |
| `ConceptIndexRepository` | 同上 | 同上 |
| `ConceptSnapshotRepository` | 同上 | 同上 |
| `NewsArticleRepository` | 同上 | 同上 |

> `KlineRepository`（`daily_kline`）和 `StockInfoRepository`（`stock_basic`）接 `get_db` session，其余 23 个接 `get_raw_db` session。

---

## 四、跨 repo 事务场景（一个事务里写多个 repo）

### 4.1 当前问题

改造后，单个 repo 方法内的 session 生命周期由 Depends 统一收尾，**但一个 `collect()` 里调用多个 repo 怎么保证同一个 session**？

**举例**：`concept_snapshot` service 可能同时调用 `ConceptSnapshotRepository` + `ConceptRepository`。

### 4.2 方案选择

| 方案 | 做法 | 适用场景 |
|---|---|---|
| **A：各 repo 独立 session**（现状） | 每个 repo 自己 `async with`，各开各事务 | 无需跨 repo 事务的场景 |
| **B：service 持有 session 透传给所有 repo** | `self._session` 透传给所有调用的 repo | 需要跨 repo 事务的场景 |

**本方案推荐方案 B**——`collect()` 里如果调用多个 repo，都传 `self._session`：

```python
async def collect(self, params: dict) -> CollectResult:
    bos1 = await self._fetcher1.fetch(...)
    saved1 = await self._repo1.save(bos1, self._session)    # ← 同一 session
    bos2 = await self._fetcher2.fetch(...)
    saved2 = await self._repo2.save(bos2, self._session)    # ← 同一 session
    # 两个 repo 在同一事务里，Depends(get_raw_db) 统一 commit/rollback
```

**需要跨 repo 事务的 service**：目前 `concept_snapshot` 可能是首个场景，后续确认。

---

## 五、与 Scheduler / 后台任务的兼容性

### 5.1 场景：APScheduler 调用 service

APScheduler 触发不走 FastAPI 请求链路，`Depends(get_raw_db)` 没有依赖图注入。需要另一种方式：

**方案 A：service 支持 `session=None` 降级**

```python
async def collect(self, params: dict) -> CollectResult:
    if self._session is None:
        async with get_raw_db_context() as session:    # ← 自己开 context
            return await self._collect_with_session(params, session)
    else:
        return await self._collect_with_session(params, self._session)

async def _collect_with_session(self, params: dict, session: AsyncSession) -> CollectResult:
    bos = await self._fetcher.fetch(...)
    saved = await self._repo.save(bos, session)
    return CollectResult(...)
```

**方案 B：scheduler 层用 `get_raw_db_context()` 调 service**

```python
async def scheduled_job():
    async with get_raw_db_context() as session:
        svc = AdjFactorService(repo=repo, session=session)
        await svc.collect(params)
```

**推荐方案 B**——scheduler 层显式控制 session 生命周期，service 不需要 `session=None` 降级逻辑，更干净。

### 5.2 两种路径对照

| 触发方式 | session 来源 | commit/rollback 收尾 |
|---|---|---|
| **route → Depends** | `Depends(get_raw_db)` | Depends 的 try/finally 自动收尾 |
| **APScheduler / scheduler** | `async with get_raw_db_context()` | contextmanager 的 try/finally 自动收尾 |

---

## 六、改动文件清单

### 6.1 修改文件（52 个）

| 层 | 文件 | 改动量 |
|---|---|---|
| **DI** | `infrastructure/di/collect_service.py` | 25 个 factory 各加 `session: AsyncSession = Depends(get_xxx_db)` |
| **Service** | `application/service/tech/adj_factor_service.py` | + `session` 入参 + `await self._repo.save(bos, self._session)` |
| **Service** | `application/service/tech/suspend_service.py` | 同上 |
| **Service** | `application/service/tech/name_change_service.py` | 同上 |
| **Service** | `application/service/tech/daily_kline_service.py` | 同上（`get_db`） |
| **Service** | `application/service/capital/moneyflow_service.py` | 同上 |
| **Service** | `application/service/capital/moneyflow_hsgt_service.py` | 同上 |
| **Service** | `application/service/capital/top_list_service.py` | 同上 |
| **Service** | `application/service/capital/top_inst_service.py` | 同上 |
| **Service** | `application/service/capital/block_trade_service.py` | 同上 |
| **Service** | `application/service/capital/margin_detail_service.py` | 同上 |
| **Service** | `application/service/capital/hsgt_top10_service.py` | 同上 |
| **Service** | `application/service/capital/limit_list_service.py` | 同上 |
| **Service** | `application/service/capital/holder_number_service.py` | 同上 |
| **Service** | `application/service/fundamental/fin_daily_basic_service.py` | 同上 |
| **Service** | `application/service/fundamental/fin_income_service.py` | 同上 |
| **Service** | `application/service/fundamental/top10_holders_service.py` | 同上 |
| **Service** | `application/service/fundamental/top10_float_holders_service.py` | 同上 |
| **Service** | `application/service/fundamental/dividend_service.py` | 同上 |
| **Service** | `application/service/fundamental/stock_basic_service.py` | 同上（`get_db`） |
| **Service** | `application/service/fundamental/stock_concepts_service.py` | 同上 |
| **Service** | `application/service/fundamental/concept_list_service.py` | 同上（待确认 get_db/get_raw_db） |
| **Service** | `application/service/fundamental/concept_members_service.py` | 同上 |
| **Service** | `application/service/fundamental/concept_index_daily_service.py` | 同上 |
| **Service** | `application/service/fundamental/concept_snapshot_service.py` | 同上 |
| **Service** | `application/service/news/news_service.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/adj_factor_repo.py` | `save(self, bos, session)` + 删 `async with` + 删 `commit` |
| **Repo** | `infrastructure/persistence/repositories/suspend_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/name_change_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/kline_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/moneyflow_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/moneyflow_hsgt_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/top_list_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/top_inst_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/block_trade_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/margin_detail_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/hsgt_top10_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/limit_list_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/holder_number_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/fin_daily_basic_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/fin_report_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/fin_top10_holders_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/fin_top10_float_holders_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/dividend_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/stock_info_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/stock_concept_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/concept_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/concept_member_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/concept_index_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/concept_snapshot_repo.py` | 同上 |
| **Repo** | `infrastructure/persistence/repositories/news_article_repo.py` | 同上 |

### 6.2 不改动文件

- 所有 route 文件（route 不感知 session，保持 `Depends(get_xxx_service)` 不变）
- 3 个实时查询 service（`MinuteKlineService`、`ConceptMinuteService`）
- 1 个空壳 service（`SentimentService`）
- `shared/infrastructure/di/db_session.py`（已经是标准入口）
- `shared/infrastructure/connection/db_factory.py`（底层 sessionmaker）

---

## 七、验收清单

### 7.1 静态验证

```bash
# 1. collect_service.py 所有 factory 有 session 形参
grep "session: AsyncSession = Depends" backend/src/contexts/collect/infrastructure/di/collect_service.py
# 期望：25 个（22 个 get_raw_db + 3 个 get_db）

# 2. 所有 repo 的 save() 签名接受 session
grep "async def save" backend/src/contexts/collect/infrastructure/persistence/repositories/*.py
# 期望：25 个 repo 的 save() 都有 session: AsyncSession

# 3. 所有 repo 不再有 async with db_session_factory
grep "async with db_session_factory" backend/src/contexts/collect/infrastructure/persistence/repositories/*.py
# 期望：无任何结果

# 4. 所有 repo 不再有 await session.commit
grep "await session.commit" backend/src/contexts/collect/infrastructure/persistence/repositories/*.py
# 期望：无任何结果

# 5. service 内调用 repo.save 时透传 session
grep "self._repo.save\|self._repo\.save" backend/src/contexts/collect/application/service/**/*.py
# 期望：25 个写库 service 的 save 调用都有第二个参数 self._session
```

### 7.2 事务一致性验证（新增）

**场景**：单 symbol 多字段采集（如 moneyflow 一次采多个字段）
**验证**：在 `get_raw_db` 注入的 session 断点，看 `svc._session` 和 `repo.save` 的 `session` 是否同一个对象。

### 7.3 回归验证

```bash
# 28 个 endpoint 全部点一遍（route 触发）
# 验证：采集入库正常，无 "session already closed" / "transaction closed" 错误
```

---

## 八、改造前后对比

| 维度 | 改造前 | 改造后 |
|---|---|---|
| **session 来源** | 各 repo 内部 `async with db_session_factory()` | service 工厂 `Depends(get_db/get_raw_db)` |
| **session 注入点** | repo 自己管 | service 工厂（route 无感知） |
| **commit/rollback** | 各 repo 各自 commit | `Depends` 统一收尾 |
| **跨 repo 事务** | 不可能 | ✅ service 透传同一 session 给所有 repo |
| **事务回滚能力** | ❌ 无（各 repo 独立 commit） | ✅ 一个 session 一个事务 |
| **异常时 rollback** | ❌ 无 | ✅ `Depends` 的 `except` 自动 rollback |
| **collect_service.py 改动** | 只注入 repo | + `session: AsyncSession = Depends(get_raw_db)` |
| **service 改动** | `__init__(repo)` | `__init__(repo, session)` + `_collect 时透传` |
| **repo 改动** | `save(bos)` 自己开 session | `save(bos, session)` 接受入参 |
| **route 改动** | 无 | **无**（完全不透传） |

---

## 九、与项目既有规范的对应

| 规范来源 | 对应本方案 |
|---|---|
| `docs/backend-docs/config/depend管理.md` 第 4 行 | "dbsession在service层注入"——本方案落地 |
| `docs/backend-docs/config/depend管理.md` 最后一行 | "await self._repo.save(bos, session=session)"——本方案落地 |
| `shared/infrastructure/di/db_session.py` docstring | "get_db / get_raw_db: FastAPI Depends 用"——本方案使用 |
| `shared/infrastructure/di/db_session.py` docstring | "Service 层独立事务用（async with）"——scheduler 用 `get_raw_db_context()` |

---

## 十、风险与回退

### 10.1 风险

| 风险 | 概率 | 缓解 |
|---|---|---|
| session 注入顺序错（先 repo 再 session）导致 Depends 调度异常 | 低 | 每个 factory 形参顺序不影响结果，FastAPI 依赖图自动按声明顺序解析 |
| repo 漏改（仍有 `async with db_session_factory()`）导致双重 session | 低 | grep 验证脚本检查 |
| 漏掉某个 service 的 `save()` 调用透传 session | 低 | grep 验证脚本检查 |
| `daily_kline` / `stock_basic` 用错 `get_db` vs `get_raw_db` | 低 | 已标注，改造时注意 |
| concept 库（concept_list 写 index_code 表）用哪个 session | 中 | 待确认后改造 |

### 10.2 回退策略

每个 layer 独立 commit：
1. `collect_service.py` 改完 → 跑全量导入验证
2. 25 个 service 改完 → 跑全量导入验证
3. 25 个 repo 改完 → 跑全量导入验证 + 28 endpoint 回归

任一步失败可单独回退。

---

## 十一、下一步（可选优化）

| 优化项 | 说明 | 优先级 |
|---|---|---|
| **跨 repo 事务确认** | `concept_snapshot` 等可能同时写多个 repo 的 service，确认是否需要 `self._session` 透传给所有 repo | 高 |
| **scheduler 兼容确认** | 确认现有 scheduler 触发方式，按方案 B 改用 `get_raw_db_context()` | 中 |
| **concept_list session 确认** | 确认 `concept` 表（index_code）走 `attribution_db` 还是 `raw_data_db` | 中 |
| **Phase 5 装饰器化** | 25 个 service 的限流/重试样板抽成装饰器（不在本批范围） | 低 |

---

**总结**：

- **最小改动范围**：只改 1 个 DI 文件 + 25 个 service + 25 个 repo，route 不动。
- **session 流向**：`Depends(get_raw_db)` → service 工厂形参 → service 实例 → repo `save()` 入参 → `session.execute()`。
- **commit/rollback**：统一由 `Depends(get_raw_db)` 的 try/except/finally 自动收尾，repo 不再自己 commit。
- **事务能力**：单次 `collect()` 内多个 repo 调用可共享同一 session，实现跨 repo 事务。
