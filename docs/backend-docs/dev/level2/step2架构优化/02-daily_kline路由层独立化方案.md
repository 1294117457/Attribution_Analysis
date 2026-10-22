# daily_kline 路由层独立化方案（route 层专项）

> 位置：`docs/backend-docs/dev/level2/step2架构优化/02-daily_kline路由层独立化方案.md`
> 配套文档：
> - `./01-daily_kline全链路分层重构方案.md`（全链路方案；本文 **取代** 其 §4.1.1 / §4.1.2，其余章节继续有效）
> - `../../config/DDD.md`（分层规范）
> - `/home/dustp/codes/idproject/idbackend/src/app/routes/attribute.py`（**结构参考件**，见 §0.2）
> - `/home/dustp/codes/idproject/idbackend/架构规范skill.md`（**约束参考件**，见 §0.2）
> 更新日期：2026-10-21
> 状态：**待评审（暂不修改代码）**
> 范围：**只改 daily_kline 的 interface 层**（route + DTO），外加 1 个必要的 domain 异常改动 + 1 处可选的 DI 精简。

---

## 〇、决策摘要

### 0.1 一句话

把 `daily_kline` 从「挤在 `route/tech/__init__.py` 里的第 1 个 endpoint」变成**独立文件 `route/tech/daily.py`**，配套把「`CollectRequest{params: dict}` 信封」换成**专属 DTO**，并按 idproject 的约定做到 **route 层零 try/except**。

### 0.2 参考件：idproject 的 attribute.py 给了什么

`/home/dustp/codes/idproject/idbackend/src/app/routes/attribute.py` 的文件头把契约写死了：

```python
"""Attribute 管理路由

接口约定：
- 前缀：/api/rule-attribute
- 路由层只做三件事：接 DTO → 调 service → 包 R 响应
- **零 try/except**：业务异常由全局 exception_handlers 自动翻译
"""
```

配套 `架构规范skill.md` 的 6 条，本文抽取其中与本项目对应的 4 条作为本方案的硬约束：

| idproject 约定 | 本项目对应物 | 本方案如何落地 |
|---|---|---|
| ① 一个业务模块一个 route 文件，自带完整 `prefix` | `route/tech/daily.py` | **拆分文件**，但 prefix 归属见 §四 D2 |
| ② 路由层只做三件事：接 DTO → 调 service → 包 R 响应 | `R.ok(...)` | route 里只留 3 行业务逻辑 |
| ③ 零 try/except，异常由全局 handler 翻译 | `app/exception_handler.py` 已有 `DomainError` handler | **把 `InvalidParams` 改成 `DomainError` 子类**（§四 D3） |
| ④ DTO 集中定义，**service 直接收 DTO** | `interface/dto/request/daily.py` | `DailyService.collect(dto: DailyCollectRequest)`，**不做中间模型**（§四 D4） |

> **与 idproject 的两处差异（有意为之）**：
> 1. idproject 没有「facet」这一层，`routes/*.py` 直接注册到 app；本项目 collect context 是 **facet → service** 两级（`/collect/tech/daily_kline`），facet 前缀必须归口，否则同一个 `/collect/tech` 会散落在 5 个文件里。→ 见 D2。
> 2. idproject 的 service 是**静态方法**（`AttributeService.list_paged(db, ...)`），没有 service 工厂；本项目的 service 是**有状态**的（持 log_service / fetcher / repo / task_runner），且 collect 是 fire-and-forget，session 生命周期与请求不同步。→ 见 D7。

### 0.3 与 01 文档的关系

| 项 | 01 文档 | 本文 |
|---|---|---|
| `DailyCollectRequest` 定义 | §4.1.1（放 `dto/request/tech.py`） | **改**：单独放 `dto/request/daily.py`（一 service 一 DTO 文件，与 route 文件一一对应） |
| `DailyCollectParams`（application 层中间模型） | §4.2.1 定义 | **删除**：不需要中间模型，service 直接收 DTO（§四 D4） |
| route 改造 | §4.1.2（daily 仍写在 `__init__.py`） | **取代**：daily 独立成 `route/tech/daily.py` |
| DTO→Params 转换点 | `DailyCollectParams.from_request(req)` | **删除**：无转换，DTO 直传 |
| 异常处理 | route 里 `try/except InvalidParams` | **改**：零 try/except，靠全局 handler |

---

## 一、现状盘点

### 1.1 现状代码

`backend/src/contexts/collect/interface/route/tech/__init__.py`（104 行）当前结构：

```
__init__.py
├── router = APIRouter(prefix="/collect/tech", tags=["采集-技术面"])
├── _run(svc, body)          ← 胶水：try/except + dict/CollectResult 双分支 + 包响应
├── daily_trigger            ← 走 _run（本次要改）
├── minute_trigger           ← 走 _run
├── adj_factor_trigger       ← 走 _run
├── suspend_trigger          ← 走 _run
└── name_change_trigger      ← 走 _run
```

daily 端点本体只有 3 行：

```python
@router.post(
    "/daily_kline", summary="日 K 线采集（全市场，时间范围必传）",
    response_model=ApiResponse[CollectResponse],
)
async def daily_trigger(body: CollectRequest, svc=Depends(get_daily_service)):
    return R.ok((await _run(svc, body)).model_dump())
```

### 1.2 三个问题

**问题 1：`CollectRequest` 是「信封套信封」，契约在 OpenAPI 里是空的。**

```python
# interface/dto/request/collect.py
class CollectRequest(BaseModel):
    params: dict = Field(default_factory=dict)     # ← OpenAPI 渲染成 object
```

前端传 `{"params": {"start_date": "...", "end_date": "..."}}`，后端拿到 `body.params` 这个**裸 dict**。后果：
- OpenAPI 里 daily_kline 的请求体是 `object`，前端拿不到「start_date / end_date 必填」的契约
- 字段名拼错不报错（`params` 是 dict，内部不做 `extra="forbid"`），`service._validate_params()` 的「白名单返回」把多余字段**静默丢弃**
- 必填校验发生在 service 层手写代码里，而不是框架层

**问题 2：DTO → service 之间没有任何契约。**

`_run` 的第 46 行：

```python
result = await svc.collect(body.params)     # ← 直接把 dict 递给 service
```

`body.params` 是 dict，`DailyService.collect(params: dict)` 收的也是 dict。**从 HTTP 到 service 全程 `dict`**，`application/port/params.py` 里已经写好的 6 个 Params 模型（含 `TradeDateParams` / `SymbolParams`）**全仓无人 import**，是死代码。

**问题 3：`_run` 一个 helper 服务两种返回协议。**

```python
if isinstance(result, dict):        # daily / adj_factor / ... → {"status": "pending"}
    ...
# 兼容：REALTIME service 返回 CollectResult
return CollectResponse(total=result.total, ...)    # minute_kline → CollectResult
```

`minute_kline` 的 `collect()` 确实返回 `CollectResult`（`minute_service.py:41`），所以这个分支是**活代码**。一个 helper 同时服务两种协议，说明抽象边界画错了 —— 它按「同属 tech facet」抽象，而不是按「协议相同」抽象。

**问题 4（附带）：异常翻译绑死在 `_run` 上。**

`InvalidParams` 目前是 `ValueError` 子类：

```python
# contexts/collect/domain/exceptions.py
class InvalidParams(ValueError):
    pass
```

而全局 handler 只认 `DomainError`：

```python
# app/exception_handler.py
@application.exception_handler(DomainError)
async def domain_error_handler(request, exc): ...   # http_status 由异常自己声明
```

`InvalidParams` **不是** `DomainError`，所以一旦 route 不写 try/except，它会掉到 `Exception` 兜底 → **HTTP 500**（错误的状态码：参数问题被报成服务器故障）。这就是 `_run` 必须写 try/except 的根本原因 —— **不是 route 层该管这件事，是异常类没接进全局体系。**

---

## 二、目标结构

### 2.1 文件树

```
backend/src/contexts/collect/
├── domain/
│   └── exceptions.py                        ← 改：InvalidParams 继承 DomainError
├── application/
│   ├── port/
│   │   └── params.py                        ← 不动（死代码，本次不碰）
│   └── service/tech/
│       └── daily_service.py                 ← 改：collect() 入参从 dict 改 DTO
└── interface/
    ├── dto/
    │   ├── request/
    │   │   ├── collect.py                   ← 保留（其余 24 个 service 过渡期仍用）
    │   │   └── daily.py                     ← ★新增：DailyCollectRequest
    │   └── response/
    │       └── collect.py                   ← 不变（CollectResponse 已有 status/log_id/message）
    └── route/
        └── tech/
            ├── __init__.py                  ← ★改：瘦身为 facet 聚合器（只做 include_router）
            ├── daily.py                     ← ★新增：日 K 线路由（独立文件）
            ├── _common.py                   ← ★新增：_run 胶水（过渡期供其余 4 个用）
            ├── minute.py                    ← 后续（01 文档 §10 推广时拆）
            ├── adj_factor.py                ← 后续
            ├── suspend.py                   ← 后续
            └── name_change.py               ← 后续
```

> **`_common.py` 而不是留在 `__init__.py`**：`__init__.py` 的长期形态是**纯聚合器**（只声明 facet prefix + include 各 service 子路由），不含业务代码。`_run` 是过渡期产物，等 4 个 endpoint 迁完连同 `CollectRequest` 一起删掉。

### 2.2 依赖方向（改完之后）

```
  前端 POST {"start_date": "...", "end_date": "..."}
        │
        ▼
interface/dto/request/daily.py     DailyCollectRequest      ← interface 层
        │  （DTO 直传，无转换）
        ▼
application/service/tech/daily_service.py
                                   DailyService.collect(dto: DailyCollectRequest)
        │
        ▼
（01 文档 §4.2/§4.3 覆盖：repo 落库、fetcher 泛型化）
```

> **application → interface 的依赖是本仓库既有实践**，不是本方案引入的新例外：
> - `market/application/service/stock_info_service.py:17` → `from contexts.market.interface.dto.request.kline import KlineCollectRequest`
> - `market/application/service/stock_info_service.py:209` → `async def collect(self, request: KlineCollectRequest) -> KlineCollectResponse`
> - `user/application/service/stock_pool_service.py:28` → import `contexts.user.interface.dto.request.pool_operation`
> - `concept/application/service/concept_board_service.py:22` → import `contexts.concept.interface.dto.request.concept_board`
>
> 4 个 context 一致采用「application service 直接收 interface DTO」。本方案沿用，不引入新范式。

---

## 三、逐文件改造

### 3.1 新增 `interface/dto/request/daily.py`

```python
"""daily_kline 专属请求 DTO（interface 层）

背景：通用 CollectRequest.params 是 dict，OpenAPI 里渲染成 object，
      前端拿不到「start_date / end_date 必填」的契约。
      本文件给 daily_kline 一个具体 schema —— 一 service 一 DTO 文件，
      与 route/tech/daily.py 一一对应。

分工（对齐 idproject）：
    DTO 负责  字段类型 / 必填 / 格式      → 违反 → FastAPI 自动 422
    service 负责 业务规则（起止顺序 / 跨度上限）→ 违反 → InvalidParams → 400

过渡期：其余 24 个 service 继续用通用 CollectRequest.params 信封。
       迁移完成后 CollectRequest 整体删除。
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class DailyCollectRequest(BaseModel):
    """POST /api/v1/collect/tech/daily_kline 请求体

    - 时间范围必传（缺失 → 422）
    - 日期格式错误（2026/10/01）→ 422
    - 跨度超限、起止颠倒 → service 层校验 → InvalidParams → 400
    - symbols 不接受前端指定：全市场采集固定从 stock_basic 取
    """

    model_config = {"extra": "forbid"}

    start_date: date = Field(..., description="起始日期 YYYY-MM-DD")
    end_date: date = Field(..., description="结束日期 YYYY-MM-DD")


__all__ = ["DailyCollectRequest"]
```

> **`extra="forbid"` 的意义**：字段名拼错直接 422，而不是被 service 的「白名单返回」静默丢弃。这是把契约显式化的关键一环（对照现状问题 1）。
>
> **为什么业务规则不放 DTO 的 model_validator**：放 DTO 里会变成 **422**（pydantic `ValidationError` → `RequestValidationError`），而现状是 **400**（`InvalidParams`）。保持 400 需要把规则留在 service —— 这也与 idproject 一致（`create_attribute` 的 docstring：「service 内部校验 type / formula / group_name」）。

### 3.2 改 `application/service/tech/daily_service.py`

`collect()` 的入参从 `dict` 改为 DTO：

```python
from contexts.collect.interface.dto.request.daily import DailyCollectRequest


async def collect(self, dto: DailyCollectRequest) -> dict:
    """HTTP 入口：校验时间参数 → 派发，立即返回

    1. 校验（起止顺序 / 跨度上限）→ 不合法抛 InvalidParams
    2. asyncio.create_task(run_collect(norm))
    3. return { status: "pending" }
    """
    start, end = self._check_range(dto.start_date, dto.end_date)
    asyncio.create_task(self.run_collect({"start_date": start.isoformat(),
                                          "end_date": end.isoformat()}))
    return {"status": "pending"}
```

> **`run_collect` 内部仍收 dict**：它要写 `collect_logs.params`（JSONB），用 dict + `mode="json"` 语义更直白。这是**内部**契约，与**边界**契约（DTO）分工不同。
>
> **`_validate_params` 的三条规则去哪了**：
> - 「必填」→ DTO 字段 `Field(...)` → **422**
> - 「ISO 格式」→ DTO 字段类型 `date` → **422**
> - 「start <= end」「跨度 <= 1095」→ service `_check_range` → **400**
>
> 手写 `date.fromisoformat` 解析、字符串比较全部删除。

### 3.3 改 `domain/exceptions.py`（D3 的前置）

```python
# contexts/collect/domain/exceptions.py
from shared.domain.base import DomainError


class InvalidParams(DomainError):
    """入参非法（业务规则约束违反）

    继承 DomainError → 全局 exception_handler 自动翻译成 HTTP 400，
    route 层因此可以零 try/except（对齐 idproject 的路由层约定）。
    """

    def __init__(self, message: str):
        super().__init__(message, code="INVALID_PARAMS", http_status=DomainError.HTTP_BAD_REQUEST)
```

**影响面核查（已逐处确认）**：

| 检查项 | 结论 |
|---|---|
| `str(e)` 是否仍等于 message | ✅ `DomainError.__init__` 调了 `super().__init__(message)` |
| 是否有代码依赖 `InvalidParams` 是 `ValueError` | ✅ 无。全仓 5 处 `except ValueError` 捕的都是 builtin（`date.fromisoformat` / `strptime` / `StockCode`） |
| 已有 `except InvalidParams` 显式捕获是否仍有效 | ✅ 有效（子类关系不变），仅变成冗余，后续可清理 |
| 全局 handler 返回体 | `{"code": "INVALID_PARAMS", "message": "...", "data": null}`，HTTP 400 |
| 前端能否取到错误信息 | ✅ 拦截器读 `error.response?.data?.message \|\| error.response?.data?.detail`，取 `message` |

> **`code` 用字符串**：与仓库既有 `DomainError` 子类一致（`"STOCK_NOT_FOUND"` / `"POOL_NOT_FOUND"` / `"KLINE_DATA_ERROR"`）。
> ⚠️ 注意：前端 `unwrap()` 判断错误用的是 `d.code >= 400`，字符串比较为 false。**这不影响错误路径** —— HTTP 400 会让 axios 走 reject 分支，`unwrap` 根本不会执行。但若将来有人把错误响应的 HTTP 状态改成 200，字符串 code 就漏判了。**约定：错误响应必须带 ≥400 的 HTTP 状态码。**

### 3.4 新增 `interface/route/tech/daily.py`（核心）

```python
"""daily_kline 路由（日 K 线采集）

URL 路径保持 stable：POST /api/v1/collect/tech/daily_kline

路由层只做三件事（对齐 idproject attribute.py 约定）：
  1. 接 DTO     —— DailyCollectRequest（OpenAPI 有完整 schema）
  2. 调 service —— DailyService.collect(dto)
  3. 包 R 响应  —— R.ok(...)

零 try/except：InvalidParams 已接进 DomainError 体系，
由 app/exception_handler.py 的 domain_error_handler 自动翻译成 HTTP 400。

★ prefix 归属：本文件不自带 prefix，路径写相对路径 /daily_kline；
  facet 前缀 /collect/tech 与 tag 由 route/tech/__init__.py 统一声明并继承
  （见方案 §四 D2）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from shared.interface import _response as R
from contexts.collect.application.service.tech.daily_service import DailyService
from contexts.collect.interface.dto.request.daily import DailyCollectRequest
from contexts.collect.interface.dto.response.collect import ApiResponse, CollectResponse
from contexts.collect.infrastructure.di.collect_service import get_daily_service

router = APIRouter()


@router.post(
    "/daily_kline",
    response_model=ApiResponse[CollectResponse],
)
async def daily_trigger(
    body: DailyCollectRequest,
    svc: DailyService = Depends(get_daily_service),
):
    """日 K 线采集触发

    入参：缺失 / 格式错 → FastAPI 自动 422
    业务规则不合法（跨度超限、起止颠倒）→ InvalidParams → 400
    """
    result = await svc.collect(body)
    return R.ok(
        CollectResponse(
            log_id=result.get("log_id"),
            status=result.get("status"),
            message="采集任务已派发，请按 service_name=daily_kline 查询采集日志",
        ).model_dump()
    )


__all__ = ["router"]
```

**对照现状的三处变化**：

| 项 | 现状 | 改后 |
|---|---|---|
| 请求体 | `{"params": {...}}` | `{"start_date": ..., "end_date": ...}`（**breaking**，见 D5） |
| 入参校验 | service 里手写 `_validate_params` | FastAPI 422（字段级）+ service 400（业务级） |
| 异常翻译 | route 里 `try/except` | 全局 handler（route 零 try/except） |

> **`summary` / `description` 不写**：本项目 28 个采集端点的 summary 都只是重复「XX 采集」四五个字，信息量低且容易与 catalog 里的 `META.label` 走偏。真正有价值的契约信息（必填、跨度上限、轮询方式）写在 DTO 的 `Field(description=...)` 里，会直接渲染到 OpenAPI 的字段说明中 —— 位置更准确，也不用在两处维护。

### 3.5 瘦身 `interface/route/tech/__init__.py`

```python
"""tech routes — 技术面 facet 路由聚合器

URL 路径保持 stable：
    /daily_kline  /minute_kline  /adj_factor  /suspend  /name_change

本文件只做三件事：声明 facet 前缀与 tag、include 各 service 子路由、导出 router。
业务代码全部下沉到各 service 的独立文件（与 application/service/tech/ 一一对应）。

过渡期：minute / adj_factor / suspend / name_change 仍走通用信封
       （CollectRequest.params + _common._run），迁移后连同 CollectRequest 一并删除。
"""
from __future__ import annotations

from fastapi import APIRouter

from contexts.collect.interface.route.tech._common import router as legacy_router
from contexts.collect.interface.route.tech.daily import router as daily_router

router = APIRouter(prefix="/collect/tech", tags=["采集-技术面"])

# 已迁移：专属 DTO
router.include_router(daily_router)

# 过渡期：通用信封（4 个 service）
router.include_router(legacy_router)


__all__ = ["router"]
```

### 3.6 新增 `interface/route/tech/_common.py`（过渡期）

把 `_run` 从 `__init__.py` 原样搬过来，**行为不变**：

```python
"""tech facet 过渡期通用路由（通用信封 CollectRequest.params）

⚠️ 过渡期产物：4 个 service 迁到专属 DTO 后，本文件与 CollectRequest 一起删除。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from shared.interface import _response as R
from contexts.collect.application.service.base import InvalidParams
from contexts.collect.interface.dto.request.collect import CollectRequest
from contexts.collect.interface.dto.response.collect import ApiResponse, CollectResponse
from contexts.collect.infrastructure.di.collect_service import (
    get_minute_service,
    get_adj_factor_service,
    get_suspend_service,
    get_name_change_service,
)

router = APIRouter()


async def _run(svc, body: CollectRequest) -> CollectResponse:
    """统一执行：触发后台采集任务（过渡期）"""
    try:
        result = await svc.collect(body.params)
    except InvalidParams as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if isinstance(result, dict):
        return CollectResponse(
            log_id=result.get("log_id"),
            status=result.get("status"),
            message=f"采集任务已派发，前端请用 log_id 轮询 /collect/logs/{result.get('log_id')}",
        )
    return CollectResponse(
        total=result.total, success=result.success, fail=result.fail,
        skip=result.skip, saved=result.saved, message=result.message,
    )


# ... 其余 4 个 endpoint 原样搬过来（minute / adj_factor / suspend / name_change）


__all__ = ["router"]
```

> **`_run` 里的 `except InvalidParams` 保留**：虽然 `InvalidParams` 现在是 `DomainError`、全局 handler 能接住，但显式 catch 优先级更高，且**响应体形状不同**（`{"detail": ...}` vs `{"code","message","data"}`）。保留可保证其余 4 个 endpoint 的行为**逐字节不变**（零回归风险）。等它们迁完再统一。

### 3.7 `shared/interface/router_compat.py` —— **零改动**

```python
from contexts.collect.interface.route.tech import router as collect_tech_router
...
api_router.include_router(collect_tech_router)
```

`tech/__init__.py` 仍然导出 `router`，对外契约不变。

---

## 四、关键决策

### D1：文件拆分粒度 —— 一个 service 一个 route 文件

**决策**：`route/tech/daily.py` 独立文件，与 `application/service/tech/daily_service.py` 一一对应。

**理由**：
- `application/service/tech/` 已经是「一 service 一文件」（`daily_service.py` / `minute_service.py` / `adj_factor_service.py` / `suspend_service.py` / `name_change_service.py`），route 层保持同样的切分，两个目录能一一对读
- 与仓库既有先例一致：`market/interface/route/kline.py` ↔ `market/interface/dto/request/kline.py`、`concept/interface/route/concept_board.py`
- daily 的特殊性（唯一带「时间范围必传 + 跨度上限」的 service）需要独立的 DTO，塞在 `__init__.py` 里只会越滚越大

**代价**：`tech/` 目录下多几个文件。**可接受** —— 这正是 idproject `routes/` 的形态。

### D2：prefix 归属 —— facet 归口（方案 B）

**决策**：`daily.py` **不自带 prefix**，写相对路径 `/daily_kline`；facet 前缀 `/collect/tech` 与 tag 由 `tech/__init__.py` 统一声明，子 router 通过 `include_router` 挂载。

**对比**：

| | 方案 A（idproject 原样） | 方案 B（facet 归口）✅ |
|---|---|---|
| `daily.py` | `APIRouter(prefix="/collect/tech/daily_kline", tags=["采集-技术面"])` | `APIRouter()`，路径写 `/daily_kline` |
| 挂载点 | `router_compat.py` 里 `api_router.include_router(collect_daily_router)` | `tech/__init__.py` 里 `router.include_router(daily_router)` |
| 最终 URL | `/api/v1/collect/tech/daily_kline` ✅ | `/api/v1/collect/tech/daily_kline` ✅ |
| facet 前缀定义处 | 散落在每个子文件 | **单点**：`tech/__init__.py` |
| tag | 每个子文件重复声明 | **继承父 router**（FastAPI `add_api_route` 会 `current_tags = self.tags.copy()`） |
| `router_compat.py` | 要加一行 | **零改动** |
| catalog / 前端目录树 | 前缀来源不唯一 | 前缀来源唯一，与 `catalog_service` 按 facet 生成 URL 的逻辑一致 |

**B 的继承行为已实测**（FastAPI 0.115.0）：父 router `prefix="/collect/tech", tags=["采集-技术面"]` include 子 router `APIRouter()` 且子路由 path `/daily_kline` → 最终 path `/collect/tech/daily_kline`，tags `['采集-技术面']` ✅

### D3：零 try/except —— `InvalidParams` 接入 `DomainError` 体系

**决策**：改 `InvalidParams` 的基类为 `DomainError`，让全局 handler 接管翻译。

**理由**：
- idproject 规范第 1 条 + 第 6 条：「异常捕获已在中间件做好，避免重复」
- 本项目 `app/exception_handler.py` **已经有** `DomainError` handler（HTTP 状态码由异常自己声明），但 `InvalidParams` 没接进去 —— 这是**接线遗漏**，不是设计缺失
- 现状下 `InvalidParams` 若逃逸到框架，会被 `Exception` 兜底成 **500**：参数错误被报成服务器故障，语义错误

**替代方案（不推荐）**：在 `exception_handler.py` 里给 `InvalidParams` 单独注册一个 handler。改动更小，但**破坏了仓库既有的 DomainError 统一约定**（`shared/domain/base.py` 的 docstring 明确说「业务异常归 domain 层」「HTTP 状态码由异常自己声明」），且 `InvalidParams` 会成为唯一不走 DomainError 的业务异常。

**影响**：见 §3.3 的核查表。

### D4：DTO 直传 service，**不设中间模型**

**决策**：`DailyService.collect(dto: DailyCollectRequest)`，DTO 从 HTTP 一路传到 service，**不做 DTO → Params 的转换**，**不新增** `application/port/params.py::DailyCollectParams`。

**理由**：

1. **与 idproject 规范第 3 条一致**：「Request,Response,VO,DTO 等数据结构体在 schema 封装好，**互相的转换也在 schema 封装好对应方法**」—— 但本例**根本不需要转换**（字段一一对应），多一个模型就是多一份要同步的字段定义。
2. **与 idproject 的实际代码一致**：`AttributeService.create(db, req)` —— service 直接收 Request DTO，业务规则校验在 service 内部。
3. **与本仓库既有实践一致**（§2.2 的 4 个 context 实证）—— application service 直接收 interface DTO 是**主流做法**，不是例外。
4. **少一个模型 = 少一处失配**：`DailyCollectRequest` 与 `DailyCollectParams` 字段完全相同（`start_date` / `end_date`），一旦有一边加了字段忘了改另一边，转换处会静默丢字段。DTO 直传没有这个缝隙。

**代价**：application 层 import interface 层的 DTO。**这个代价本仓库已经付过了**（4 个 context 都在付），本方案不新增例外。若将来要严格分层，正确的做法是**整体迁移**（把 DTO 下沉到 application，interface 只做 import 别名），而不是在单个 service 上搞特殊。

**与 01 文档 §4.2.1 的差异**：01 文档设计的 `DailyCollectParams`（含 `max_span_days` 字段 + `to_log_dict()`）**本方案不需要**：
- `max_span_days` 是**服务端常量**（1095 天），不该出现在前端契约里 → 直接用 `DailyService.MAX_SPAN_DAYS`
- `to_log_dict()` 是**内部**契约（写 `collect_logs.params` JSONB）→ 由 service 内部处理，不外泄

### D5：请求体 breaking change 与前端同步

**现状**：`POST /api/v1/collect/tech/daily_kline` body = `{"params": {"start_date": "...", "end_date": "..."}}`
**改后**：body = `{"start_date": "...", "end_date": "..."}`

**前端改动点**（唯一一处）：

```ts
// frontend/src/views/collect-manage/api.ts:182-192
// 现状：所有 service 统一包一层 params 信封
const body: CollectStartPayload = 'params' in (payload as any)
  ? (payload as CollectStartPayload)
  : { params: (payload as Record<string, any>) || {} }
```

改后需要按 service 区分（daily_kline 用扁平体，其余 24 个仍用信封）。建议：

```ts
// 迁移期白名单：已迁到专属 DTO 的 service 用扁平请求体
const FLAT_BODY_SERVICES = new Set(['daily_kline'])

const body = FLAT_BODY_SERVICES.has(name)
  ? (payload as Record<string, any>)
  : { params: (payload as Record<string, any>) || {} }
```

**发布顺序**：

| 方案 | 做法 | 适用 |
|---|---|---|
| **A 同步发版（推荐）** | 前后端同一个 PR 改，前后端一起上线 | 本仓库前后端同仓同发布，天然原子 |
| B 兼容窗口 | DTO 加 `model_validator(mode="before")` 展开旧信封 `{"params": {...}}`，前端下一批再改 | 需要分开上线时；过渡期结束后删掉兼容分支 |

**方案 B 的兼容代码**（如需要）：

```python
@model_validator(mode="before")
@classmethod
def _unwrap_legacy_envelope(cls, data):
    """过渡期兼容旧信封 {"params": {...}}；前端切换完成后删除"""
    if isinstance(data, dict) and "params" in data:
        data = dict(data.get("params") or {})
    return data
```

> 兼容期内 `extra="forbid"` 对 `params` 键的检查会失效（先被 pop 掉），需在代码注释里标注。

**状态码变化**（前端不受影响，但需记录）：

| 场景 | 现状 | 改后 |
|---|---|---|
| 缺 `start_date` | 400 | **422** |
| 日期格式错（`2026/10/01`） | 400 | **422** |
| 起止颠倒 | 400 | 400 |
| 跨度超限 | 400 | 400 |

422 与 400 都是 4xx，前端拦截器都弹 `message`，**用户感知一致**。

### D6：`_run` 的去留

| 阶段 | `_run` 位置 | `CollectRequest` |
|---|---|---|
| **本次** | 移到 `route/tech/_common.py`，只服务其余 4 个 | 保留 |
| 后续（01 文档 §10 推广） | 4 个 endpoint 逐个迁到专属 DTO | 保留 |
| 全部迁完 | **删除** `_common.py` + `CollectRequest` + `CollectResult` 兼容分支 | **删除** |

**为什么本次不直接删 `_run`**：其余 4 个 endpoint 还在用它，一次性删会连带改 4 个 service 的入参契约，超出「只改 daily_kline」的批次边界。

### D7：service 的注入方式 —— 保留 DI 工厂，但去掉多余的 session 依赖

**决策**：
- **保留** `Depends(get_daily_service)`（service 的**构造**留在 DI 工厂）
- **可选**：`get_daily_service()` 去掉 `session: AsyncSession = Depends(get_raw_db)` 参数

**为什么 service 的构造必须留在 DI 工厂（不改成 route 里 new）**：

1. `DailyService` 需要 `log_service=CollectLogService()`（application 层的日志服务，内部自管 attribution 库短事务 + 全局 redis 单例）和 `fetcher`。让 route 写 `DailyService(log_service=CollectLogService())` 意味着 **route 知道了 application 内部的装配细节** → 违反「route 层只做三件事」。
2. 28 个 factory 已是仓库统一约定（`collect_service.py` 的 docstring 写明「标准工厂模板」「28 个 factory 无一例外」）。破例的成本 > 收益。
3. idproject 的 `AttributeService.list_paged(db, ...)` 是**静态方法 + session 显式传参**，本项目不适用（见下）。

**为什么 idproject 的静态方法风格不适用**：

| | idproject | 本项目 |
|---|---|---|
| service 形态 | 静态方法命名空间（`AttributeService.list_paged`） | 有状态实例（持 log_service / fetcher / repo / task_runner） |
| session 来源 | route 的 `Depends(get_db)` → 显式传给 service | DI 工厂注入；且 collect 是 fire-and-forget，session 生命周期 ≠ 请求生命周期 |
| 改造量 | —— | 28 个 service 全部重写 + 28 个 factory 废弃 |

**「去掉多余 session 依赖」是一个真实发现**：

- `DailyService.collect()` **完全不用** `self._session` —— 它只做校验 + `asyncio.create_task(self.run_collect(...))`
- `run_collect()` 自己 `async with get_raw_db_context() as session` 开新 session
- `self._session` 只被 `get()`（实时查询）用，而 **`get()` 目前没有任何调用方**（已全仓确认；`stock_info_service` 里那条 `daily_svc` 路径是已登记的缺陷 X1，注入缺失）
- 现状代价：每次触发 daily 采集，都从 raw_data 连接池 **checkout 一个连接并在整个请求期间持有**，而这个连接一次都没被用过

**建议**（可作为独立小改动，不阻塞本方案）：

```python
def get_daily_service():
    """日 K 线 service（不再注入 session）

    - collect() 不碰 DB（run_collect 自开 raw_data session）
    - get() 实时查询改为内部自开 session（与 run_collect 一致）
    """
    from contexts.collect.application.service.tech.daily_service import DailyService
    return DailyService(log_service=CollectLogService())
```

**风险**：改完后 `DailyService.get()` 需要自己开 session（`async with get_raw_db_context()`），要一并改。当前 `get()` 无调用方，**改动实际影响为零**，但属于「有调用方前先修好」的预防性改动。

> **本方案不强制这一项**。它是 Step 2 的可选子项（见 §六）。

---

## 五、影响面清单

### 5.1 后端

| 文件 | 动作 | 说明 |
|---|---|---|
| `collect/interface/route/tech/daily.py` | **新增** | 日 K 线路由（§3.4） |
| `collect/interface/route/tech/__init__.py` | **改** | 瘦身为 facet 聚合器（§3.5） |
| `collect/interface/route/tech/_common.py` | **新增** | 过渡期通用信封路由（§3.6） |
| `collect/interface/dto/request/daily.py` | **新增** | `DailyCollectRequest`（§3.1） |
| `collect/domain/exceptions.py` | **改** | `InvalidParams` 继承 `DomainError`（§3.3） |
| `collect/application/service/tech/daily_service.py` | **改** | `collect(params: dict)` → `collect(dto: DailyCollectRequest)`；`_validate_params` 三条规则拆成「DTO 层 422」+「service 层 400」（§3.2） |
| `collect/infrastructure/di/collect_service.py` | **可选改** | `get_daily_service` 去掉 session 依赖（D7） |
| `collect/application/port/params.py` | **不改** | 死代码，本次不碰 |
| `collect/interface/dto/request/collect.py` | **不改** | 过渡期保留 |
| `shared/interface/router_compat.py` | **不改** | 零改动（§3.7） |

> ⚠️ **service 侧是硬依赖**：`DailyService.collect()` 必须同步改成收 DTO，否则 route 传模型、service 按 dict 取会炸。因此本方案**不能只改 route**，service 的签名适配必须同批落地。

### 5.2 前端

| 文件 | 动作 | 说明 |
|---|---|---|
| `frontend/src/views/collect-manage/api.ts` | **改** | `runService` 的请求体包装按 service 白名单区分（§D5） |
| `frontend/src/views/collect-manage/components/CollectActionCard.vue` | **不改** | 它 emit 的是 `{ params }`（内部语义），由 `api.ts` 决定最终 body 形状 |

### 5.3 文档

| 文件 | 动作 |
|---|---|
| `docs/backend-docs/dev/level2/step2架构优化/01-daily_kline全链路分层重构方案.md` | 标注 §4.1.1 / §4.1.2 / §4.2.1 被本文取代 |
| `docs/backend-docs/dev/00-项目索引.md` | §4 路由模块清单同步（实施后） |
| `docs/backend-docs/data/当前接口实现.md` | 请求体形状变更同步（实施后） |

---

## 六、实施步骤

> 3 个可独立评审的 commit。每个 commit 结束时应用都能跑（无中间态破损）。

### Step 1：domain 异常接入全局体系（独立、无行为变化）

1. `collect/domain/exceptions.py`：`InvalidParams` 改继承 `DomainError`（`code="INVALID_PARAMS"`, `http_status=400`）
2. 验证：其余 4 个 tech endpoint 的 400 响应体不变（`_run` 里的显式 catch 优先）；`market` / `concept` 的 `except InvalidParams` 仍有效

**验收**：
```bash
curl -s -X POST http://localhost:8000/api/v1/collect/tech/daily_kline \
  -H 'Content-Type: application/json' \
  -d '{"params":{}}' -w '\n%{http_code}\n'
# 期望：400 + 缺少必填参数...
```

### Step 2：DTO + 独立 route 文件 + service 签名（核心）

1. `interface/dto/request/daily.py`：新文件（§3.1）
2. `interface/route/tech/daily.py`：新文件（§3.4）
3. `interface/route/tech/_common.py`：新文件，`_run` + 其余 4 个 endpoint（§3.6）
4. `interface/route/tech/__init__.py`：改为聚合器（§3.5）
5. `application/service/tech/daily_service.py`：`collect()` 收 DTO；`_validate_params` 拆成 DTO 层 + service 层（§3.2）
6. （可选）`infrastructure/di/collect_service.py`：`get_daily_service` 去掉 session 依赖（D7）

**验收**：
```bash
# 1) 缺字段 → 422
curl -X POST .../collect/tech/daily_kline -H 'Content-Type: application/json' -d '{}'
# 2) 格式错 → 422
curl -X POST .../collect/tech/daily_kline -d '{"start_date":"2026/10/01","end_date":"2026-10-21"}'
# 3) 起止颠倒 → 400
curl -X POST .../collect/tech/daily_kline -d '{"start_date":"2026-10-21","end_date":"2026-10-01"}'
# 4) 正常 → 200
curl -X POST .../collect/tech/daily_kline -d '{"start_date":"2026-10-01","end_date":"2026-10-21"}'
# 5) 多传字段 → 422（extra=forbid）
curl -X POST .../collect/tech/daily_kline -d '{"start_date":"2026-10-01","end_date":"2026-10-21","symbols":["000001"]}'
```

### Step 3：前端同步 + 文档更新

1. `frontend/src/views/collect-manage/api.ts`：扁平 body 白名单（§D5）
2. 更新 01 文档（标注被取代的章节）+ `00-项目索引.md` + `当前接口实现.md`

---

## 七、验收清单

- [ ] `POST /api/v1/collect/tech/daily_kline` 的 **URL 与 HTTP 方法不变**
- [ ] OpenAPI（`/docs`）里该端点的 requestBody 是**有字段的对象**（不是 `object`），`start_date` / `end_date` 标 `required`
- [ ] OpenAPI 里该端点的 tag 仍是 `采集-技术面`
- [ ] 缺字段 / 格式错 → **422**；起止颠倒 / 跨度超限 → **400**；正常 → **200** `{code:200, data:{status:"pending", ...}}`
- [ ] 多传字段（`symbols`）→ **422**（不再静默丢弃）
- [ ] `route/tech/__init__.py` 行数 < 40，且不含 `try/except`
- [ ] `daily.py` 内**零 try/except**、零字段搬运、无 `summary` / `description`
- [ ] `daily_service.collect()` 的入参类型标注是 `DailyCollectRequest`
- [ ] `application/port/params.py` **零改动**（本方案不引入中间模型）
- [ ] 其余 4 个 tech endpoint 行为**逐字节不变**（`minute` / `adj_factor` / `suspend` / `name_change`）
- [ ] `router_compat.py` 零改动
- [ ] `git grep "CollectRequest" backend/src/contexts/collect/interface/route/tech/` 只命中 `_common.py`
- [ ] 前端 `CollectManage.vue` 触发 daily 采集 → 列表页能看到 pending 日志

---

## 八、风险与回滚

| # | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R1 | **请求体 breaking change**，前后端不同步上线 → 前端 422 | 中 | 高 | 同 PR 同发版；或用 D5 方案 B 的兼容 validator 留窗口 |
| R2 | `InvalidParams` 改基类后，某处依赖 `ValueError` 语义 | 低 | 高 | 已逐处核查（§3.3）：全仓无依赖；CI 跑全量测试兜底 |
| R3 | `extra="forbid"` 把前端现有的一些多余字段变成 422 | 中 | 中 | 前端 `CollectActionCard.vue` 只传 `start_date` / `end_date`，逐字段核对 |
| R4 | service 侧签名改造遗漏（route 传 DTO、service 收 dict） | 中 | 高 | Step 2 必须在同一个 commit 内改完 service，验收用真实请求打 |
| R5 | `include_router` 后 prefix / tag 与预期不符 | 低 | 中 | 已在 FastAPI 0.115.0 实测验证（§D2）；Step 2 验收看 OpenAPI |
| R6 | 响应体从 `{"detail": ...}` 变 `{"code","message","data"}` | 低 | 低 | 前端拦截器两个字段都读（§3.3）；其余 4 个 endpoint 行为不变 |
| R7 | 状态码从 400 变 422（缺字段 / 格式错） | 高（必然） | 低 | 前端都弹 message，用户感知一致（§D5 状态码变化表） |
| R8 | D7 去掉 session 依赖后，`get()` 需要自开 session | 低 | 低 | `get()` 当前无调用方；改动时同步改 `get()` 实现 |

**回滚**：本方案是纯新增文件 + 4 处小改，回滚成本低。
- Step 1 独立提交 → 单独 revert 即可
- Step 2 独立提交 → revert 后回到现状（`tech/__init__.py` 恢复原样）
- Step 3 独立提交 → 只动前端与文档，单独 revert
