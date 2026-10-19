# Interface / Service / Repo 三层同步方案

> 位置：`docs/backend-docs/dev/level2/step1采集模块优化/03整体同步/01-interface-service-repo同步方案.md`
> 配套文档：
> - `02fetcher同步/01-fetcher与接口文档对账与同步方案.md`（已落地）
> - `02fetcher同步/02-fetcher同步情况总结.md`（已落地，21 项 P0/P1 全部修复）
> - `01接口文档-数据库/01-字段对账与修复方案.md`（30 张表已对齐）
> - `../config/DDD.md`（DDD 架构规范）
> 更新日期：2026-10-18
> 状态：**待评审（暂不修改代码）**

---

## 〇、决策与方向（评审前先看）

### 0.1 三层职责定位（user 提出）

> 28 个 route ↔ 28 个 service，**一比一**；route 收前端参数 → 调 service → service 调 fetcher（实时查询）或 repo（采集入库）。
> 限流、重试延后做（Phase 5 之后），不在本批范围。

| 项 | 本批 | 延后 |
|---|---|---|
| route 收参数 + 调 service | ✅ | |
| service 调 fetcher（实时查询） | ✅ | |
| service 调 repo 写库 | ✅ | |
| service 调 fetcher 拿数据后入 repo | ✅ | |
| 限流（Redis check） | | ⏸ Phase 5 |
| 限流/重试装饰器抽离 | | ⏸ Phase 5 |
| scheduler / APScheduler | | ⏸ Phase 6 |
| RunLog 持久化 | | ⏸ Phase 6 |

### 0.2 关键名词澄清

- **trigger endpoint**：POST 触发的"执行一次采集"接口（`POST /api/collect/{facet}/{service_name}`）。本批仅做 DTO 化，**不引入新概念、不抽抽象**。DTO 命名取业务语义 `CollectRequest`/`CollectResponse`（与 `application/service/base.py::CollectResult` 保持一致）。
- **query endpoint**：GET 触发的"实时查询"接口（`GET /api/collect/query/{name}`），不在本批改动（保持现状）。
- **写库 service vs 实时查询 service**：
  - **写库 service**（如 `daily_kline` / `moneyflow` / `top_list`）—— `collect()` 调 fetcher 拉数据 + repo 写库；**无 `get()`**（前端要查就调 query endpoint，service 内部不读 DB）。
  - **实时查询 service**（如 `minute_kline` / `concept_minute`）—— `get()` 直接调 fetcher（**无 repo**）；`collect()` 返回"请用 get()"提示。
  - 两者 `collect()` 入口都在本批走 DTO 化。

### 0.3 五项决策（user 拍板）

| # | 决策 | 选择 |
|---|---|---|
| **D1** | 聚合根粒度 | **A：28 个聚合根**（每张表 = 1 个聚合根，严格 DDD） |
| **D2** | Protocol 范围 | **B：28 个全抽 Protocol**（DDD 严格） |
| **D3** | 未入库 service 补做策略 | **A：本次全部补做**；严格区分"采集入库"和"实时查询" |
| **D4** | BO → row 转换位置 | **A：放 repo 内部**（每个 repo 一个 `_to_row(bo)`） |
| **D5** | 旧 DTO 处置 | **B：删除 `dto/response/collect.py` 中无用的 `TaskDefResponse` 等**（确认无引用后删） |

---

## 一、目标与范围

### 1.1 目标

把 fetcher 同步（已完成）的成果**贯穿到三层**：
- **interface**：请求 DTO 化、参数校验前置、响应统一（命名对齐 `CollectRequest`/`CollectResponse`）
- **service**：service 不再 inline ORM，全部走 repo；写库/实时查询两类明确分离
- **repo**：每个聚合根（27 个有效聚合根）有清晰接口；表模型与 BO 字段一一对齐

### 1.2 功能链路（用户视角）

```
前端 CollectActionCard.vue
  ↓ POST /api/collect/{facet}/{service_name} { mode, params }
  ↓
interface/route/{facet}.py
  ↓ CollectRequest DTO 校验（mode 枚举、params schema 推断）
  ↓ Depends(get_xxx_service)
  ↓
application/service/xxx_service.py
  ↓
  ├─ 写库类（daily_kline / moneyflow / top_list ...）                  实时查询类（minute_kline / concept_minute ...）
  │  1) fetcher.fetch(**) → list[BO]                                  1) fetcher.fetch(**) → list[BO]
  │  2) repo.save(bos) → int                                         2) BO → dict（直接返回，不入库）
  │  3) CollectResponse
  │
  ↓ 或 ↓
infrastructure/repo/xxx_repo.py                              fetcher 直接返回
  ↑      接受 list[BO]，调 ORM upsert
  ↑
infrastructure/persistence/models/    ← ORM 模型（30 张表已与文档对齐）
  ↑
shared/connection/db_factory.py      ← db_session_factory
```

### 1.3 不在本批范围

- 限流 / 重试装饰器抽离（Phase 5 单独做）
- scheduler / APScheduler / 定时（Phase 6 单独做）
- RunLog / Task / Plan 持久化（Phase 6 单独做）
- 前端 CollectActionCard 改造（另一批）
- query endpoint 的 DTO 化（GET 实时查询不归本批）

---

## 二、当前三层现状（与 DDD 偏差）

> 全部路径基于 `backend/src/contexts/collect/`

### 2.1 interface 层（基本合规，缺 DTO）

**现状结构**（已与 DDD 一致）：
```
contexts/collect/interface/
├── router.py                # catalog_router + facet_routers 元组
├── route/
│   ├── tech/__init__.py
│   ├── capital/__init__.py
│   ├── fundamental/__init__.py
│   ├── news/__init__.py
│   └── sentiment/__init__.py
└── dto/
    ├── request/collect.py   # CollectJobSaveRequest（采集方案保存用，不是 collect 触发）
    └── response/collect.py  # TaskDefResponse（采集元数据用，已知无引用，按 D5 删除）
```

**与 DDD 的偏差**：

| 偏差 | 位置 | 影响 |
|---|---|---|
| ① route 内的 `CollectBody`（mode/params）**内联定义在 route 文件**，未走 DTO | `route/tech/__init__.py:30-40` | 前端 payload 字段契约不清晰；不同 facet 路由各自重复 |
| ② `dto/response/collect.py` 内容是**采集任务**元数据，与当前 `collect()` 触发响应无关 | `dto/response/collect.py` | 按 D5 决策删除（含 `TaskDefResponse` / `FacetGroupResponse` / `CollectCatalogResponse` / `CollectFetcherResponse` / `CollectPlanItemResponse` / `CollectPlanResponse`） |
| ③ `interface/dto/request/collect.py` 内的 `CollectJobSaveRequest` **未在 route 中被任何 endpoint 使用** | route/* | DTO 死代码；本批同步删除（与 D5 同思路） |
| ④ `services` / `query/{name}` 的 404/400 错误**用 HTTPException 抛字符串** | `interface/router.py:280-300` | 响应体格式与其它 endpoint 不一致（次要，下批） |

### 2.2 application / service 层（核心偏差：inline ORM）

**现状结构**（28 个 service，按 5 个 facet 分目录）：
```
contexts/collect/application/service/
├── base.py                 # CollectResult / CollectService Protocol
├── tech/                   # 5 个：daily_kline / minute_kline / adj_factor / suspend / name_change
├── capital/                # 9 个：moneyflow / moneyflow_hsgt / top_list / top_inst / block_trade /
│                           #       margin / hsgt_top10 / limit_list / holder_number
├── fundamental/            # 12 个：daily_basic / fin_income / top10_holders / top10_floatholders /
│                           #       dividend / stock_basic / stock_concepts / concept_list / concept_members /
│                           #       concept_index_daily / concept_minute / concept_snapshot
├── news/                   # 1 个：news
└── sentiment/              # 1 个：sentiment（空壳/隐藏）
```

**27 个实际生效 service 的入库实现分布**：

| 类别 | 数量 | 备注 |
|---|---|---|
| ✅ **已抽 repo**（service 内调 Repository 类） | 3 | `DailyKlineService` → `KlineRepository`（独立文件）；`StockBasicService` → `StockInfoRepository`（独立文件）；`AdjFactorService` → 内联 `AdjFactorRepository`（同文件） |
| ❌ **直接 inline ORM**（service 内 `pg_insert + db_session_factory`） | 11 | `BlockTradeService` / `MoneyflowService` / `TopListService` / `TopInstService` / `MarginService` / `MoneyflowHsgtService` / `HsgtTop10Service` / `LimitListService` / `HolderNumberService` / `DailyBasicService` / `ConceptListService` |
| ❌ **未实现入库**（拿到 BO 只统计条数，不落库） | 7 | `FinIncomeService` / `Top10HoldersService` / `Top10FloatHoldersService` / `DividendService` / `ConceptIndexDailyService` / `ConceptMembersService` / `ConceptSnapshotService` |
| ⚠️ **未实现入库（仅 collect 占位，无 fetch）** | 3 | `SuspendService` / `NameChangeService` / `NewsService` |
| 🔄 **实时查询（无需入库）** | 3 | `MinuteKlineService` / `ConceptMinuteService` / `ConceptSnapshotService`（按 D3，本次兼做"实时查询+采集入库"两类） |

**重新整理（按 D3 决策，本批全部走 repo）**：

| 类别 | 数量 | service |
|---|---|---|
| **写库 service**（collect 走 repo） | 25 | `daily_kline` / `adj_factor` / `suspend` / `name_change` / `moneyflow` / `moneyflow_hsgt` / `top_list` / `top_inst` / `block_trade` / `margin` / `hsgt_top10` / `limit_list` / `holder_number` / `daily_basic` / `fin_income` / `top10_holders` / `top10_float_holders` / `dividend` / `stock_basic` / `stock_concepts` / `concept_list` / `concept_members` / `concept_index_daily` / `concept_snapshot` / `news` |
| **实时查询 service**（无 repo，只有 `get()`） | 2 | `minute_kline` / `concept_minute` |
| **空壳/隐藏 service** | 1 | `sentiment` |

> **最终分布**：25 写库 + 2 实时查询 + 1 空壳 = **28 service**。

**与 DDD 的偏差**：

| 偏差 | 严重度 | 例子 |
|---|---|---|
| ① **service 直接 import ORM 模型 + 调 pg_insert** | 🔴 高 | `block_trade_service.py:60-78` 内联 `pg_insert(CapBlockTradeDB)` |
| ② **service 直接 import `db_session_factory`** | 🔴 高 | 11 个 service 都 import `from shared.infrastructure.connection.db_factory import db_session_factory` |
| ③ **service 内 import `RateLimited` + 写 3 次重试循环** | 🟡 中 | 27 个 service 中 26 个 service 有完全相同的 3 次重试样板代码（**本批不动**，Phase 5） |
| ④ **service 内的限流/重试样板代码几乎一模一样** | 🟡 中 | `await check(self.RATE_LIMIT)` + `for attempt in range(3)` + `except RateLimited`（**本批不动**） |
| ⑤ **CollectResult 字段有 5 个（total/success/fail/skip/saved），但**部分 service 只填 1-2 个** | 🟡 中 | `ConceptListService` 错把 `saved=0` 当 `skip=1` |
| ⑥ **无 `domain/` 目录**（service 直接 import ORM 模型） | 🔴 高 | DDD 要求 `application → domain (repository 接口) ← infrastructure (实现)`；目前 application 直接 import infrastructure 的 ORM |
| ⑦ **部分 service 通过 `getattr(r, "name")` 等访问 BO 的属性** | 🟢 低 | OK，但应明确 BO 字段名与 ORM 列名的一致性约束 |
| ⑧ **`_save` 方法参数类型不一致**：有的 `bos: list[BO]`，有的 `bos: list` | 🟡 中 | 缺少 BO → row 的统一转换函数（**D4 决策放 repo 内部**） |

### 2.3 infrastructure / repo 层（残缺）

**现状结构**：
```
contexts/collect/infrastructure/
├── di/
│   ├── __init__.py
│   └── collect_service.py    # 28 个 get_xxx_service() 工厂（按 facet 分组）
├── connect/
│   ├── tushare_client.py     # 单例 TushareClient
│   ├── adata_client.py
│   └── pytdx_client.py
├── parser/tushare.py         # symbol_to_ts_code / num / text / rows 等
├── cache/rate_limit.py       # Redis check()
├── retry.py
├── fetcher/                  # 27 个 fetcher（已全部同步）
└── persistence/
    ├── models/               # 30 个 ORM 模型（已与文档对齐）
    └── repositories/
        ├── __init__.py
        ├── kline_repo.py          # ✅ KlineRepository（save_klines/find/get_coverage）
        └── stock_info_repo.py     # ✅ StockInfoRepository（save_batch/find/list_symbols）
```

**与 DDD 的偏差**：

| 偏差 | 严重度 | 影响 |
|---|---|---|
| ① **30 张表只有 2 个 repo**（Kline + StockInfo） | 🔴 高 | 26 张表的 ORM 模型没人用（service 直接 inline 用，或根本没入库） |
| ② **无 `domain/` 层**（无 repository 接口 Protocol） | 🔴 高 | DDD §2.1 要求"repository 接口在 domain，infrastructure 实现"；目前 application 直接 import infrastructure 的 ORM |
| ③ **repositories 目录位置正确**（在 `infrastructure/persistence/repositories/`） | ✅ | 符合 DDD §2.4 |
| ④ **di/collect_service.py** 提供 `get_xxx_service()` 工厂，**但都是 `DefaultConstruct`**（无状态） | ✅ | 符合 DDD §2.4（业务 DI 自管理） |
| ⑤ **30 个 ORM 模型已与表结构 100% 对齐** | ✅ | 上次表结构修复已完成 |
| ⑥ **缺一个 `repositories/__init__.py` 总览**（已存在但仅 re-export） | ✅ | OK |

---

## 三、目标架构（落地后状态）

### 3.1 interface 层

```
contexts/collect/interface/
├── router.py                # catalog_router（不变）
├── deps.py                  # 暂不新增（横切依赖本批用不到）
├── route/
│   ├── tech/__init__.py
│   ├── capital/__init__.py
│   ├── fundamental/__init__.py
│   ├── news/__init__.py
│   └── sentiment/__init__.py
└── dto/
    ├── request/
    │   └── collect.py       # 新增 CollectRequest（mode + params）；CollectJobSaveRequest 同步删除（D5）
    └── response/
        └── collect.py       # 新增 CollectResponse（对齐 application/service/base.py::CollectResult）
```

> **不再**有 `response/trigger.py` / `response/query.py`——DTO 命名用业务语义 `collect.py`。

### 3.2 application 层

```
contexts/collect/application/
├── service/
│   ├── base.py                 # CollectService Protocol / CollectResult（既有）
│   ├── tech/                   # 5 个 service（结构不变，全部走 repo）
│   ├── capital/                # 9 个 service
│   ├── fundamental/            # 12 个 service
│   ├── news/                   # 1 个 service
│   └── sentiment/              # 1 个 service（空壳/隐藏）
├── bo/                         # 既有（已同步完成）
└── port/                       # 既有（params / errors）
```

> **本批不引入** `service/_common.py`（装饰器抽离延后 Phase 5）。

### 3.3 domain 层（新增，27 个有效聚合根 + 25 个 Protocol）

```
contexts/collect/domain/
├── __init__.py
├── exceptions.py               # 新增：业务级异常（InvalidParams / NotSupported）
└── entitys/                    # 27 个有效聚合根
    ├── kline/                  # 既有 Kline entity / repository（迁 KlineRepository Protocol）
    │   ├── entity.py
    │   ├── repository.py       # KlineRepository Protocol
    │   └── vo.py
    ├── stock_info/
    ├── adj_factor/             # 新增
    ├── moneyflow/              # 新增
    ├── moneyflow_hsgt/         # 新增
    ├── top_list/               # 新增
    ├── top_inst/               # 新增
    ├── block_trade/            # 新增
    ├── margin_detail/          # 新增
    ├── hsgt_top10/             # 新增
    ├── limit_list/             # 新增
    ├── holder_number/          # 新增
    ├── fin_daily_basic/        # 新增
    ├── fin_report/             # 新增（fin_income）
    ├── fin_top10_holders/      # 新增
    ├── fin_top10_float/        # 新增
    ├── dividend/               # 新增
    ├── stock_concept/          # 新增
    ├── concept/                # 新增（concept_list）
    ├── concept_member/         # 新增
    ├── concept_index/          # 新增
    ├── concept_snapshot/       # 新增
    ├── suspend/                # 新增
    ├── name_change/            # 新增
    └── news_article/           # 新增
```

> 27 个有效聚合根（D1 严格 DDD）。`sentiment` 空壳不计。

### 3.4 infrastructure 层

```
contexts/collect/infrastructure/
├── di/
│   ├── __init__.py
│   ├── collect_service.py     # 既有 28 个 get_xxx_service()，改 Depends(repo)
│   └── repo.py                # 新增：25 个 get_xxx_repository() 工厂
├── persistence/
│   ├── models/                # 既有 30 个 ORM
│   └── repositories/          # 由 2 个扩到 25 个
│       ├── kline_repo.py
│       ├── stock_info_repo.py
│       ├── adj_factor_repo.py
│       ├── ...  共 25 个
│       └── __init__.py
├── connect/, cache/, parser/, retry.py, fetcher/  # 既有（不动）
```

---

## 四、详细改造方案（按层）

### 4.1 interface 层改造（P1，28 个 endpoint 共享）

#### 4.1.1 重写 `dto/request/collect.py`

```python
"""采集 trigger 请求 DTO（POST 触发）

按 D5 决策：本文件覆盖原 CollectJobSaveRequest 死代码，统一用业务语义命名。
"""
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class CollectRequest(BaseModel):
    """POST /api/collect/{facet}/{service_name} 请求体"""
    mode: Literal["full", "condition"] = "condition"
    params: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _strip_empty(self) -> "CollectRequest":
        # 过滤空字符串/空数组/None，避免 "symbols 必填" 误报
        cleaned = {k: v for k, v in self.params.items()
                   if v not in (None, "", [], {})}
        self.params = cleaned
        return self
```

> **删除**原 `CollectJobSaveRequest`（scheduler 阶段会重新设计，路径可能不同；本批清空）。

#### 4.1.2 重写 `dto/response/collect.py`

```python
"""采集 trigger 响应 DTO（POST 执行结果）

字段对齐 application/service/base.py::CollectResult；不引入新字段。
"""
from pydantic import BaseModel


class CollectResponse(BaseModel):
    """POST /api/collect/{facet}/{service_name} 响应"""
    total: int = 0
    success: int = 0
    fail: int = 0
    skip: int = 0
    saved: int = 0
    message: str = ""
```

> **删除**原 `dto/response/collect.py` 中的 6 个旧 DTO：`TaskDefResponse` / `FacetGroupResponse` / `CollectCatalogResponse` / `CollectFetcherResponse` / `CollectPlanItemResponse` / `CollectPlanResponse`（D5）。

#### 4.1.3 改造 5 个 `route/{facet}/__init__.py`

把内联的 `CollectBody` 替换为 `CollectRequest`；响应改为 `CollectResponse`：

```python
# route/tech/__init__.py（示范）
from fastapi import APIRouter, Depends
from contexts.collect.interface.dto.request.collect import CollectRequest
from contexts.collect.interface.dto.response.collect import CollectResponse
from contexts.collect.application.service.base import CollectService
from contexts.collect.infrastructure.di.collect_service import (
    get_daily_kline_service, get_minute_kline_service, get_adj_factor_service,
    get_suspend_service, get_name_change_service,
)

router = APIRouter(prefix="/collect/tech", tags=["采集-技术面"])

async def _run(svc: CollectService, body: CollectRequest) -> CollectResponse:
    merged = {**body.params, "mode": body.mode}
    result = await svc.collect(merged)
    return CollectResponse(
        total=result.total, success=result.success, fail=result.fail,
        skip=result.skip, saved=result.saved, message=result.message,
    )

@router.post("/daily_kline", summary="日 K 线采集（按 symbol 批量）", response_model=CollectResponse)
async def daily_kline_trigger(body: CollectRequest, svc=Depends(get_daily_kline_service)):
    return await _run(svc, body)

# 其余 4 个 endpoint 同模式
```

#### 4.1.4 interface 层改造清单

| 文件 | 动作 |
|---|---|
| `dto/request/collect.py` | 替换：`CollectJobSaveRequest` → `CollectRequest` |
| `dto/response/collect.py` | 替换：删除 6 个旧 DTO → 新增 `CollectResponse` |
| `route/tech/__init__.py` | 重构：内联 `CollectBody` → `CollectRequest`；响应 → `CollectResponse` |
| `route/capital/__init__.py` | 同上（9 个 endpoint） |
| `route/fundamental/__init__.py` | 同上（12 个 endpoint） |
| `route/news/__init__.py` | 同上（1 个 endpoint） |
| `route/sentiment/__init__.py` | 同上（1 个 endpoint，隐藏） |

> `interface/router.py` 的 query endpoint **本批不改**（D3 不动 query；DTO 化放到 Phase 5 之后单独做）。

### 4.2 application / service 层改造（核心）

#### 4.2.1 service 改写原则

- **写库 service（25 个）**：`collect()` 流程统一为
  ```
  1) 解析 params（symbols / trade_date / ...）
  2) 调 fetcher.fetch(**) → list[BO]
  3) 调 self._repo.save(bos) → int
  4) 返回 CollectResult(total=..., success=..., saved=saved, ...)
  ```
  限流/重试样板**保留**（本批不动）。
- **实时查询 service（2 个，minute_kline / concept_minute）**：`get()` 流程
  ```
  1) 解析 params
  2) 调 fetcher.fetch(**) → list[BO]
  3) BO → dict
  4) 返回 list[dict]
  ```
  无 repo。`collect()` 返回"请用 get()"提示。
- **空壳 service（1 个，sentiment）**：保留 `name/facet/label` 类属性，方法抛 `NotImplementedError`。

#### 4.2.2 service 模板（写库类）

```python
"""adj_factor_service.py 模板（写库类）"""
from contexts.collect.application.service.base import CollectResult
from contexts.collect.application.bo import BaseAdjFactorBO
from contexts.collect.infrastructure.fetcher.tech.AdjFactorTushareFetcher import AdjFactorTushareFetcher

class AdjFactorService:
    name = "adj_factor"
    facet = "tech"
    sub_facet = "adj"
    label = "复权因子"
    DEFAULT_PARAMS = {"symbols": []}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 5

    def __init__(
        self,
        fetcher: AdjFactorTushareFetcher | None = None,
        repo: "AdjFactorRepository" | None = None,   # 由 DI 注入
    ) -> None:
        self._fetcher = fetcher or AdjFactorTushareFetcher()
        self._repo = repo

    async def collect(self, params: dict) -> CollectResult:
        # ... 限流 / 重试 / 业务逻辑保留 ...
        bos: list[BaseAdjFactorBO] = await self._fetcher.fetch(symbol=symbol)
        saved = await self._repo.save(bos)
        return CollectResult(total=1, success=1, saved=saved, message=...)
```

> `AdjFactorRepository` 是 type hint（Protocol），service 不直接 import 具体实现类。

#### 4.2.3 service 模板（实时查询类）

```python
"""minute_kline_service.py 模板（实时查询类，无 repo）"""
from contexts.collect.application.service.base import CollectResult
from contexts.collect.infrastructure.fetcher.tech.MinuteKlinePytdxFetcher import MinuteKlinePytdxFetcher

class MinuteKlineService:
    name = "minute_kline"
    facet = "tech"
    sub_facet = "kline_minute"
    label = "分钟 K 线"
    DEFAULT_PARAMS = {"symbol": None, "interval": "5min", "days": 1}
    RATE_LIMIT = ("pytdx", 60, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: MinuteKlinePytdxFetcher | None = None) -> None:
        self._fetcher = fetcher or MinuteKlinePytdxFetcher()
        # 无 self._repo

    async def collect(self, params: dict) -> CollectResult:
        return CollectResult(message="MinuteKline 是实时查询 service，请使用 get()")

    async def get(self, symbol: str, interval: str = "5min", days: int = 1) -> list[dict]:
        bos = await self._fetcher.fetch(symbol=symbol, interval=interval, days=days)
        return [b.model_dump() for b in bos]   # BO 直接 dict
```

#### 4.2.4 service 改造清单（28 个 service）

| service | 现状 | 改造动作 |
|---|---|---|
| **tech 5** | | |
| `DailyKlineService` | ✅ 已抽 KlineRepository | type hint `list[Kline]`；service 入参 `repo: KlineRepository` |
| `MinuteKlineService` | ✅ 实时查询，无需 repo | type hint + 改用 `model_dump()` 返回 |
| `AdjFactorService` | ⚠️ 内联 `AdjFactorRepository`（同文件） | 迁 repo 到 `infrastructure/persistence/repositories/adj_factor_repo.py`；service 改 Depends 注入 |
| `SuspendService` | ❌ 无入库 | **新增** `SuspendRepository` + service 调 repo |
| `NameChangeService` | ❌ 无入库 | **新增** `NameChangeRepository` + service 调 repo |
| **capital 9** | | |
| `MoneyflowService` | ❌ inline ORM | 抽 `MoneyflowRepository`；service 改调 |
| `MoneyflowHsgtService` | ❌ inline ORM | 抽 `MoneyflowHsgtRepository` |
| `TopListService` | ❌ inline ORM | 抽 `TopListRepository` |
| `TopInstService` | ❌ inline ORM | 抽 `TopInstRepository` |
| `BlockTradeService` | ❌ inline ORM | 抽 `BlockTradeRepository` |
| `MarginService` | ❌ inline ORM | 抽 `MarginDetailRepository` |
| `HsgtTop10Service` | ❌ inline ORM | 抽 `HsgtTop10Repository` |
| `LimitListService` | ❌ inline ORM | 抽 `LimitListRepository` |
| `HolderNumberService` | ❌ inline ORM | 抽 `HolderNumberRepository` |
| **fundamental 12** | | |
| `DailyBasicService` | ❌ inline ORM | 抽 `FinDailyBasicRepository` |
| `FinIncomeService` | ❌ 无入库 | **新增** `FinReportRepository` + service 调 repo |
| `Top10HoldersService` | ❌ 无入库 | **新增** `FinTop10HoldersRepository` + service 调 repo |
| `Top10FloatHoldersService` | ❌ 无入库 | **新增** `FinTop10FloatHoldersRepository` + service 调 repo |
| `DividendService` | ❌ 无入库 | **新增** `DividendRepository` + service 调 repo |
| `StockBasicService` | ✅ 已抽 `StockInfoRepository` | type hint；service 入参 `repo: StockInfoRepository` |
| `StockConceptsService` | ❌ 无入库 | **新增** `StockConceptRepository` + service 调 repo |
| `ConceptListService` | ❌ inline ORM | 抽 `ConceptRepository`（in concept context） |
| `ConceptMembersService` | ❌ 无入库 | **新增** `ConceptMemberRepository` + service 调 repo |
| `ConceptIndexDailyService` | ❌ 无入库 | **新增** `ConceptIndexRepository` + service 调 repo |
| `ConceptMinuteService` | ✅ 实时查询 | type hint + 改用 `model_dump()` 返回 |
| `ConceptSnapshotService` | ✅ 实时查询（兼 collect） | **新增** `ConceptSnapshotRepository` + service 调 repo；`get()` 保留实时查询 |
| **news 1** | | |
| `NewsService` | ❌ 无入库 | **新增** `NewsArticleRepository` + service 调 repo（fetcher 返回 `list[dict]`，service 内 dict → row） |
| **sentiment 1** | | |
| `SentimentService` | 空壳/隐藏 | 不动 |

### 4.3 domain 层新增（DDD 严格，D1=27 个聚合根 + D2=27 个 Protocol）

#### 4.3.1 通用 repository Protocol 模板

```python
# contexts/collect/domain/entitys/adj_factor/repository.py
from typing import Protocol
from contexts.collect.application.bo import BaseAdjFactorBO

class AdjFactorRepository(Protocol):
    """复权因子仓储协议（domain 层定义）

    infrastructure.persistence.repositories.adj_factor_repo.AdjFactorRepository 实现此 Protocol。
    service 通过 Depends 注入，不直接 import infrastructure 实现。
    """
    async def save(self, bos: list[BaseAdjFactorBO]) -> int: ...
    async def find_by_symbol(self, symbol: str) -> list[BaseAdjFactorBO]: ...
    async def delete_by_symbol(self, symbol: str) -> int: ...
```

#### 4.3.2 25 个聚合根的 Protocol 文件（D2：写库才有 Protocol，实时查询无 Protocol）

| 聚合根目录 | repository.py 文件 | 协议方法 |
|---|---|---|
| `kline/` | KlineRepository Protocol | `save` / `find` / `get_coverage` / `delete_by_symbol` |
| `stock_info/` | StockInfoRepository Protocol | `save` / `find` / `list_symbols` / `list_dates` |
| `adj_factor/` | AdjFactorRepository Protocol | `save` / `find_by_symbol` / `delete_by_symbol` |
| `moneyflow/` | MoneyflowRepository Protocol | `save` / `find_by_date` / `delete_by_date` |
| `moneyflow_hsgt/` | MoneyflowHsgtRepository Protocol | `save` / `find_by_date` / `delete_by_date` |
| `top_list/` | TopListRepository Protocol | `save` / `find_by_date` |
| `top_inst/` | TopInstRepository Protocol | `save` / `find_by_date` |
| `block_trade/` | BlockTradeRepository Protocol | `save` / `find_by_date` |
| `margin_detail/` | MarginDetailRepository Protocol | `save` / `find_by_date` |
| `hsgt_top10/` | HsgtTop10Repository Protocol | `save` / `find_by_date` |
| `limit_list/` | LimitListRepository Protocol | `save` / `find_by_date` / `delete_by_date` |
| `holder_number/` | HolderNumberRepository Protocol | `save` / `find_by_symbol` |
| `fin_daily_basic/` | FinDailyBasicRepository Protocol | `save` / `find_by_date` / `delete_by_date` |
| `fin_report/` | FinReportRepository Protocol | `save` / `find_by_symbol` |
| `fin_top10_holders/` | FinTop10HoldersRepository Protocol | `save` / `find_by_date` |
| `fin_top10_float/` | FinTop10FloatHoldersRepository Protocol | `save` / `find_by_date` |
| `dividend/` | DividendRepository Protocol | `save` / `find_by_symbol` |
| `stock_concept/` | StockConceptRepository Protocol | `save` / `find_by_symbol` / `delete_by_symbol` |
| `concept/` | ConceptRepository Protocol | `save` / `find` / `list_all_codes` |
| `concept_member/` | ConceptMemberRepository Protocol | `save` / `find_by_index` / `delete_by_index` |
| `concept_index/` | ConceptIndexRepository Protocol | `save` / `find_by_index` / `delete_by_index` |
| `concept_snapshot/` | ConceptSnapshotRepository Protocol | `upsert` / `find_by_index` |
| `suspend/` | SuspendRepository Protocol | `save` / `find_by_date` |
| `name_change/` | NameChangeRepository Protocol | `save` / `find_by_symbol` |
| `news_article/` | NewsArticleRepository Protocol | `save` / `find` / `delete_by_published_at` |
| `kline_minute/` | ❌ 无（实时查询，无 repo） | — |
| `concept_minute/` | ❌ 无（实时查询，无 repo） | — |
| `sentiment/` | ❌ 无（空壳） | — |

> **25 个 Protocol**（写库聚合根）；2 个实时查询 + 1 个空壳 = 28 service 共 25 个 Protocol。

#### 4.3.3 `domain/exceptions.py`

```python
"""业务级异常（DDD §2.4「异常分层」）

与 application/port/errors.py 的区别：
  - port/errors.py 装 port 契约级异常（RateLimited/SourceUnavailable），由 SDK 翻译
  - domain/exceptions.py 装业务规则违反（参数/能力合规），由 entity 自身抛
"""
class InvalidParams(ValueError): ...
class NotSupported(NotImplementedError): ...
class SymbolNotFound(KeyError): ...
```

### 4.4 infrastructure / repo 层改造（核心）

#### 4.4.1 25 个 repo 增量清单

```
contexts/collect/infrastructure/persistence/repositories/
├── kline_repo.py                # 既有（KlineRepository 实现）
├── stock_info_repo.py           # 既有（StockInfoRepository 实现）
├── adj_factor_repo.py           # 新增
├── moneyflow_repo.py            # 新增
├── moneyflow_hsgt_repo.py       # 新增
├── top_list_repo.py             # 新增
├── top_inst_repo.py             # 新增
├── block_trade_repo.py          # 新增
├── margin_detail_repo.py        # 新增
├── hsgt_top10_repo.py           # 新增
├── limit_list_repo.py           # 新增
├── holder_number_repo.py        # 新增
├── fin_daily_basic_repo.py      # 新增
├── fin_report_repo.py           # 新增
├── fin_top10_holders_repo.py    # 新增
├── fin_top10_float_repo.py      # 新增
├── dividend_repo.py             # 新增
├── stock_concept_repo.py        # 新增
├── concept_repo.py              # 新增（concept_list 入库到 concept DB）
├── concept_member_repo.py       # 新增
├── concept_index_repo.py        # 新增
├── concept_snapshot_repo.py     # 新增
├── suspend_repo.py              # 新增
├── name_change_repo.py          # 新增
├── news_article_repo.py         # 新增
└── __init__.py                  # 既有，re-export
```

> **25 个 repo**（`kline_minute` 和 `concept_minute` 是实时查询无 repo；`sentiment` 空壳也无 repo）

#### 4.4.2 Repository 通用规范（D4 决策：BO → row 转换放 repo 内部）

```python
# adj_factor_repo.py 模板
from sqlalchemy.dialects.postgresql import insert as pg_insert
from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.collect.infrastructure.persistence.models.adj_factor import AdjFactorDB
from contexts.collect.application.bo import BaseAdjFactorBO


class AdjFactorRepository:
    """复权因子仓储（实现 domain Protocol）"""

    async def save(self, bos: list[BaseAdjFactorBO]) -> int:
        if not bos:
            return 0
        rows = [self._to_row(b) for b in bos]
        async with db_session_factory() as session:
            stmt = pg_insert(AdjFactorDB).values(rows)
            update_cols = {c.name: stmt.excluded[c.name] for c in AdjFactorDB.__table__.columns
                           if c.name not in ("id", "created_at", "symbol", "trade_date")}
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "trade_date"],
                set_=update_cols,
            )
            r = await session.execute(stmt)
            await session.commit()
            return r.rowcount or len(rows)

    @staticmethod
    def _to_row(b: BaseAdjFactorBO) -> dict:
        """BO → ORM row（D4 决策：转换放 repo 内部）"""
        return {"symbol": b.symbol, "trade_date": b.trade_date, "adj_factor": b.adj_factor}
```

#### 4.4.3 upsert 模式约定

| 表 | upsert key | delete before upsert? |
|---|---|---|
| `tech_kline_daily` | `(symbol, trade_date)` | ❌ upsert |
| `fundamental_stock_info` | `symbol` | ❌ upsert |
| `tech_adj_factor` | `(symbol, trade_date)` | ❌ upsert |
| `capital_moneyflow` | `(symbol, trade_date)` | ✅ delete-then-insert（按 trade_date 整日重写） |
| `capital_block_trade` | `(trade_date, symbol, buyer, seller)` | ✅ delete-then-insert |
| `fundamental_daily_basic` | `(symbol, trade_date)` | ✅ delete-then-insert |
| `capital_moneyflow_hsgt` | `(trade_date, symbol)` | ✅ |
| `capital_top_list` | `(trade_date, symbol)` | ✅ |
| `capital_top_inst` | `(trade_date, symbol, exalter, side)` | ✅ |
| `capital_margin_detail` | `(trade_date, symbol)` | ✅ |
| `capital_hsgt_top10` | `(trade_date, symbol, market_type, rank)` | ✅ |
| `capital_limit_list_d` | `(trade_date, symbol, limit_type)` | ✅ |
| `capital_holder_num` | `(symbol, end_date)` | ❌ upsert |
| `fundamental_report` | `(symbol, end_date, report_type)` | ❌ upsert |
| `fundamental_top10` | `(symbol, ann_date, end_date, holder_name)` | ✅ |
| `fundamental_top10_float` | `(symbol, ann_date, end_date, holder_name)` | ✅ |
| `fundamental_dividend` | `(symbol, end_date, ann_date)` | ❌ upsert |
| `fundamental_stock_concept` | `(symbol, index_code)` | ❌ upsert |
| `fundamental_concept` | `index_code` | ❌ upsert |
| `fundamental_concept_member` | `(index_code, symbol)` | ✅ delete-by-index-then-insert |
| `fundamental_concept_index` | `(index_code, trade_date)` | ❌ upsert |
| `fundamental_concept_snapshot` | `(index_code, trade_date)` | ❌ upsert |
| `tech_suspend` | `(symbol, trade_date)` | ✅ delete-by-date |
| `tech_name_change` | `(symbol, name, start_date)` | ❌ upsert |
| `news_article` | `(published_at, title)` | ❌ upsert |

> 每个 repo 顶部用 docstring 标明：本表是 "upsert" 还是 "delete-then-insert"。

### 4.5 DI 层改造

#### 4.5.1 `infrastructure/di/repo.py`（新增）

```python
"""repo 工厂：service 通过 Depends 注入 repo"""


def get_kline_repository():
    from contexts.collect.infrastructure.persistence.repositories.kline_repo import KlineRepository
    return KlineRepository()

# ... 共 25 个 get_xxx_repository() 工厂
```

#### 4.5.2 `infrastructure/di/collect_service.py`（既有）改造

每个 `get_xxx_service()` 改为注入 repo（仅 25 个写库 service 改）：

```python
def get_adj_factor_service(
    repo: "AdjFactorRepository" = Depends(get_adj_factor_repository),
):
    from contexts.collect.application.service.tech.adj_factor_service import AdjFactorService
    return AdjFactorService(repo=repo)
```

> **25 个 service** 改 Depends(repo)；**3 个 service**（2 个实时查询 + 1 个空壳）保持现状。

---

## 五、改造时序与工作量估算

> 总工作量约 **7-10 个工作日**（单人）。装饰器抽离不再计入（延后 Phase 5）。

### Phase 1：抽 repo + service 改调 repo — 6-7 天

| 步骤 | 文件数 | 估算 |
|---|---|---|
| 1. 抽 `AdjFactorRepository`（已有内联版迁移）+ service 改造 | 2 | 0.5 天 |
| 2. 抽 `BlockTradeRepository` + service 改造 | 2 | 0.5 天 |
| 3. 抽 `MoneyflowRepository` + `MoneyflowHsgtRepository` | 3 | 0.5 天 |
| 4. 抽 `TopListRepository` + `TopInstRepository` | 3 | 0.5 天 |
| 5. 抽 `MarginDetailRepository` + `HsgtTop10Repository` | 3 | 0.5 天 |
| 6. 抽 `LimitListRepository` + `HolderNumberRepository` | 3 | 0.5 天 |
| 7. 抽 `FinDailyBasicRepository`（daily_basic） | 2 | 0.5 天 |
| 8. 抽 `FinReportRepository`（fin_income）+ service 接入 | 2 | 0.5 天 |
| 9. 抽 3 个新 repo（top10_holders / top10_float / dividend）+ service 接入 | 6 | 1 天 |
| 10. 抽 `NewsArticleRepository` + service 改造 | 2 | 0.5 天 |
| 11. 抽 `ConceptRepository`（concept_list 入库到 concept DB） | 2 | 0.5 天 |
| 12. 抽 3 个新 concept repo（members / index / snapshot）+ service 接入 | 6 | 1 天 |
| 13. 抽 `SuspendRepository` + `NameChangeRepository` + service 接入 | 4 | 0.5 天 |
| 14. 抽 `StockConceptRepository`（stock_concepts 表入库）+ service 接入 | 2 | 0.5 天 |

### Phase 2：domain 层（DDD 严格）— 1-2 天

| 步骤 | 范围 | 估算 |
|---|---|---|
| 1. 27 个聚合根目录 + repository Protocol | 27 | 1 天 |
| 2. `domain/exceptions.py` | 1 | 0.5 天 |
| 3. Kline / StockInfo 既有 entity 迁过来 | 2 | 0.5 天 |

### Phase 3：interface 层（DTO 化 + 旧 DTO 清理）— 1 天

| 步骤 | 范围 | 估算 |
|---|---|---|
| 1. 重写 `dto/request/collect.py`（含删除 `CollectJobSaveRequest`） | 1 | 0.25 天 |
| 2. 重写 `dto/response/collect.py`（删除 6 个旧 DTO，加 `CollectResponse`） | 1 | 0.25 天 |
| 3. 改造 5 个 route 文件 | 5 | 0.5 天 |

### Phase 4：DI 工厂 + 验收 — 1 天

| 步骤 | 范围 | 估算 |
|---|---|---|
| 1. 25 个 `get_xxx_repository()` 工厂 | 1 | 0.5 天 |
| 2. `collect_service.py` 25 个 service 改 Depends(repo) | 1 | 0.5 天 |
| 3. 跑全量回归 + mock 测试 | — | 0.5 天 |

---

## 六、决策项（已评审确认）

| # | 决策 | 选择 | 说明 |
|---|---|---|---|
| **D1** | 聚合根粒度 | **A 严格 DDD** | **27 个有效聚合根**（sentiment 空壳不计） |
| **D2** | Protocol 范围 | **B 全抽** | **25 个 Protocol**（2 个实时查询 + 1 个空壳无） |
| **D3** | 未入库 service 补做 | **A 全部补做** | 严格区分写库/实时查询两类 |
| **D4** | BO → row 转换位置 | **A repo 内部** | 每个 repo 一个 `_to_row(bo)` |
| **D5** | 旧 DTO 处置 | **B 删除无用** | 删除 `dto/response/collect.py` 中 6 个旧 DTO + `dto/request/collect.py` 中 `CollectJobSaveRequest` |

---

## 七、验收清单

### 7.1 静态验证

```bash
# 1. import 全 28 service + 25 repo
python -m scripts.verify_service_imports  # 本批新增

# 2. 既有 fetcher import 仍 OK
python -m scripts.verify_fetcher_imports

# 3. 既有 mock 测试仍 OK
python -m scripts.test_fetcher_mock
```

### 7.2 DDD 依赖方向检查

```python
# 1. domain 不应 import application 或 infrastructure
# 2. application 不应 import interface 或 infrastructure（具体实现）
# 3. infrastructure 可以 import application 和 domain

# 校验脚本（建议本批新增）
python -m scripts.verify_ddd_dependencies
```

### 7.3 ORM 是否还有 inline？

```bash
grep -r "pg_insert\|db_session_factory" backend/src/contexts/collect/application/service/
# 期望：无任何结果（全部移到 repo）
```

### 7.4 端到端回归

```bash
# 启动后端
uvicorn main:app --reload

# 跑前端
pnpm dev

# 28 个 endpoint 全部点一遍：全量 + 条件
```

### 7.5 DB 校验

```bash
python -m scripts.verify_raw_db_deep   # 既有：30 张表
# 新增：scripts.verify_collect_db_records.py  # 抽查每张表至少 1 条数据
```

### 7.6 service 类型检查

```python
# 写库 service 必须有 self._repo: XxxRepository
# 实时查询 service 必须无 self._repo
# service 内不应有 pg_insert / db_session_factory / 任何 import ORM 模型
```

---

## 八、改造前后对比

| 维度 | 改造前 | 改造后 |
|---|---|---|
| **service 数** | 28 | 28 |
| **service 内 inline ORM** | 11 | **0** |
| **service 完全未入库** | 11 | **0**（全部走 repo；2 个实时查询无 repo 是设计） |
| **写库 service** | 13（错乱混合） | **25**（明确） |
| **实时查询 service** | 3（混在写库 service 中） | **2**（明确） |
| **空壳 service** | 1 | **1** |
| **repo 数** | 2 | **25**（每张表 1 个） |
| **domain 聚合根** | 0 | **27** |
| **domain Protocol** | 0 | **25** |
| **route DTO 化** | 0/5 | **5/5** |
| **route response_model** | 无 | **CollectResponse（统一）** |
| **旧 DTO 死代码** | 7 个 | **0** |
| **校验** | 30 表对齐 + 16 mock | **+ DDD 依赖检查 + 25 repo import + 全量回归** |

---

## 九、风险与回退

### 9.1 风险

| 风险 | 概率 | 缓解 |
|---|---|---|
| repo 抽错主键 → 写入重复 | 中 | Phase 1 每个 repo 完成后跑 `verify_raw_db_deep` 抽样 |
| service 重构引入回归 | 中 | 16 个 fetcher mock 测试 + 28 endpoint 全量回归 |
| 限流/重试延后导致 service 体积没减小 | 低 | 本批重点是"调 repo"，不是"减少样板"；装饰器延后 Phase 5 |
| DDD 拆分过细 | 中 | 27 聚合根（不是 28，sentiment 排除），每个文件约 30 行 |

### 9.2 回退策略

每 Phase 独立 commit；任一 Phase 失败可 `git revert` 单 phase。

---

## 十、后续 PR 排队

| 序号 | PR | 依赖 | 状态 |
|---|---|---|---|
| **#P3-1** | Phase 1: 抽 25 个 repo + 11 个 inline ORM service 改调 repo + 7 个未入库 service 接入 | — | 本批 |
| **#P3-2** | Phase 2: domain 层 27 聚合根 + 25 Protocol + exceptions | P3-1 | 本批 |
| **#P3-3** | Phase 3: interface 层 DTO 化 + 旧 DTO 清理 | — | 本批 |
| **#P3-4** | Phase 4: DI 工厂 + 验收脚本 + 全量回归 | P3-1 + P3-2 + P3-3 | 本批 |
| **#P3-5**（延后） | Phase 5: 限流/重试装饰器抽离（25 service 共用） | P3-4 | 延后 |
| **#P3-6**（延后） | Phase 6: scheduler / APScheduler / RunLog | P3-5 | 延后 |

---

**总结**：
- **本次 4 个 Phase，7-10 工作日**，落地后 25 写库 + 2 实时查询 + 1 空壳 = 28 service 全部规范化。
- 严格 DDD：27 聚合根 + 25 Protocol（不含 2 个实时查询 + 1 个空壳）。
- 限流重试/装饰器**延后到 Phase 5**（P3-5），不影响本批落地。
- DTO 命名用业务语义 `CollectRequest`/`CollectResponse`（不再叫 `trigger`）；旧 7 个 DTO 删除。
- PR 拆 4 个，每个 Phase 独立可回退。
