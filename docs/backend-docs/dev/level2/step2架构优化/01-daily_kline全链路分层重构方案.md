# daily_kline 全链路分层重构方案

> 位置：`docs/backend-docs/dev/level2/step2架构优化/01-daily_kline全链路分层重构方案.md`
> 配套文档：
> - `../step1采集模块优化/03整体同步/01-interface-service-repo同步方案.md`（上一轮：全量 28 service 铺开，本轮只做 1 条线的深改）
> - `../step1采集模块优化/08session注入修正/01-session注入修正方案.md`（session 注入约定，本轮沿用并补充「后台任务例外」说明）
> - `docs/config/DDD.md`（分层规范）
> 更新日期：2026-10-21
> 状态：**待评审（暂不修改代码）**

---

## 〇、决策与方向（评审前先看）

### 0.1 本批范围

只做 **1 条线**：`daily_kline`（日 K 线采集）。

| 层 | 文件 |
|---|---|
| interface | `collect/interface/route/tech/__init__.py` + 新增 `collect/interface/dto/request/tech.py` |
| application | `collect/application/service/tech/daily_service.py` + `collect/application/port/params.py` |
| infrastructure/fetcher | `collect/infrastructure/fetcher/tech/DailyTushareFetcher.py` + `collect/infrastructure/fetcher/base.py` |
| infrastructure/repo | `collect/infrastructure/persistence/repositories/kline_repo.py` |
| infrastructure/DI | `collect/infrastructure/di/collect_service.py` + `collect/infrastructure/di/repo.py` |

> **不铺开到其余 24 个 service**。上一轮（step1）已经把「抽 repo + service 调 repo」铺开了，但 `daily` 是唯一漏网的——它是唯一仍在 service 里 inline SQL 的写库 service。先把这一条做深做透，产出可复制的模板，再横向推广（见 §10）。

### 0.2 关键名词

- **Params**：application 层的入参模型（Pydantic，`extra="forbid"`），业务语义字段，不含 SDK 特有格式（`ts_code` / `"20261013"`）。
- **BO**：fetcher 出口的数据模型（`KlineBO`），已在 `market/application/bo/kline.py` 定义，**本轮不动**。
- **Request DTO**：interface 层的入参模型，会出现在 OpenAPI 里，是前端的唯一契约来源。
- **写库 service**：`collect()` 触发后台采集 → fetcher 取数 → repo 落库。
- **实时查询 service**：`get()` 直接读 DB，不入库。`daily` 两者都有（`collect()` 写库 + `get()` 查询）。

### 0.3 本批要解决的 5 个问题

| # | 问题 | 严重度 |
|---|---|---|
| **P1** | `service._save()` 直接 `pg_insert(TechKlineDailyDB)`，绕过 repo | 🔴 高 |
| **P2** | `service.get()` 直接 `select(TechKlineDailyDB)`，绕过 repo | 🔴 高 |
| **P3** | `service._list_all_symbols_via_session()` 直接查 `StockBasicDB`，绕过 repo | 🟡 中 |
| **P4** | 前端 → route → service → fetcher 全程 `params: dict`，无类型契约（`CollectRequest.params` 是 `dict`，OpenAPI 里是 `object`） | 🔴 高 |
| **P5** | `BaseFetcher.fetch(**params)` 无类型；`application/port/params.py` 已定义 6 个 Params 模型但**全仓无人 import**（死代码） | 🟡 中 |

### 0.4 顺带发现的既有缺陷（本轮不改，登记备查）

> 以下 4 项在写方案过程中发现，均**不属本方案范围**，但影响判断，一并列出：

| # | 位置 | 问题 |
|---|---|---|
| **X1** | `market/application/service/stock_info_service.py:221` + `market/infrastructure/di/stock_info.py:48` | `StockInfoService.collect()` 期望 `DailyService.collect()` 返回带 `.saved/.total/.message` 的对象，但 v4 后 `DailyService.collect()` 返回 `{"status":"pending"}` **dict** → `AttributeError`。且 `get_stock_info_service()` **根本没注入 `daily_svc`** → `POST /api/v1/klines/collect` 与 `/collect/batch` 必 502 |
| **X2** | `market/infrastructure/persistence/repositories/kline_repository.py:91` | `save_batch()` 写死 `constraint="uq_tech_kline_symbol_date"`，但表已重命名为 `tech_daily`、约束名改为 `uq_tech_daily_symbol_date`（`market/infrastructure/persistence/models/tech_kline.py:35`）。目前无调用方，**一旦被调用即 500** |
| **X3** | `collect/infrastructure/persistence/repositories/kline_repo.py:1-5` | docstring 写「DailyService 直接调本类的 save_klines()」，实际**从未被调用**（`get_kline_repository()` 无任何 `Depends`）。整文件为死代码 |
| **X4** | `collect/infrastructure/fetcher/tech/DailyTushareFetcher.py:60-85` | `_resolve_name()` 在 fetcher 内部回查 Tushare `stock_basic` 拉全量名称；而 `run_collect` 已经从 DB 读过 `stock_basic` 了。且异常分支下 `_names_loaded=True` 已置位，后续每只股票退化为一次单独 API 调用 |

---

## 一、目标与范围

### 1.1 目标

把 `daily_kline` 这一条线改造成**契约完整、职责单一**的形态，作为其余 24 个 service 的改造模板：

1. **route → service** 有类型契约（DTO → Params），入参错误在 HTTP 层就返回 422/400
2. **service** 不再 import 任何 ORM 模型、不再出现 `pg_insert` / `select`，只做编排
3. **fetcher** 入参出参都有类型，`BaseFetcher` 泛型化
4. **repo** 成为 `tech_daily` 表的**唯一**写入口，upsert 语义收敛到一处
5. **DI** 显式注入 repo，session 获取路径统一

### 1.2 数据链路对比

**改造前**（现状）：

```
前端 CollectActionCard.vue  { params: { start_date, end_date } }   ← Record<string, any>，无 schema
  ↓ POST /api/v1/collect/tech/daily_kline
route/tech/__init__.py      CollectRequest{ params: dict }        ← OpenAPI 里是 object
  ↓ svc.collect(dict)
DailyService.collect(params: dict)
  │   _validate_params()    手写 ISO 解析 / 起止校验 / 跨度校验      ← 本该 Pydantic 干的活
  ↓ asyncio.create_task(run_collect(dict))
DailyService.run_collect(params: dict)
  │   _parse_date_range()   再解析一遍 date
  │   _list_all_symbols_via_session()   ❌ select(StockBasicDB)    ← 越层
  │   _collect_one() → DailyTushareFetcher.fetch(symbol, start, end) → list[KlineBO]
  │   _save()               ❌ pg_insert(TechKlineDailyDB)        ← 越层
  │   get()                 ❌ select(TechKlineDailyDB)           ← 越层
  ↓
infrastructure/fetcher/DailyTushareFetcher
  │   fetch(**params)       ← kwargs 无类型
  │   _resolve_name()       ❌ 内部回查 Tushare stock_basic（DB 里已有）
  ↓
infrastructure/repositories/kline_repo.py  KlineRepository        ← ❌ 从未被调用
```

**改造后**（目标）：

```
前端  { start_date: "2026-10-01", end_date: "2026-10-21" }        ← 有 schema / 有必填提示
  ↓
route/tech/__init__.py
  │   body: DailyCollectRequest            ← OpenAPI 有完整 schema，缺字段直接 422
  ↓   DailyCollectRequest → DailyCollectParams
DailyService.collect(params: DailyCollectParams)
  │   Pydantic 校验（extra=forbid + 跨度 model_validator）
  ↓ asyncio.create_task(run_collect(params))
DailyService.run_collect(params: DailyCollectParams)
  │   self._repo.list_symbols(session)                     ← ✅ 走 repo
  │   self._fetcher.fetch(DailyKlineFetchParams) → list[KlineBO]
  │   self._repo.save_klines(klines, session)              ← ✅ 走 repo
  │   self._repo.find_by_symbol(...)   （get() 实时查询）    ← ✅ 走 repo
  ↓
infrastructure/fetcher/base.py  BaseFetcher[ParamsT, BOT]  ← 泛型，类型安全
infrastructure/repositories/kline_repo.py  KlineRepository  ← tech_daily 唯一写入口
```

### 1.3 不在本批范围

- 其余 24 个 collect service 的同步改造（见 §10 推广计划）
- `minute_kline` / `concept_minute` 等 REALTIME service 的 repo 化（无 repo 需求）
- `collect_task_runner.py`（TaskRunner）—— v4 协议已废弃该派发路径，仅剩 `adj_factor` 等老 service 还在用
- §0.4 的 X1–X4 四个既有缺陷
- 前端 `CollectActionCard.vue` 的类型定义（后端 DTO 定稿后再同步，前端可先用 TS 类型手工对齐）

---

## 二、当前现状（逐层）

### 2.1 route 层

```python
# collect/interface/dto/request/collect.py:18
params: dict = Field(default_factory=dict)

# collect/interface/route/tech/__init__.py:63-70
@router.post("/daily_kline", ...)
async def daily_trigger(body: CollectRequest, svc=Depends(get_daily_service)):
    return R.ok((await _run(svc, body)).model_dump())
```

**问题**：

| # | 问题 | 影响 |
|---|---|---|
| R1 | `params: dict` 在 OpenAPI 里渲染成 `object` | 前端/接口文档都无法感知「必须传 start_date/end_date」 |
| R2 | 校验下沉到 service（`_validate_params`），失败手动 `raise HTTPException(400)` | 绕过 FastAPI/Pydantic 的 422 机制；错误信息格式与其它 endpoint 不一致 |
| R3 | `_run(svc, body)` 是 5 个 endpoint 共享的私有 helper，内部 `isinstance(result, dict)` 分支处理 CollectResult 兼容 | 协议混杂（v4 之后 `collect()` 已全部返回 dict，兼容分支实际已失效） |

### 2.2 application 层

**service（`daily_service.py`，427 行）**：

| 方法 | 行号 | 现状 | 问题 |
|---|---|---|---|
| `collect()` | 91-96 | `_validate_params` → `create_task(run_collect)` | 依赖 dict 形状 |
| `_validate_params()` | 113-169 | 手写 57 行校验（必填 / ISO / 起止 / 跨度 / 白名单） | 本该 Pydantic |
| `run_collect()` | 171-296 | 日志全生命周期 + 编排 | 合规 |
| `_parse_date_range()` | 302-310 | 再把 ISO 字符串解析成 `date` | 与 `_validate_params` 重复 |
| `_list_all_symbols_via_session()` | 314-322 | `select(StockBasicDB)` | ❌ P3 |
| `_collect_one()` | 324-352 | 限流 + 3 次重试 + rollback | 合规 |
| `_save()` | 355-371 | `pg_insert(TechKlineDailyDB)` + 每只 commit | ❌ P1 |
| `get()` | 374-407 | `select(TechKlineDailyDB)` | ❌ P2 |

**`_save()` 的两处注释是关键信息**：

```python
# ORM 模型实际列名是 "date"，不是 "trade_date"。
# 只能更新 rows 中实际存在的列，否则 UPSERT 会把数据库里
# name / change_pct 覆盖成 NULL。
```

第二句说明这是**权宜之计**：为了不把 `name`/`change_pct` 写成 NULL，干脆不更新这两列。副作用是 `tech_daily.name` 永远拿不到 daily 采集来的名字。而 `kline_repo.KlineRepository.save_klines()` 恰恰**会**更新这两列（`kline_repo.py:39-47`）——两套 upsert 语义并存（虽然后者是死代码，但 `market/KlineRepoImpl.save_batch()` 也是同样的「直接覆盖」语义）。

**正确解法是 `COALESCE`**：`set_={"name": func.coalesce(stmt.excluded.name, TechKlineDailyDB.name)}`，既写入新值又不会被 NULL 覆盖。§4.4 展开。

**port/params.py（死代码）**：

```python
# collect/application/port/params.py —— 6 个模型，全仓零 import
class EmptyParams / TradeDateParams / SymbolParams / IndexCodeParams /
      StockBasicParams / MinuteKlineParams
```

只有 `application/port/__init__.py` 自己 re-export。这说明「Params 契约化」是原始设计意图，只是从未落地。本轮是它的首次落地。

### 2.3 fetcher 层

```python
# collect/infrastructure/fetcher/base.py:47-49
@abstractmethod
async def fetch(self, **params) -> list[BaseModel]:
    """调 SDK 拿数据，返回 list[BO]
    入参直接 kwargs，service 负责类型校验和默认值填充。
    """
```

| # | 问题 |
|---|---|
| F1 | `**params` 无类型：调用方写 `fetch(symbl=...)` 拼错 key 编译期无感知，运行到 fetcher 内部才炸 |
| F2 | 各 fetcher 自建局部 Params 模型（`MoneyflowParams` / `DailyBasicParams` / `TopListParams` 等 12 个），彼此不共享、也不与 `port/params.py` 打通 |
| F3 | `DailyTushareFetcher._resolve_name()` 内部回查 Tushare（X4） |
| F4 | `BaseFetcher` 注释说「service 负责类型校验和默认值填充」→ 校验职责事实上漏到了 fetcher 边界之外 |

**出口方向是对的**：`fetch()` 返回 `list[KlineBO]`，parser 已把 Tushare 的 `YYYYMMDD` / `vol(手)` / `amount(千元)` 全部归一化。**入口方向是缺的**，本轮补齐。

### 2.4 repo 层

| 文件 | 类 | 状态 |
|---|---|---|
| `collect/.../repositories/kline_repo.py` | `KlineRepository` | ❌ **死代码**：`get_kline_repository()` 定义在 `di/repo.py:15`，但无任何 `Depends` 调用；全文件 12 个方法无一被调用 |
| `collect/domain/entitys/kline/repository.py` | `KlineRepository(Protocol)` | ❌ **死代码**：签名 `save_klines(klines)` 不带 session，与实现的 `(klines, session)` 不一致，无人实现它 |
| `market/.../repositories/kline_repository.py` | `KlineRepoImpl` | ⚠️ 部分存活：`find_by_symbol` / `count_by_symbol` / `delete_*` 被 `StockInfoService` 调用；`save` / `save_batch` 无调用方，且 `save_batch` 的约束名已过期（X2） |

**即 `tech_daily` 表存在 3 份仓储实现**，其中活跃的写路径反而是 service 里的内联 SQL。

`KlineRepository` 已具备的能力（只是没人调）：

```
save_klines / find / find_by_symbol / count_by_symbol / delete_one /
delete_by_symbol / get_coverage / list_symbol_dates / list_symbols / delete
```

`_list_all_symbols_via_session` 想做的事，`list_symbols(session, list_status="L")`（`kline_repo.py:133-142`）已经实现了，**逐行等价**。

### 2.5 DI 层

```python
# collect/infrastructure/di/collect_service.py:58-71
def get_daily_service(session: AsyncSession = Depends(get_raw_db)):
    return DailyService(log_service=CollectLogService(), session=session)
```

与其它 27 个工厂的**标准模板不一致**：其它都是 `Depends(get_xxx_repository)` 注入 repo，`daily` / `minute` / `stock_basic` / `concept_minute` 三个没有 repo 注入（后两个是合理例外，`daily` 不是）。

同时注意：`session` 由 DI 注入但**只给 `get()` 用**；`run_collect()` 自己 `get_raw_db_context()` 开 session。原因见 §4.2.4。

### 2.6 问题清单汇总

| # | 层 | 问题 | 位置 | 严重度 |
|---|---|---|---|---|
| P1 | service | inline `pg_insert` | `daily_service.py:355-371` | 🔴 |
| P2 | service | inline `select`（get） | `daily_service.py:374-407` | 🔴 |
| P3 | service | inline `select(StockBasicDB)` | `daily_service.py:314-322` | 🟡 |
| P4 | 全链路 | `params: dict` 无契约 | `dto/request/collect.py:18` | 🔴 |
| P5 | fetcher | `fetch(**params)` 无类型；`port/params.py` 死代码 | `fetcher/base.py:47` | 🟡 |
| P6 | repo | `KlineRepository` 死代码 | `repositories/kline_repo.py` | 🟡 |
| P7 | repo | 3 份 tech_daily 仓储并存 | — | 🟡 |
| P8 | repo | upsert 语义两套（覆盖 vs 跳过） | `daily_service.py:355-371` vs `kline_repo.py:39-47` | 🔴 |
| P9 | DI | `get_daily_service` 缺 repo 注入 | `di/collect_service.py:58` | 🟡 |
| P10 | service | 手写 57 行参数校验 | `daily_service.py:113-169` | 🟡 |
| P11 | service | `_parse_date_range` 与 `_validate_params` 重复 | `daily_service.py:302-310` | 🟢 |
| P12 | fetcher | 内部回查 Tushare 取 name | `DailyTushareFetcher.py:60-85` | 🟡 |

---

## 三、目标架构

### 3.1 分层职责

| 层 | 职责 | 允许 import | 禁止 |
|---|---|---|---|
| **interface** | HTTP 解析、DTO ↔ Params 转换、异常 → HTTP | application 的 Params、domain 的异常 | ORM、repo 实现、SQL |
| **application** | 编排：校验 → 限流 → 调 fetcher → 调 repo → 日志 | 同层 BO / port、domain 的 Protocol 与异常 | **ORM 模型、pg_insert、select、具体 repo 实现** |
| **domain** | 实体、值对象、Repository Protocol、领域异常 | shared | 任何 infrastructure |
| **infrastructure** | ORM / repo 实现 / fetcher / SDK client / session | application 的 BO·Params、domain | — |

> 关键红线：**application 层不得出现任何 ORM 类名、`pg_insert`、`select`、`execute`**。

### 3.2 目录结构变更

```
contexts/collect/
├── interface/
│   ├── dto/request/
│   │   ├── collect.py               # 改：CollectRequest 保留（其它 4 endpoint 过渡期继续用）
│   │   └── tech.py                  # 新增：DailyCollectRequest / MinuteQueryRequest
│   └── route/tech/__init__.py       # 改：daily 用专属 DTO，_run 简化
├── application/
│   ├── port/
│   │   ├── params.py                # 改：新增 DailyCollectParams / DailyKlineFetchParams
│   │   ├── session.py               # 新增：SessionProvider Protocol（见 §4.2.4）
│   │   └── fetcher.py               # 新增：FetcherPort Protocol（可选，见 D9）
│   └── service/tech/daily_service.py  # 改：签名类型化、去 SQL、去手写校验
├── infrastructure/
│   ├── fetcher/
│   │   ├── base.py                  # 改：BaseFetcher[ParamsT, BOT] 泛型
│   │   └── tech/DailyTushareFetcher.py  # 改：fetch(params)、name 来源下沉
│   ├── persistence/repositories/
│   │   └── kline_repo.py            # 改：收 BO、upsert COALESCE、加 list_names
│   └── di/
│       ├── collect_service.py       # 改：get_daily_service 注入 repo + session provider
│       └── repo.py                  # 改：get_kline_repository 真正被用上
└── domain/entitys/kline/repository.py  # 改：Protocol 签名与实现对齐
```

### 3.3 数据契约流向

```
DailyCollectRequest (interface, 前端可见, OpenAPI schema)
        │  字段一一对应
        ▼
DailyCollectParams (application, 业务语义 + 业务校验)
        │  展开为 N 个
        ▼
DailyKlineFetchParams (application, 单只股票 + 时间范围)
        │
        ▼
DailyTushareFetcher.fetch() → list[KlineBO] (application BO)
        │
        ▼
KlineRepository.save_klines(bos, session) → row dict → ORM
```

---

## 四、详细改造方案（逐文件）

### 4.1 interface 层

#### 4.1.1 新增 `interface/dto/request/tech.py`

```python
"""tech facet 专属请求 DTO（参数形状明确的 service 用专属 DTO）

背景：CollectRequest.params 是 dict，OpenAPI 里渲染为 object，
      前端拿不到「必填 start_date/end_date」的契约。
      本文件为 daily_kline（及后续迁移的 service）提供具体 schema。

过渡期：其余 service 继续用通用 CollectRequest.params 信封。
       迁移完成后 CollectRequest 整体删除。
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class DailyCollectRequest(BaseModel):
    """POST /api/v1/collect/tech/daily_kline 请求体

    - 时间范围必传（后端 Params 层再校验跨度）
    - symbols 不接受前端指定：全市场采集固定从 stock_basic 取
      （保留字段仅为向前兼容，命中即 422，见 DailyCollectParams）
    """
    model_config = {"extra": "forbid"}

    start_date: date = Field(..., description="起始日期 YYYY-MM-DD")
    end_date: date = Field(..., description="结束日期 YYYY-MM-DD")


class DailyQueryRequest(BaseModel):
    """GET /api/v1/collect/query/daily_kline 查询参数（实时查 DB）"""
    model_config = {"extra": "forbid"}

    symbol: str = Field("", description="股票代码，留空查全部")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    limit: int = Field(30, ge=1, le=5000)
```

> **为什么是 `extra="forbid"` 而不是静默丢弃**：当前 `_validate_params` 的「白名单返回」逻辑会静默吞掉前端多传的字段，前端拼错字段名时**没有任何反馈**（静默生效或静默丢弃）。`forbid` 让字段名拼错直接 422，是把契约显式化的关键一环。
>
> `symbols` 字段的处理见 §5 决策 D4。

#### 4.1.2 改造 `interface/route/tech/__init__.py`

```python
# ── daily_kline（已迁移：专属 DTO）──────────────────────
@router.post(
    "/daily_kline", summary="日 K 线采集（全市场，时间范围必传）",
    response_model=ApiResponse[CollectResponse],
)
async def daily_trigger(
    body: DailyCollectRequest,
    svc: DailyService = Depends(get_daily_service),
):
    """入参由 FastAPI + Pydantic 自动校验，缺失/格式错直接 422"""
    try:
        params = DailyCollectParams.from_request(body)
        result = await svc.collect(params)
    except InvalidParams as e:
        # 仅业务规则错误（跨度超限等）落到 400；字段级错误已由 422 处理
        raise HTTPException(status_code=400, detail=str(e)) from e
    return R.ok(CollectResponse(status=result["status"], log_id=None,
                                message="采集任务已派发，前端请按 service_name 查日志").model_dump())


# ── 其余 4 个（过渡期：仍用通用 CollectRequest 信封）─────
@router.post("/adj_factor", ...)
async def adj_factor_trigger(body: CollectRequest, svc=Depends(get_adj_factor_service)):
    return R.ok((await _run(svc, body)).model_dump())
```

**`_run()` 的处理**：`v4` 之后所有 `collect()` 都返回 dict，`CollectResult` 兼容分支（`_run` 里的 `isinstance(result, dict)` else 分支）已无触发路径。建议在 `daily` 迁移时**删掉该分支**，并把 `_run` 收敛为「校验 + 派发 + 包响应」。等 4 个 endpoint 都迁移完，`_run` 与 `CollectRequest` 一并删除。

#### 4.1.3 response DTO 不变

`CollectResponse` 已有 `log_id` / `status` / `message`，v4 协议下 `log_id` 恒为 `None`（不暴露）。本轮不删字段——前端 `CollectManage.vue` 可能在读，等前端同步批次再清。

---

### 4.2 application 层

#### 4.2.1 `port/params.py` 新增两个模型

```python
# ── 追加到 collect/application/port/params.py ──────────────

class DailyCollectParams(BaseModel):
    """daily_kline 采集入参（application 层契约）

    校验规则：
        - start_date / end_date 必填（Pydantic 层，缺失 → 422）
        - start_date <= end_date
        - 跨度 <= max_span_days
        - 白名单：symbols / mode 等字段一律拒绝（extra="forbid"）

    日志用 JSONB 存 params，所以 model_dump(mode="json") 出来的
    date 是 ISO 字符串，不会序列化失败。
    """
    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    max_span_days: int = Field(1095, ge=1, le=1095, description="跨度上限，仅内部使用")

    @model_validator(mode="after")
    def _check_range(self) -> "DailyCollectParams":
        if self.start_date > self.end_date:
            raise ValueError(f"start_date（{self.start_date}）不能晚于 end_date（{self.end_date}）")
        span = (self.end_date - self.start_date).days
        if span > self.max_span_days:
            raise ValueError(f"时间跨度过大：{span} 天，超过上限 {self.max_span_days} 天")
        return self

    def to_log_dict(self) -> dict:
        """写 collect_logs.params（JSONB）用"""
        return self.model_dump(mode="json", exclude={"max_span_days"})

    @classmethod
    def from_request(cls, req) -> "DailyCollectParams":
        """Request DTO → Params（唯一的转换点）"""
        return cls(start_date=req.start_date, end_date=req.end_date)


class DailyKlineFetchParams(BaseModel):
    """单只股票日 K 拉取入参（service → fetcher 契约）"""
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(..., min_length=6, max_length=6)
    start_date: date
    end_date: date

    @field_validator("symbol")
    @classmethod
    def _zfill(cls, v: str) -> str:
        return v.zfill(6)
```

> `max_span_days` 放字段而不是 ServiceMeta，是为了让它进入校验链路（否则 service 又要手写常量比较）。`to_log_dict()` 排除它，避免污染日志行。**如果评审觉得别扭，可改为 `PrivateAttr` / 常量 + `model_validator` 内比较**——见 §5 决策 D3。

#### 4.2.2 `DailyService` 目标骨架

```python
class DailyService:
    META = ServiceMeta(
        name="daily_kline", facet="tech", label="日 K 线",
        description="Tushare pro.daily 日 K 线",
        kind=ServiceKind.INCREMENTAL,
        rate_limit=("tushare", 200, 60),
        concurrency=1,   # 见 §4.2.4，本轮保持 1
    )

    def __init__(
        self,
        log_service: "CollectLogService",
        session: AsyncSession | None = None,          # 仅 get() 实时查询用
        session_provider: "SessionProvider" | None = None,  # run_collect 用
        fetcher: DailyTushareFetcher | None = None,
        repo: KlineRepository | None = None,
    ) -> None:
        self._log_service = log_service
        self._session = session
        self._session_provider = session_provider or get_raw_db_context
        self._fetcher = fetcher or DailyTushareFetcher()
        self._repo = repo or KlineRepository()

    # ── 入口 A：HTTP 触发 ───────────────────────────────
    async def collect(self, params: DailyCollectParams) -> dict:
        """零状态：只派发。校验已由 Pydantic 完成，这里不重复。"""
        asyncio.create_task(self.run_collect(params))
        return {"status": "pending"}

    # ── 入口 B：后台执行 ───────────────────────────────
    async def run_collect(self, params: DailyCollectParams) -> None:
        log_id = await self._log_service.create_pending(
            service_name=self.META.name, facet=self.META.facet,
            kind=self.META.kind.value, params=params.to_log_dict(),
            trigger_source="manual",
        )
        async with self._session_provider() as session:
            try:
                symbols = await self._repo.list_symbols(
                    session, list_status="L",
                )                                   # ✅ P3：下沉 repo
                if not symbols:
                    await self._log_service.mark_failed(...)
                    return
                total = len(symbols)
                await self._log_service.mark_running(self.META.name, log_id)

                # name 映射一次性取回，避免 fetcher 逐只回查（✅ P12）
                names = await self._repo.list_names(session, symbols)

                saved_total = fail_total = 0
                for result in self._as_completed(...):
                    ...
                await self._log_service.mark_finished(...)
            except Exception as e:
                ...mark_failed...

    async def _collect_one(
        self, symbol: str, params: DailyCollectParams,
        name: str, session: AsyncSession,
    ) -> int:
        await check(self.META.rate_limit)
        for attempt in range(3):
            try:
                fetch_params = DailyKlineFetchParams(
                    symbol=symbol, start_date=params.start_date, end_date=params.end_date,
                )
                bos: list[KlineBO] = await self._fetcher.fetch(fetch_params)
                if not bos:
                    return 0
                for b in bos:
                    b.name = name or b.name          # ✅ P12：名字来自 DB
                return await self._repo.save_klines(bos, session)   # ✅ P1
            except Exception:
                if attempt < 2:
                    await session.rollback()
                    await asyncio.sleep(1)
                else:
                    raise
        return 0

    # ── 实时查询 ──────────────────────────────────────
    async def get(
        self, symbol: str = "", start_date: str | None = None,
        end_date: str | None = None, limit: int = 30,
    ) -> list[dict]:
        if self._session is None:
            logger.warning("daily_kline.get() 缺少 session，返回空")
            return []
        klines = await self._repo.find_by_symbol(   # ✅ P2：下沉 repo
            symbol=symbol, start_date=start_date, end_date=end_date,
            limit=limit, order_desc=True, session=self._session,
        )
        return [k.to_dict() for k in klines]
```

#### 4.2.3 手写校验逐条对照

`_validate_params()`（`daily_service.py:113-169`，57 行）删除后，每条规则的去处：

| 现有校验 | 行号 | 去处 |
|---|---|---|
| `start_date` / `end_date` 必填 | 134-142 | `DailyCollectRequest` 必填字段 → **422**（原 400） |
| ISO 格式（`date.fromisoformat`） | 144-152 | `DailyCollectRequest: date` 类型 → **422** |
| `start <= end` | 154-156 | `DailyCollectParams._check_range` |
| 跨度 <= `MAX_SPAN_DAYS` | 158-162 | `DailyCollectParams._check_range` |
| 白名单丢弃多余字段 | 164-169 | `extra="forbid"` → **422**（原静默丢弃） |
| 返回 ISO 字符串给 JSONB | 168 | `DailyCollectParams.to_log_dict()`（`mode="json"`） |
| `_parse_date_range()` 二次解析 | 302-310 | **删除**，Params 里已经是 `date` 对象 |

**净减少 ~70 行**。

#### 4.2.4 session 管理（本轮保留自开，但要给出理由）

`run_collect()` 通过 `asyncio.create_task` 在**请求生命周期之外**执行。FastAPI 的 `Depends(get_raw_db)` 产出的 session 绑定 request，请求结束即关闭——后台任务持有它必然踩 `InterfaceError: session is closed`。

所以 **`run_collect()` 必须自开 session**，这一点当前代码是对的。问题只在于它直接 `from shared.infrastructure.di.db_session import get_raw_db_context`（越层 + 循环依赖隐患）。

方案：在 `application/port/session.py` 定义 Protocol，infrastructure 提供实现，DI 注入：

```python
# application/port/session.py
from typing import Protocol
from contextlib import AbstractAsyncContextManager
from sqlalchemy.ext.asyncio import AsyncSession


class SessionProvider(Protocol):
    """提供 raw_data 库的短生命周期 session 上下文

    ★ 背景：run_collect 由 asyncio.create_task 派发，脱离 FastAPI
      请求生命周期，不能持有 Depends 注入的 session（请求结束即关闭）。
      故后台任务必须自开 session —— 但不应由 service 直接 import
      infrastructure，故抽象成 Protocol 由 DI 注入。
    """
    def __call__(self) -> AbstractAsyncContextManager[AsyncSession]: ...
```

```python
# di/collect_service.py
def get_daily_service(
    repo=Depends(get_kline_repository),
    session: AsyncSession = Depends(get_raw_db),      # 仅 get() 实时查询
):
    return DailyService(
        log_service=CollectLogService(),
        session=session,
        session_provider=get_raw_db_context,          # run_collect 用
        repo=repo,
    )
```

**`concurrency=1` 的注释也要更正**：现在的理由写的是「AsyncSession 非并发安全」，但真正原因是 §4.2.4 的 request-scoped session + 每只 commit 的组合。若后续改为「每只一个独立 session」（SessionProvider 天然支持），`concurrency` 可放开到 3–5，5000 只股票的采集时间会显著下降。**本轮不动**，登记为后续优化项（§10）。

---

### 4.3 fetcher 层

#### 4.3.1 `BaseFetcher` 泛型化

```python
# collect/infrastructure/fetcher/base.py
from abc import ABC, abstractmethod
from typing import ClassVar, Generic, TypeVar
from pydantic import BaseModel

ParamsT = TypeVar("ParamsT", bound=BaseModel)
BOT = TypeVar("BOT", bound=BaseModel)


class BaseFetcher(ABC, Generic[ParamsT, BOT]):
    """Fetcher 抽象基类

    唯一职责：Params → 调 SDK → 返回 list[BO]
    不限流、不并发、不缓存、不入库、不做业务校验
    （入参校验在 Params 模型里已经做完，这里只做 SDK 格式转换）
    """
    source: ClassVar[str] = ""
    fetcher_type: ClassVar[str] = ""
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""

    #: 本 fetcher 接受的 Params 类型（供 DI / 测试断言用）
    params_model: ClassVar[type[BaseModel]]

    @abstractmethod
    async def fetch(self, params: ParamsT) -> list[BOT]:
        """调 SDK 拿数据

        ★ 显式接收一个 Params 对象，不再是 **kwargs：
          - 调用方拼错字段 → 构造 Params 时就报错
          - SDK 特有格式（ts_code / YYYYMMDD）在本方法内部转换，不外泄
        """
```

**改造影响面**：`BaseFetcher` 有 26 个子类。一次性全改风险大，建议：
- 本轮只改 `BaseFetcher` 的签名 + `DailyTushareFetcher`
- 其余 25 个子类改为 `class XxxFetcher(BaseFetcher[XxxParams, XxxBO])` 标注继承，但保留 `fetch(self, **params)` 实现（加 `# TODO(P3-N): 迁移到 fetch(params)`）
- 迁移顺序见 §10

> 另一种更保守的做法：本轮**不改** `BaseFetcher`，只给 `DailyTushareFetcher.fetch` 加 `params: DailyKlineFetchParams` 显式入参，等其它 25 个迁完再抽泛型基类。**见 §5 决策 D6**，本文推荐前者（早统一），但后者风险更低。

#### 4.3.2 `DailyTushareFetcher` 改造

```python
class DailyTushareFetcher(BaseFetcher[DailyKlineFetchParams, KlineBO]):
    fetcher_type = "daily_kline_tushare"
    source = "tushare"
    label = "日 K 线（Tushare）"
    description = "Tushare pro.daily 接口"
    params_model = DailyKlineFetchParams

    def __init__(self) -> None:
        self._c = get_tushare_client()
        self._parser = TushareKlineParser()

    async def fetch(self, params: DailyKlineFetchParams) -> list[KlineBO]:
        """SDK 格式转换全部封在本方法内，不外泄"""
        ts_code = symbol_to_ts_code(params.symbol)
        buf_start = params.start_date - timedelta(days=START_BUFFER_DAYS)
        df = await self._c.query(
            "daily",
            ts_code=ts_code,
            start_date=buf_start.strftime("%Y%m%d"),   # ISO → YYYYMMDD
            end_date=params.end_date.strftime("%Y%m%d"),
        )
        if df.empty:
            return []
        df = df.sort_values("trade_date").reset_index(drop=True)
        return self._parser.parse(df, params.symbol)
```

**变化**：
- `_resolve_name()` 与 `self._names` 缓存**整体删除**（P12 / X4）：名字由 service 从 DB 取后回填 `b.name`
- `START_BUFFER_DAYS` 多取 2 天的逻辑保留（覆盖周末/节假日首日缺口），但**当前它取回来的 buffer 数据会被原样入库**——多写 2 天的 K 线到 DB。这是一个待确认点，见 §5 决策 D7
- `fetch` 出参类型标注 `list[KlineBO]` 而非 `list[BaseModel]`

#### 4.3.3 name 的来源迁移

| | 现状 | 目标 |
|---|---|---|
| 来源 | Tushare `stock_basic` 全量 API（fetcher 内部，懒加载一次） | DB `fundamental_stock_basic.name` |
| 调用次数 | 首次 1 次全量 API；异常后退化为每只 1 次 | 0 次 API，1 次 DB 查询 |
| 一致性 | 与 DB 里的 stock_basic 可能不同步 | 与 DB 一致 |
| 兜底 | 拉不到 name 时 BO.name 为空 | 同 |

```python
# repo 新增方法
async def list_names(self, session: AsyncSession, symbols: Iterable[str]) -> dict[str, str]:
    """批量取股票名称（避免 N+1）"""
    rows = (await session.execute(
        select(StockBasicDB.symbol, StockBasicDB.name)
        .where(StockBasicDB.symbol.in_(list(symbols)))
    )).all()
    return {str(r[0]).zfill(6): (r[1] or "") for r in rows}
```

> **注意**：`list_names` 与 `list_symbols` 都查 `StockBasicDB`，语义上属于「股票基本信息」而非「日 K 线」。**放 `kline_repo` 是权宜之计**。正解是加到 `StockInfoRepository`（`repositories/stock_info_repo.py` 已有该表访问能力）。见 §5 决策 D5。

---

### 4.4 repo 层

#### 4.4.1 `KlineRepository` 目标接口

```python
class KlineRepository:
    """日 K 线仓储（tech_daily 表唯一写入口）

    所有方法接受 session 入参（由 service 注入的 SessionProvider 提供）。
    """

    # ── 写 ──
    async def save_klines(self, bos: list[KlineBO], session: AsyncSession) -> int:
        """批量 upsert。upsert 语义见 §4.4.2"""

    # ── 读 ──
    async def find(self, symbol: str, start: date | None, end: date | None,
                   session: AsyncSession) -> list[Kline]: ...
    async def find_by_symbol(self, symbol: str, session: AsyncSession,
                             start_date=None, end_date=None,
                             limit: int = 1000, order_desc: bool = False) -> list[Kline]: ...
    async def count_by_symbol(self, symbol: str, session: AsyncSession) -> int: ...
    async def get_coverage(self, symbols, session) -> dict[str, tuple[date, date]]: ...

    # ── 删 ──
    async def delete(self, symbol: str, session) -> int: ...
    async def delete_one(self, symbol: str, trade_date: date, session) -> int: ...
    async def delete_by_symbol(self, symbol: str, session) -> int: ...

    # ── 辅助（供 daily 采集用）──
    async def list_symbols(self, session, list_status: str = "L") -> list[str]: ...
    async def list_names(self, session, symbols) -> dict[str, str]: ...
```

**签名调整 2 处**：

| 现状 | 目标 | 原因 |
|---|---|---|
| `save_klines(klines: list[Kline], session)` | `save_klines(bos: list[KlineBO], session)` | 实际调用方（fetcher）返回的是 `KlineBO`，现有标注 `list[Kline]` 是**错的**。统一按 D4 决策「BO → row 转换放 repo」 |
| `delete_by_symbol()` 调 `self.delete()`（方法不存在） | 删除该别名，或指向 `delete()` | 潜在 `AttributeError` |

#### 4.4.2 upsert 语义统一（本方案的技术核心）

**当前两套语义**：

| 实现 | `set_` 列 | 问题 |
|---|---|---|
| `daily_service._save()` | open/high/low/close/volume/amount | `name` / `change_pct` **永不更新**（权宜之计） |
| `kline_repo.save_klines()` | name/open/.../change_pct | `name=None` 会**覆盖**已有值成 NULL |
| `market/KlineRepoImpl.save_batch()` | 同上 | 同上；且约束名过期（X2） |

**目标语义**（第三种，正确解法）：

```python
async def save_klines(self, bos: list[KlineBO], session: AsyncSession) -> int:
    if not bos:
        return 0
    rows = [self._to_row(b) for b in bos]
    stmt = pg_insert(TechKlineDailyDB).values(rows)

    # ★ 关键：COALESCE 让「有新值就更新，没新值就保留旧值」
    #   既解决 _save 的「name 永不更新」，也解决 save_klines 的「NULL 覆盖」
    excluded = stmt.excluded
    updatable = ["open", "high", "low", "close", "volume", "amount"]
    set_ = {c: excluded[c] for c in updatable}
    set_["name"] = func.coalesce(excluded.name, TechKlineDailyDB.name)
    set_["change_pct"] = func.coalesce(excluded.change_pct, TechKlineDailyDB.change_pct)

    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "date"],   # 用 index_elements，不用 constraint 名
        set_=set_,
    )
    r = await session.execute(stmt)
    return r.rowcount or len(rows)
```

**三个技术要点**：

1. **用 `index_elements=["symbol", "date"]` 而不是 `constraint="..."`**——约束名会随表重命名漂移（X2 就是活例子）。ORM 模型里已有 `UniqueConstraint("symbol","date")`，`index_elements` 稳定。
2. **`COALESCE` 一劳永逸解决 NULL 覆盖**：`_save` 的注释担心的「覆盖成 NULL」问题，被 `coalesce` 完全消除，所以 `name` 可以放心更新。
3. **`id` / `created_at` / `updated_at` 不进 `set_`**（由 `TimestampMixin` / 序列管理）。

#### 4.4.3 与 market `KlineRepoImpl` 的关系

现状：`tech_daily` 有 3 份仓储（2 份死代码 + 1 份部分存活）。目标状态：

| 类 | 处置 |
|---|---|
| `collect/.../kline_repo.KlineRepository` | ✅ **唯一活跃写入口**（本轮启用） |
| `market/.../kline_repository.KlineRepoImpl` | ⚠️ 读方法（`find_by_symbol` / `count_by_symbol` / `delete_*`）被 `StockInfoService` 依赖，**保留**；写方法（`save` / `save_batch`）删除（顺带消灭 X2） |
| `collect/domain/entitys/kline/repository.py` Protocol | 🔧 签名对齐实现（加 `session` 参数），或删除（见 §5 决策 D8） |

> **不合并两个类的原因**：`KlineRepoImpl` 的接口签名是 `StockCode`/`TradeDate`（VO），`KlineRepository` 是 `str`/`date`。强行合并要动 `StockInfoService` 的 7 处调用点，超出本批范围。**登记为后续收敛项**（§10）。

#### 4.4.4 `_to_row` 适配 BO

```python
@staticmethod
def _to_row(b: KlineBO) -> dict:
    """KlineBO → ORM row

    ★ trade_date（BO）→ date（ORM 列名），这是最容易写错的一处：
      ORM 模型的列名是 "date"，不是 "trade_date"。
    """
    return {
        "symbol": str(b.symbol).zfill(6),
        "name": b.name or None,          # 空串 → None，配合 COALESCE 保留旧值
        "date": b.trade_date,
        "open": float(b.open),
        "high": float(b.high),
        "low": float(b.low),
        "close": float(b.close),
        "volume": int(b.volume),
        "amount": float(b.amount or 0.0),
        "change_pct": float(b.change_pct) if b.change_pct is not None else None,
    }
```

---

### 4.5 DI 层

```python
# collect/infrastructure/di/collect_service.py
def get_daily_service(
    repo=Depends(get_kline_repository),
    session: AsyncSession = Depends(get_raw_db),        # 仅 get()
):
    """日 K 线 service

    - repo     : tech_daily 唯一写入口（run_collect + get 复用）
    - session  : 仅 get() 实时查询（request 生命周期内有效）
    - run_collect 的 session 由 service 内部 SessionProvider 自开
      （asyncio.create_task 脱离 request 生命周期，见 port/session.py）
    """
    from contexts.collect.application.service.tech.daily_service import DailyService
    from shared.infrastructure.di.db_session import get_raw_db_context
    return DailyService(
        log_service=CollectLogService(),
        session=session,
        session_provider=get_raw_db_context,
        repo=repo,
    )
```

`get_kline_repository()` 已存在于 `di/repo.py:15`，本轮**首次被真正使用**（P6）。

---

## 五、待拍板决策项

| # | 决策 | 选项 | 建议 | 影响 |
|---|---|---|---|---|
| **D1** | `CollectRequest.params: dict` 信封去留 | **A** 保留信封，daily 用专属 DTO（渐进迁移）<br>**B** 一次性全部迁到专属 DTO，删掉信封 | **A** | A 改动可控；B 要改 28 个 endpoint + 前端 |
| **D2** | 未知字段策略 | **A** `extra="forbid"` → 422<br>**B** 静默丢弃（现状） | **A** | A 会让之前拼错字段名也不报错的调用方暴露出来（可能是好事） |
| **D3** | 跨度上限放哪 | **A** `DailyCollectParams.max_span_days` 字段<br>**B** 保持 `DailyService.MAX_SPAN_DAYS` 常量，在 model_validator 外比较 | **A** | A 会让该字段进入 Params（需 `to_log_dict` 排除）；B 更保守 |
| **D4** | `symbols` 前端可控性 | **A** 彻底不支持（`forbid` 命中即 422）<br>**B** 允许传 symbols，为空则全市场 | **A** | 当前 `_validate_params` 静默丢弃 symbols；A 把隐式行为显式化。**若前端将来需要「采集指定股票」则要选 B** |
| **D5** | `list_symbols` / `list_names` 放哪 | **A** 放 `KlineRepository`（权宜，语义错位）<br>**B** 放 `StockInfoRepository`，daily 注入两个 repo | **B** | B 语义正确，DI 多一个依赖 |
| **D6** | `BaseFetcher` 泛型化范围 | **A** 本轮改基类签名 + 26 个子类标注继承（写方法暂不改）<br>**B** 本轮不动基类，只改 `DailyTushareFetcher` | **A** | A 早统一但一次动 26 个文件；B 风险低但模板不完整 |
| **D7** | `START_BUFFER_DAYS=2` 多取的数据 | **A** 原样入库（现状）<br>**B** 只保留 `>= start_date` 的行 | **B** | A 会往 DB 多写 2 天/只/次的数据；B 语义更干净。**当前库里可能已有冗余数据，需确认是否清理** |
| **D8** | `collect/domain/entitys/kline/repository.py` Protocol | **A** 签名对齐并保留<br>**B** 删除（它与 market 的 Protocol 重复且无人实现） | **A** | DDD 规范要求 repository 接口在 domain；但保留一份没人实现的 Protocol 也是负担 |
| **D9** | 是否抽 `application/port/fetcher.py` Protocol | **A** 只靠 `BaseFetcher` 泛型<br>**B** application 定义 `FetcherPort`，fetcher 实现它 | **A** | A 简单；B 更严格 DDD（application 不 import infrastructure）。**注意现状：所有 service 都直接 import 具体 Fetcher 类，是全仓性偏差** |

---

## 六、改造清单（文件级 checklist）

### interface（2 文件）

- [ ] 新增 `collect/interface/dto/request/tech.py` — `DailyCollectRequest` / `DailyQueryRequest`
- [ ] 改 `collect/interface/route/tech/__init__.py` — daily 用专属 DTO；`_run` 删 `CollectResult` 兼容分支

### application（3 文件）

- [ ] 改 `collect/application/port/params.py` — 追加 `DailyCollectParams` / `DailyKlineFetchParams`，补 `__all__`
- [ ] 新增 `collect/application/port/session.py` — `SessionProvider` Protocol
- [ ] 改 `collect/application/service/tech/daily_service.py` — 见 §4.2.2（预计 427 → ~300 行）

### infrastructure/fetcher（2 文件 + 25 标注）

- [ ] 改 `collect/infrastructure/fetcher/base.py` — 泛型化
- [ ] 改 `collect/infrastructure/fetcher/tech/DailyTushareFetcher.py` — `fetch(params)`、删 `_resolve_name`
- [ ] 25 个其它 fetcher — 加泛型标注 + `# TODO(P3-N)`（若 D6=A）

### infrastructure/repo（3 文件）

- [ ] 改 `collect/infrastructure/persistence/repositories/kline_repo.py` — `list[KlineBO]`、COALESCE upsert、加 `list_names`、修 `delete_by_symbol`
- [ ] 改 `collect/infrastructure/persistence/repositories/__init__.py` — 无需改（导出已有）
- [ ] 改 `collect/domain/entitys/kline/repository.py` — 签名对齐（D8=A 时）
- [ ] 改 `market/.../repositories/kline_repository.py` — 删 `save` / `save_batch`（顺带消灭 X2）

### infrastructure/DI（2 文件）

- [ ] 改 `collect/infrastructure/di/collect_service.py` — `get_daily_service` 注入 repo + session_provider
- [ ] 改 `collect/infrastructure/di/repo.py` — 视 D5 结果微调

### 前端（1 文件，延后）

- [ ] `frontend/src/views/collect-manage/` — 补 TS 类型定义（后端 DTO 定稿后）

---

## 七、实施时序与工作量

| Phase | 内容 | 文件数 | 估算 |
|---|---|---|---|
| **P0** | repo 统一 upsert 语义（COALESCE）+ `_save` 删除 + `_list_all_symbols` 下沉 | 1 | **0.5 天** |
| **P1** | Params 模型 + Request DTO + service 签名类型化 | 3 | **1 天** |
| **P2** | fetcher 泛型化 + `DailyTushareFetcher` 改造 + name 来源迁移 | 3 + 25 标注 | **1 天** |
| **P3** | DI 接线 + `SessionProvider` + `get()` 走 repo | 3 | **0.5 天** |
| **P4** | 验收：静态检查 + 端到端 + DB 抽查 | — | **0.5 天** |
| | **合计** | | **3.5 天** |

**建议合并为一个 PR**：P0–P3 互相依赖（repo 改完 service 才能删 `_save`；Params 改完 fetcher 才能改签名），拆开会产生中间态编译不过。P4 的验收脚本可独立提。

---

## 八、验收清单

### 8.1 静态验证（改造的核心目标）

```bash
# ① application 层零 SQL —— 期望：无输出
grep -rn "pg_insert\|\.execute(\|select(\|TechKlineDailyDB\|StockBasicDB" \
     backend/src/contexts/collect/application/service/

# ② application 层零 ORM import —— 期望：无输出
grep -rn "infrastructure.persistence.models" \
     backend/src/contexts/collect/application/

# ③ service 不再直连 infrastructure 的 db session —— 期望：无输出
grep -rn "db_session\|get_raw_db_context\|db_session_factory" \
     backend/src/contexts/collect/application/service/tech/daily_service.py

# ④ fetcher 无遗留 kwargs fetch —— 期望：仅 25 个待迁移的
grep -rn "async def fetch(self, \*\*params)" backend/src/contexts/collect/infrastructure/fetcher/
```

建议把 ①②③ 做成 `backend/scripts/verify_layering.py`（后续 24 个 service 迁移时反复用）。

### 8.2 契约验证

```bash
# OpenAPI 中 params 必须是具体 object（不是 {}）
curl -s localhost:8000/openapi.json | jq '.paths["/api/v1/collect/tech/daily_kline"].post'
# 期望：requestBody schema 引用 DailyCollectRequest，start_date/end_date 在 required 里

# 缺字段 → 422
curl -X POST localhost:8000/api/v1/collect/tech/daily_kline \
     -H 'Content-Type: application/json' -d '{"params":{}}'
# 期望：422 detail 指向 start_date/end_date missing

# 多传字段 → 422（extra=forbid）
curl -X POST localhost:8000/api/v1/collect/tech/daily_kline \
     -H 'Content-Type: application/json' \
     -d '{"start_date":"2026-10-01","end_date":"2026-10-21","symbols":["000001"]}'
# 期望：422 extra_forbidden

# 跨度超限 → 400
curl -X POST localhost:8000/api/v1/collect/tech/daily_kline \
     -H 'Content-Type: application/json' \
     -d '{"start_date":"2020-01-01","end_date":"2026-10-21"}'
# 期望：400 detail 含「时间跨度过大」
```

### 8.3 端到端回归

- [ ] `POST /api/v1/collect/tech/daily_kline` 触发小范围采集（改 `MAX_SPAN_DAYS` 或临时缩 symbols）
- [ ] `GET /api/v1/collect/logs?service_name=daily_kline` 确认 `success` 终态
- [ ] DB 抽查：

```sql
-- name 列现在应该能被 daily 采集写进去了（改造前是 NULL/旧值）
SELECT symbol, date, name, close, change_pct
FROM tech_daily WHERE name IS NULL LIMIT 10;

-- upsert 幂等：同一天跑两次，行数不变、值一致
SELECT count(*), count(DISTINCT (symbol, date)) FROM tech_daily;

-- change_pct 保留验证：先手工把某行 change_pct 设成 99，
-- 再重跑该股票的采集，确认 99 被真实值覆盖（而不是被 NULL 覆盖）
```

### 8.4 回归影响面

| 端点 | 影响 |
|---|---|
| `POST /api/v1/collect/tech/daily_kline` | 请求体结构变化（`{params:{}}` → `{start_date,end_date}`）**breaking** |
| `GET /api/v1/collect/query/daily_kline`（若存在） | 入参类型化，需确认前端调用方式 |
| `POST /api/v1/klines/collect` | 本就 502（X1），需**先修 X1 或明确下线**，否则改造后仍是 502 |

> ⚠️ **`{params:{start_date,end_date}}` → `{start_date,end_date}` 是 breaking change**。前端 `CollectManage` 的调用方必须同步改。若不想 breaking，Request DTO 可写成兼容两种形状（`model_validator(mode="before")` 拆信封），但那样契约就又不干净了。见 §5 决策 D1。

---

## 九、风险与回退

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| **前端未同步**导致 422 全量失败 | 高 | 采集中断 | DTO 定稿后与前端同一 PR 改；或过渡期兼容信封格式 |
| `COALESCE` 语义与预期不符 | 低 | name/change_pct 更新行为变化 | §8.3 的三条 SQL 抽查逐条验证 |
| 删 `KlineRepoImpl.save/save_batch` 漏了调用方 | 低 | 运行期 AttributeError | 改前 `grep -rn "save_batch\|\.save(" market/` 确认 |
| `BaseFetcher` 泛型化引发 26 个子类 import 失败 | 中 | 启动即崩 | D6=B 兜底；或改完后 `python -c "import main"` 冒烟 |
| `concurrency=1` 下 5000 只采集耗时过长 | — | 用户感知慢 | 现状不变；后续 SessionProvider 改造后放开 |
| 单个 Phase 失败 | — | — | P0–P3 同一 PR，`git revert` 整体回退 |

---

## 十、对齐与后续推广

### 10.1 本方案沉淀的模板

```
interface/route/{facet}     专属 Request DTO（OpenAPI 有 schema）
    ↓
application/port/params.py  Params（extra=forbid + 业务校验）
    ↓
application/service/xxx     编排：校验已在 Params 完成，service 不碰 SQL/ORM
    ↓
infrastructure/fetcher      BaseFetcher[ParamsT, BOT]，SDK 格式转换内聚
    ↓
infrastructure/repositories 唯一写入口，COALESCE upsert
```

### 10.2 后续 PR 排队

| PR | 内容 | 依赖 | 优先级 |
|---|---|---|---|
| **本 PR** | daily_kline 全链路（P0–P4） | — | 🔴 |
| **PR-A** | 修 §0.4 的 X1（`/klines/collect` 502）、X2（约束名）、X3（死代码 docstring） | 无 | 🔴（独立小 PR） |
| **PR-B** | 其余 25 个 service 迁移到专属 DTO + Params | 本 PR | 🟡 |
| **PR-C** | `BaseFetcher` 剩余 25 个子类迁移到 `fetch(params)` | 本 PR（D6=A 时可延后） | 🟡 |
| **PR-D** | `run_collect` session 改造 → `concurrency` 放开到 3–5 | 本 PR | 🟢（性能） |
| **PR-E** | `tech_daily` 双仓储收敛（`KlineRepoImpl` → `KlineRepository`） | 本 PR | 🟢 |
| **PR-F** | application 定义 `FetcherPort` Protocol，消除 application → infrastructure 的类 import | 本 PR | 🟢（架构） |
| **PR-G** | 跨 context ORM 依赖收口（`stock_basic` / `tech_daily` 归属 shared） | PR-E | ⚪ |

### 10.3 文档同步义务

落地后需同步更新：
- `docs/backend-docs/dev/00-项目索引.md`（当前内容已严重过时，仍描述旧的 `route/application/domain/infrastructure` 四段式与 `tech_kline_dailys` 旧表名）
- `docs/backend-docs/dev/level2/step1采集模块优化/03整体同步/02-三层同步情况总结.md`（把 daily 从「例外」改为「已改造」）

---

## 附录 A：关键代码位置索引

| 内容 | 文件:行 |
|---|---|
| route `daily_trigger` | `collect/interface/route/tech/__init__.py:63-70` |
| `CollectRequest.params: dict` | `collect/interface/dto/request/collect.py:18` |
| `DailyService.collect` | `collect/application/service/tech/daily_service.py:91-96` |
| `DailyService._validate_params`（57 行手写校验） | `.../daily_service.py:113-169` |
| `DailyService.run_collect` | `.../daily_service.py:171-296` |
| `DailyService._parse_date_range` | `.../daily_service.py:302-310` |
| `DailyService._list_all_symbols_via_session`（inline select） | `.../daily_service.py:314-322` |
| `DailyService._save`（inline pg_insert） | `.../daily_service.py:355-371` |
| `DailyService.get`（inline select） | `.../daily_service.py:374-407` |
| `BaseFetcher.fetch(**params)` | `collect/infrastructure/fetcher/base.py:47-49` |
| `DailyTushareFetcher._resolve_name` | `.../tech/DailyTushareFetcher.py:60-85` |
| `KlineRepository.save_klines`（死代码） | `collect/.../repositories/kline_repo.py:29-53` |
| `KlineRepository.list_symbols` | `.../repositories/kline_repo.py:133-142` |
| `port/params.py`（6 个模型，零 import） | `collect/application/port/params.py:22-49` |
| `TechKlineDailyDB`（表 `tech_daily`） | `market/.../models/tech_kline.py:19-38` |
| `get_daily_service`（无 repo 注入） | `collect/infrastructure/di/collect_service.py:58-71` |
| `get_kline_repository`（无调用方） | `collect/infrastructure/di/repo.py:15-20` |
| `KlineRepoImpl.save_batch`（约束名过期） | `market/.../repositories/kline_repository.py:72-95` |
| `StockInfoService.collect`（X1） | `market/.../stock_info_service.py:209-230` |