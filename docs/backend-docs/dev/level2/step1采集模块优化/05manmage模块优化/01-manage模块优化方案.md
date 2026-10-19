# 01-manage 模块优化方案

> 位置：`docs/backend-docs/dev/level2/step1采集模块优化/05manmage模块优化/01-manage模块优化方案.md`
> 上游文档：
> - `../../03整体同步/01-interface-service-repo同步方案.md`（Phase 1-4 已落地）
> - `../../03整体同步/04-Session依赖注入优化方案.md`（session 注入已落地）
> 更新日期：2026-10-19
> 状态：**待评审（暂不修改代码）**

---

## 〇、决策与方向（评审前先看）

### 0.1 本次优化目标

把 `interface/router.py` 里"**管理面 + 业务面混在一起**"的状态拆开，让 catalog 元数据的来源从"router 里硬编码的 `_build_catalog()`"改为"**每个 service 自报家门**"：

> 1. **去掉 `interface/router.py`**——业务面的 5 个 facet router 直接挂到 `router_compat.py`，与 `market` 上下文同一模式。
> 2. **每个 service 内部声明 `UI_SCHEMA`**——前端需要的 UI 字段由 service class 显式给出，router 不再推导。
> 3. **新增 `manage/` 子模块**——catalog + 实时查询两个 endpoint 收敛到 `interface/manage/` 下，由 `CatalogService` 统一反射生成元数据。

### 0.2 现状问题

| 现状 | 问题 |
|---|---|
| **`interface/router.py` 共 329 行**，承担 3 个职责：导出 `facet_routers`、构造 catalog、暴露 `catalog_router`（`/services` + `/query/*`） | 职责混杂；同一文件里既有业务面又有管理面；其他 context（market / auth / concept）都没有这种"中间 router.py" |
| **`_infer_param_ui(key, default)`** 是一个 80 行的 if/elif 推导函数 | 推导规则是"猜"的（看 key 名字后缀、看 value 类型），字段语义丢失，类型易混；service 自己最清楚每个字段是日期、股票代码还是下拉框 |
| **`_build_catalog()` 硬编码 28 个 service class** | 新增 service 必须改这个 list；catalog 业务逻辑（`name/facet/label/...`）和 router 编织在一起 |
| **`facet_routers = (tech, capital, ...)` 这个 tuple** 是给 `router_compat.py` 循环用的 | `market` 上下文是 6 个 `include_router` 显式调用，没有 tuple——不一致 |

### 0.3 根因

"**catalog 业务 = router 的事**"这个错位导致：
- 新增 service → 要改 2 个地方（`application/service/{facet}/{name}_service.py` + `interface/router.py` 的 `services` 列表）
- 修改 UI 字段语义 → 要改 `_infer_param_ui` 这个 if/elif 大块
- 拆 `manage/` 模块 → 不知道把 `_build_catalog` 放哪（放 `interface/manage/` 不合适——它有业务；放 `application/service/manage/` 又得绕一圈）

### 0.4 三项决策（user 拍板）

| # | 决策 | 选择 |
|---|---|---|
| **M1** | `interface/router.py` 去留 | **A：整文件删除**（与 `market` 上下文一致，5 个 facet router 直接挂到 `router_compat`） |
| **M2** | UI schema 来源 | **A：每个 service class 上声明 `UI_SCHEMA = [...]` class attribute**（部分 service 已声明，本次补全 + 文档规范） |
| **M3** | catalog 业务归属 | **A：`application/service/manage/catalog_service.py`**（业务逻辑归 application 层，handler 归 interface 层） |

---

## 一、目标架构

### 1.1 整体目录（重构后）

```
contexts/collect/
├── application/
│   └── service/
│       ├── tech/                         # 5 个 service
│       ├── capital/                      # 9 个 service
│       ├── fundamental/                  # 12 个 service
│       ├── news/                         # 1 个 service
│       ├── sentiment/                    # 1 个 service（占位）
│       └── manage/                       # ← 新增：catalog 业务
│           ├── __init__.py
│           └── catalog_service.py        # ← CatalogService.list() / .get()
├── interface/
│   ├── manage/                           # ← 新增：管理面
│   │   ├── __init__.py
│   │   ├── router.py                     # ← manage_router（catalog + 未来 runs/schedules）
│   │   └── catalog_handler.py            # ← GET /collect/services + GET /collect/query/{name}
│   ├── route/                            # 5 个 facet router（已有，不动结构）
│   │   ├── tech/router.py
│   │   ├── capital/router.py
│   │   ├── fundamental/router.py
│   │   ├── news/router.py
│   │   └── sentiment/router.py
│   └── router.py                         # ← 整文件删除
└── infrastructure/
    └── ...
```

> **`application/service/manage/`** 和 **`interface/manage/`** 各管一边：application 负责"**怎么造**"（catalog 业务），interface 负责"**怎么传**"（HTTP handler）。这与 DDD 分层一致。

### 1.2 与 `market` 上下文的对照

| 维度 | market（现状参照） | collect（重构后） |
|---|---|---|
| `interface/router.py` 中间层 | ❌ 无 | ❌ 无（删除） |
| facet/route 数量 | 6（kline/stock/panel/minute_kline/data_board/stock_analysis） | 5（tech/capital/fundamental/news/sentiment） |
| `interface/manage/` | ❌ 无（market 暂无管理面需求） | ✅ 有（catalog + 未来扩展） |
| `router_compat.py` 挂载方式 | 6 个 `include_router` 显式调用 | 5 个 facet `include_router` + 1 个 manage_router `include_router` |
| UI 元数据来源 | 无 catalog 需求 | `service.UI_SCHEMA`（class attribute） |

---

## 二、动作 A：每个 service 声明 `UI_SCHEMA`

### 2.1 现状盘点

28 个 service 中已有 `UI_SCHEMA` 声明的有：`DailyKlineService`、`AdjFactorService`、`SuspendService`、`MinuteKlineService` 等部分 service。**本次要把 28 个 service 全部声明 `UI_SCHEMA`**，并固化字段规范。

### 2.2 `UI_SCHEMA` 字段规范

```python
UI_SCHEMA = [
    {
        "key":         str,    # 必填，对应 CollectRequest.params 的 key
        "ui":          str,    # 必填，前端控件类型（见下表）
        "label":       str,    # 必填，前端 label 文案（中文）
        "required":    bool,   # 必填，是否必传
        "placeholder": str,    # 选填，输入框 placeholder
        "help":        str,    # 选填，输入框下方说明
    },
    ...
]
```

### 2.3 `ui` 控件类型枚举

| `ui` 取值 | 前端控件 | 适用场景 | 示例 `key` |
|---|---|---|---|
| `ts_code_str` | 文本输入 | Tushare 单股代码（带市场后缀） | `ts_code` |
| `symbols_list` | 多行文本/Tag | 股票代码列表（每行一只） | `symbols` |
| `index_codes_list` | 多行文本/Tag | 指数代码列表 | `index_codes` |
| `symbol_str` | 文本输入 | 6 位股票代码（无后缀） | `symbol` |
| `index_code_str` | 文本输入 | 指数代码 | `index_code` |
| `date_str` | 日期选择器 | 日期（YYYY-MM-DD） | `trade_date` / `start_date` / `end_date` |
| `list_status` | 下拉单选 | 上市状态 | `L`/`D`/`P` |
| `exchange_multi` | 多选下拉 | 交易所 | `SSE`/`SZSE`/`BSE` |
| `interval_kline` | 下拉单选 | K线周期（分钟） | `1`/`5`/`15`/`30`/`60` |
| `period_kline` | 下拉单选 | K线周期（日/周/月） | `D`/`W`/`M` |
| `minutes_int` | 数字输入 | 分钟数 | `minutes` |
| `days_int` | 数字输入 | 天数 | `days` |
| `years_int` | 数字输入 | 年数 | `years` |
| `limit_int` | 数字输入 | 限制条数 | `limit` |
| `bool_flag` | Switch | 布尔开关 | `is_paused` 等 |
| `str_list` | 多行文本 | 通用字符串列表 | 其他 |
| `str` | 文本输入 | 兜底字符串 | 其他 |

> **service 自己声明最准确的控件类型**——比如 `start_date` 和 `end_date` 都是 `date_str`，`symbols` 是 `symbols_list`（不是 `str_list`），`trade_date` 必填而 `start_date` 选填。

### 2.4 各 facet service 的 `UI_SCHEMA` 草案

#### tech（5 个）

| service | `UI_SCHEMA` |
|---|---|
| `DailyKlineService` | `symbols`(symbols_list, 非必) + `start_date`(date_str, 非必) + `end_date`(date_str, 非必) |
| `MinuteKlineService` | `symbol`(symbol_str, 非必) + `interval`(interval_kline, 非必) + `days`(days_int, 非必) |
| `AdjFactorService` | `symbols`(symbols_list, 非必) |
| `SuspendService` | `trade_date`(date_str, 必填) |
| `NameChangeService` | `[]`（无参数） |

#### capital（9 个）

| service | `UI_SCHEMA` 草案 |
|---|---|
| `MoneyflowService` | `trade_date`(date_str, 非必) |
| `MoneyflowHsgtService` | `trade_date`(date_str, 非必) |
| `TopListService` | `trade_date`(date_str, 非必) |
| `TopInstService` | `trade_date`(date_str, 非必) |
| `BlockTradeService` | `trade_date`(date_str, 非必) |
| `MarginService` | `trade_date`(date_str, 非必) |
| `HsgtTop10Service` | `trade_date`(date_str, 非必) |
| `LimitListService` | `trade_date`(date_str, 非必) |
| `HolderNumberService` | `ts_code`(ts_code_str, 非必) |

#### fundamental（12 个）

| service | `UI_SCHEMA` 草案 |
|---|---|
| `DailyBasicService` | `trade_date`(date_str, 非必) |
| `FinIncomeService` | `ts_code`(ts_code_str, 非必) + `period`(str, 非必) |
| `Top10HoldersService` | `ts_code`(ts_code_str, 必填) |
| `Top10FloatHoldersService` | `ts_code`(ts_code_str, 必填) |
| `DividendService` | `ts_code`(ts_code_str, 非必) |
| `StockBasicService` | `list_status`(list_status, 非必) + `exchange`(exchange_multi, 非必) |
| `StockConceptsService` | `ts_code`(ts_code_str, 必填) |
| `ConceptListService` | `[]`（无参数） |
| `ConceptMembersService` | `concept_id`(str, 非必) |
| `ConceptIndexDailyService` | `ts_code`(ts_code_str, 必填) |
| `ConceptMinuteService` | `concept_id`(str, 必填) |
| `ConceptSnapshotService` | `[]`（无参数） |

#### news（1 个）

| service | `UI_SCHEMA` 草案 |
|---|---|
| `NewsService` | `start_date`(date_str, 非必) + `end_date`(date_str, 非必) + `src`(str, 非必) |

#### sentiment（1 个）

| service | `UI_SCHEMA` |
|---|---|
| `SentimentService` | `[]`（空壳，catalog 隐藏） |

> **所有 `UI_SCHEMA` 在评审通过后由人手工编辑**——本方案只列草案，不在评审阶段批量修改。落地时按"先 tech 5 个验证 → 推广到 capital 9 个 → 推广到 fundamental 12 个"节奏。

### 2.5 已声明 service 的对照

| service | 当前 `UI_SCHEMA` | 状态 |
|---|---|---|
| `SuspendService` | 1 项 `trade_date`(date_str, 必填) | ✅ 符合规范 |
| `AdjFactorService` | 1 项 `symbols`(symbols_list, 非必) | ✅ 符合规范 |
| `DailyKlineService` | 3 项 | ✅ 符合规范 |
| `NameChangeService` | `[]` | ✅ 符合规范 |

> 已声明 service 字段命名/类型符合 2.3 节规范，**不需修改**；本次只需要补全其他 24 个 service。

---

## 三、动作 B：抽出 `manage/` 模块

### 3.1 新增 3 个文件

#### 3.1.1 `application/service/manage/catalog_service.py`

```python
"""manage/catalog_service — catalog 业务逻辑

从 collect 模块的 5 个 facet 下的 28 个 service class 反射出元数据，
提供给前端的 GET /collect/services 端点。
"""
from __future__ import annotations

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.config.settings import get_settings


# ═══════════════════════════════════════════════════════════════════════
# 导入 28 个 service class（按 facet 分组）
# ═══════════════════════════════════════════════════════════════════════
from contexts.collect.application.service.tech import (
    DailyKlineService, MinuteKlineService, AdjFactorService,
    SuspendService, NameChangeService,
)
from contexts.collect.application.service.capital import (
    MoneyflowService, MoneyflowHsgtService, TopListService, TopInstService,
    BlockTradeService, MarginService, HsgtTop10Service, LimitListService,
    HolderNumberService,
)
from contexts.collect.application.service.fundamental import (
    DailyBasicService, FinIncomeService, Top10HoldersService,
    Top10FloatHoldersService, DividendService, StockBasicService,
    StockConceptsService, ConceptListService, ConceptMembersService,
    ConceptIndexDailyService, ConceptMinuteService, ConceptSnapshotService,
)
from contexts.collect.application.service.news import NewsService
from contexts.collect.application.service.sentiment import SentimentService


# catalog 中隐藏（前端不展示）
_HIDDEN_SERVICES: frozenset[str] = frozenset({
    "sentiment",  # 暂无 fetcher（空壳）
})

# 实时查询 service（只 get()，无 collect() 入库）
_REAL_TIME_ONLY: frozenset[str] = frozenset({
    "minute_kline",      # 分K线
    "concept_minute",    # 概念分时
    "concept_snapshot",  # 概念快照
})


class CatalogService:
    """catalog 业务：service class 列表 → 元数据 dict list"""

    def __init__(self, services: tuple[type, ...] | None = None) -> None:
        # 注入式：测试时可传入假 service 列表
        self._services = services or self._default_services()
        self._api_prefix = get_settings().API_V1_PREFIX  # "/api"
        self._cls_by_name: dict[str, type] = {
            cls.name: cls for cls in self._services
        }
        self._items: list[dict[str, Any]] = [
            self._to_item(cls) for cls in self._services
        ]
        self._items.sort(key=lambda x: (x["facet"], x["sub_facet"], x["name"]))

    @staticmethod
    def _default_services() -> tuple[type, ...]:
        """默认 28 个 service class 列表"""
        return (
            # tech 5
            DailyKlineService, MinuteKlineService, AdjFactorService,
            SuspendService, NameChangeService,
            # capital 9
            MoneyflowService, MoneyflowHsgtService, TopListService, TopInstService,
            BlockTradeService, MarginService, HsgtTop10Service, LimitListService,
            HolderNumberService,
            # fundamental 12
            DailyBasicService, FinIncomeService, Top10HoldersService,
            Top10FloatHoldersService, DividendService, StockBasicService,
            StockConceptsService, ConceptListService, ConceptMembersService,
            ConceptIndexDailyService, ConceptMinuteService, ConceptSnapshotService,
            # news 1
            NewsService,
            # sentiment 1
            SentimentService,
        )

    def list(self) -> list[dict[str, Any]]:
        """返回过滤后的 catalog（去掉 _HIDDEN_SERVICES）"""
        return [it for it in self._items if it["name"] not in _HIDDEN_SERVICES]

    def get(self, name: str) -> dict[str, Any] | None:
        for it in self._items:
            if it["name"] == name:
                if it["name"] in _HIDDEN_SERVICES:
                    return None
                return it
        return None

    def get_class(self, name: str) -> type | None:
        return self._cls_by_name.get(name)

    def _to_item(self, cls: type) -> dict[str, Any]:
        """service class → catalog item dict"""
        name = cls.name
        default_params = dict(getattr(cls, "DEFAULT_PARAMS", {}) or {})
        facet = getattr(cls, "facet", "") or ""
        has_get = hasattr(cls, "get") and callable(getattr(cls, "get", None))

        # kind 决定：realtime / both / collect
        if name in _REAL_TIME_ONLY:
            kind = "realtime"
        elif has_get:
            kind = "both"
        else:
            kind = "collect"

        # 优先用 service 自己的 UI_SCHEMA（动作 A 的成果）
        ui_schema = list(getattr(cls, "UI_SCHEMA", []) or [])

        return {
            "name": name,
            "facet": facet,
            "sub_facet": getattr(cls, "sub_facet", ""),
            "label": getattr(cls, "label", "") or name,
            "description": getattr(cls, "description", ""),
            "default_params": default_params,
            "param_schema": ui_schema,
            "rate_limit": getattr(cls, "RATE_LIMIT", None),
            "concurrency": int(getattr(cls, "CONCURRENCY", 1) or 1),
            "supports_query": has_get,
            "kind": kind,
            # 实际可调用的 POST 路径
            "path": f"{self._api_prefix}/collect/{facet}/{name}",
            # 实时查询（仅 has_get 时使用）
            "query_path": f"{self._api_prefix}/collect/query/{name}" if has_get else None,
        }


__all__ = ["CatalogService"]
```

#### 3.1.2 `interface/manage/catalog_handler.py`

```python
"""manage/catalog_handler — catalog 端点的 HTTP handler

提供：
  - GET /collect/services     28 service 元数据 catalog
  - GET /collect/query/{name} 实时查询 service.get()
"""
from __future__ import annotations

import json as _json
from typing import Any

from fastapi import APIRouter, HTTPException

from shared.interface import _response as R
from contexts.collect.application.service.manage import CatalogService

router = APIRouter(prefix="/collect", tags=["采集-管理面"])
_svc = CatalogService()


@router.get(
    "/services",
    summary="28 service 元数据 catalog（前端左侧目录树数据源）",
    response_description="{ total, items: [...] }",
)
async def list_services() -> dict[str, Any]:
    """列出全部 service 的元数据

    响应 data: { total, items: [{name, facet, sub_facet, label, description,
                                 default_params, param_schema, rate_limit,
                                 concurrency, supports_query, kind, path, query_path}, ...] }
    """
    items = _svc.list()
    return R.ok({"total": len(items), "items": items})


@router.get(
    "/query/{service_name}",
    summary="实时查询 service.get()",
    response_description="list[dict]（service 决定）",
)
async def query_service(
    service_name: str,
    params: str = "",  # JSON-encoded kwargs；留空表示无参数
) -> dict[str, Any]:
    """对 supports_query=true 的 service 调 get(**kwargs)

    入参用 query string `params=<JSON>`，例如：
        ?params={"symbol":"000001","interval":"5","days":1}
    """
    meta = _svc.get(service_name)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"service {service_name!r} 不存在")
    if not meta.get("supports_query"):
        raise HTTPException(
            status_code=400,
            detail=f"service {service_name!r} 不支持实时查询（supports_query=false）",
        )

    if params.strip():
        try:
            kwargs = _json.loads(params)
        except _json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"params 不是合法 JSON: {e}")
        if not isinstance(kwargs, dict):
            raise HTTPException(status_code=400, detail="params 必须是 JSON object")
    else:
        kwargs = {}

    cls = _svc.get_class(service_name)
    instance = cls()  # 无状态 default construct
    try:
        result = await instance.get(**kwargs)
    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {e}")
    return R.ok(result)


__all__ = ["router"]
```

#### 3.1.3 `interface/manage/router.py`

```python
"""manage/router — 管理面所有 handler 的总装（APIRouter 聚合）

当前只挂 catalog_handler；未来可加：
  - run_log_handler     GET /collect/runs        采集运行历史
  - schedule_handler    GET /collect/schedules   调度任务列表
  - health_handler      GET /collect/health      采集健康度
"""
from __future__ import annotations

from fastapi import APIRouter

from contexts.collect.interface.manage.catalog_handler import router as catalog_router

manage_router = APIRouter()
manage_router.include_router(catalog_router)


__all__ = ["manage_router"]
```

### 3.2 修改 `router_compat.py`

#### 3.2.1 改造前（line 48-49）

```python
# ── collect 上下文：28 service ↔ 28 route（按 5 个基本面分目录）──
# URL 风格：/api/collect/{facet}/{service_name}
# /api/collect/services
# /api/collect/query/{name}
from contexts.collect.interface.router import (
    catalog_router, facet_routers,
)
```

#### 3.2.2 改造后

```python
# ── collect 上下文：5 个 facet router + manage_router ──
# /api/collect/manage/services
# /api/collect/manage/query/{name}
# /api/collect/{facet}/{service_name}
from contexts.collect.interface.manage.router import manage_router
from contexts.collect.interface.route.tech import router as collect_tech_router
from contexts.collect.interface.route.capital import router as collect_capital_router
from contexts.collect.interface.route.fundamental import router as collect_fundamental_router
from contexts.collect.interface.route.news import router as collect_news_router
from contexts.collect.interface.route.sentiment import router as collect_sentiment_router
```

#### 3.2.3 改造前（line 79-82）

```python
# collect（28 service ↔ 28 route + catalog + query，分开挂避免 prefix 嵌套问题）
for facet_router in facet_routers:
    api_router.include_router(facet_router)
api_router.include_router(catalog_router)
```

#### 3.2.4 改造后

```python
# collect（5 个 facet + 1 个 manage，与 market 上下文结构对齐）
api_router.include_router(manage_router)
api_router.include_router(collect_tech_router)
api_router.include_router(collect_capital_router)
api_router.include_router(collect_fundamental_router)
api_router.include_router(collect_news_router)
api_router.include_router(collect_sentiment_router)
```

### 3.3 URL 变化对照

| 路径 | 改造前 | 改造后 |
|---|---|---|
| catalog 列表 | `GET /api/collect/services` | `GET /api/collect/manage/services` ⚠️ URL 变化 |
| 实时查询 | `GET /api/collect/query/{name}` | `GET /api/collect/manage/query/{name}` ⚠️ URL 变化 |
| 业务面 5 个 facet | `/api/collect/{facet}/{name}` | `/api/collect/{facet}/{name}` ✅ 不变 |

> **决策点 D1**：是否要保持旧 URL 不变（**推荐 A**）。
> | 选项 | 做法 | 代价 |
> |---|---|---|
> | **A：保持不变（推荐）** | `manage_router` 改用 `prefix="/collect"`（跟原 `catalog_router` 一致），不挂 `/manage` 子路径 | 前端零改动；URL 与当前一致 |
> | **B：改为 `/collect/manage/*`** | manage_router 用 `prefix="/collect/manage"` | URL 更规范；**前端需改 `useCatalog.ts:51` 的 listServicesCached 调用** |
>
> 本方案**默认采用 A**——保持 URL 不变；评审时如有偏好选 B，文档后续修订。

### 3.4 整文件删除 `interface/router.py`

`interface/router.py` 全部 329 行删除（含 `_build_catalog` / `_infer_param_ui` / `_derive_param_schema` / `_build_catalog` 调用 / `catalog_router` / `list_services_endpoint` / `query_service_endpoint` 等所有内容）。

---

## 四、为什么 `manage_router` 内部用嵌套 include_router 而不是直接平铺

```python
# interface/manage/router.py
manage_router = APIRouter()
manage_router.include_router(catalog_router)
```

| 现状平铺 | 重构后嵌套 |
|---|---|
| `router_compat.py` 直接 `include_router(catalog_handler.router)` + `include_router(其他_handler.router)` | `router_compat.py` 只 `include_router(manage_router)`，manage 内部聚合多个 handler |

**为什么用嵌套**：
1. **未来扩展性**——加 `run_log_handler` / `schedule_handler` 时，`router_compat.py` 不动，只在 `manage/router.py` 加一行 `include_router`
2. **manage 域统一 prefix**——所有管理面 endpoint 在 `manage/router.py` 里加 `prefix="/collect"`，handler 内部不再写 prefix
3. **未来若拆出独立 service（如 `run_log`）**，`router_compat.py` 仍然只挂一个 `manage_router`

---

## 五、改动文件清单

### 5.1 新增文件（4 个）

| 文件 | 行数预估 | 职责 |
|---|---|---|
| `application/service/manage/__init__.py` | ~5 | re-export `CatalogService` |
| `application/service/manage/catalog_service.py` | ~130 | 反射 28 个 service class → catalog item |
| `interface/manage/__init__.py` | ~5 | re-export `manage_router` |
| `interface/manage/router.py` | ~15 | manage 域 APIRouter 聚合 |
| `interface/manage/catalog_handler.py` | ~80 | 2 个 endpoint：`/services` + `/query/{name}` |

### 5.2 删除文件（1 个）

| 文件 | 删除原因 |
|---|---|
| `interface/router.py`（329 行） | 业务归业务（5 个 facet router 已存在），管理归 manage/（3.1 已搬） |

### 5.3 修改文件（1 + 28 = 29 个）

| 文件 | 改动量 |
|---|---|
| `shared/interface/router_compat.py` | 替换 5 行 import + 替换 3 行 include_router |
| `application/service/tech/adj_factor_service.py` | （可能不动，已有 UI_SCHEMA） |
| `application/service/tech/suspend_service.py` | （可能不动，已有 UI_SCHEMA） |
| `application/service/tech/daily_kline_service.py` | （可能不动，已有 UI_SCHEMA） |
| `application/service/tech/minute_kline_service.py` | 补 `UI_SCHEMA`（如未声明） |
| `application/service/tech/name_change_service.py` | （已有 `UI_SCHEMA = []`） |
| `application/service/capital/*.py` × 9 | 补 `UI_SCHEMA` |
| `application/service/fundamental/*.py` × 12 | 补 `UI_SCHEMA` |
| `application/service/news/news_service.py` | 补 `UI_SCHEMA` |
| `application/service/sentiment/sentiment_service.py` | 补 `UI_SCHEMA = []`（标记为隐藏） |

### 5.4 不改动文件

- `interface/route/{5 个 facet}/router.py`：5 个业务面 router 已经是"端点"形态
- `infrastructure/di/collect_service.py`、各 `*_service.py`、各 `*_repo.py`：本次不涉及
- `infrastructure/fetcher/**`：本次不涉及

---

## 六、UI_SCHEMA 字段补充的 28 个 service 改造步骤

> **本节是步骤拆分**，方便分批评审和分批 commit。

### 6.1 第一批：tech 5 个（已多数完成）

| service | 当前 `UI_SCHEMA` | 改动 |
|---|---|---|
| `DailyKlineService` | ✅ 3 项已声明 | 无 |
| `MinuteKlineService` | 需补 | 补 `symbol`(symbol_str) + `interval`(interval_kline) + `days`(days_int) |
| `AdjFactorService` | ✅ 1 项已声明 | 无 |
| `SuspendService` | ✅ 1 项已声明 | 无 |
| `NameChangeService` | ✅ `[]` 已声明 | 无 |

### 6.2 第二批：capital 9 个

每个 service 补 1 项 `trade_date`(date_str, 非必)，其中 `HolderNumberService` 改为 `ts_code`(ts_code_str, 非必)。

### 6.3 第三批：fundamental 12 个

每个 service 按 2.4 节草案补 0~2 项。

### 6.4 第四批：news 1 个 + sentiment 1 个

- `NewsService` 补 3 项：`start_date` + `end_date` + `src`
- `SentimentService` 补 `UI_SCHEMA = []`（标记空壳，catalog 自动隐藏）

---

## 七、验收清单

### 7.1 静态验证

```bash
# 1. 28 个 service 全部有 UI_SCHEMA（哪怕是 []）
grep -L "UI_SCHEMA" backend/src/contexts/collect/application/service/**/*.py
# 期望：无输出

# 2. 28 个 service 的 UI_SCHEMA 都是 list 类型
grep -A 1 "UI_SCHEMA" backend/src/contexts/collect/application/service/**/*.py | grep -E "= \[" | wc -l
# 期望：28

# 3. 整文件删除后，interface/router.py 不存在
test ! -f backend/src/contexts/collect/interface/router.py && echo "已删除"

# 4. 没有任何地方还从 interface/router import
grep -r "from contexts.collect.interface.router" backend/src/
grep -r "from contexts.collect.interface import router" backend/src/
# 期望：无任何结果

# 5. router_compat.py 改用新 import
grep "from contexts.collect.interface.manage" backend/src/shared/interface/router_compat.py
grep "from contexts.collect.interface.route" backend/src/shared/interface/router_compat.py
# 期望：1 + 5 行

# 6. manage_router 被 router_compat.py 挂载
grep "include_router(manage_router)" backend/src/shared/interface/router_compat.py
# 期望：1 行
```

### 7.2 HTTP 验证

```bash
# 1. catalog 端点（URL 与改造前一致）
curl -s http://localhost:8000/api/collect/services | jq '.data.total'
# 期望：27（28 - 1 隐藏 sentiment）

# 2. 随机抽 1 个 service 检查 param_schema 不再是 _infer 推导出来的"粗糙"形态
curl -s http://localhost:8000/api/collect/services | jq '.data.items[] | select(.name=="suspend") | .param_schema'
# 期望：[{"key":"trade_date","ui":"date_str","label":"交易日期","required":true,...}]

# 3. 实时查询端点
curl -s "http://localhost:8000/api/collect/query/daily_kline?params=%7B%22symbol%22%3A%22000001%22%2C%22limit%22%3A5%7D" | jq
# 期望：返回 list[dict]，前 5 条 daily kline

# 4. 业务面 5 个 facet endpoint 全部 200
for f in tech capital fundamental news sentiment; do
  curl -s -o /dev/null -w "%{http_code} /api/collect/$f/daily_kline\n" -X POST http://localhost:8000/api/collect/$f/daily_kline
done
# 期望：200 200 200 200 200（或 4xx if 不允许 GET/POST）
```

### 7.3 前端回归

```bash
# 前端 useCatalog.ts 调 /api/collect/services 应正常返回 27 个 item
# 左侧目录树（按 facet 分组）正常渲染
# 每个 service 的 param_schema 在 CollectActionCard 控件上正常显示
```

---

## 八、改造前后对比

| 维度 | 改造前 | 改造后 |
|---|---|---|
| **`interface/router.py`** | 329 行，承担 3 职责 | 整文件删除 |
| **catalog 数据源** | `_build_catalog()` 硬编码 28 个 class + `_infer_param_ui` 推导 | `CatalogService` 从 `tech/capital/.../__init__.py` 自动收集；`UI_SCHEMA` 来自 service class |
| **catalog URL** | `/api/collect/services` | `/api/collect/services` ✅ 不变（默认 A 方案） |
| **UI 字段类型** | `_infer_param_ui` 推导（看 key 名后缀、看 value 类型） | service 显式声明 `ui` 控件 |
| **新增 service 改动面** | 2 个文件（service + `interface/router.py` 列表） | 1 个文件（service 自带 `UI_SCHEMA`） |
| **`interface/manage/` 子模块** | 不存在 | ✅ 存在（catalog + 未来 runs/schedules） |
| **catalog 业务与 HTTP 解耦** | ❌ 揉在 router.py | ✅ `application/service/manage/catalog_service.py` 业务 + `interface/manage/catalog_handler.py` 协议 |
| **`router_compat.py` 挂载** | `for facet_router in facet_routers: include_router(...)` + `include_router(catalog_router)` | 6 个 `include_router` 显式调用（与 market 一致） |

---

## 九、风险与回退

### 9.1 风险

| 风险 | 概率 | 缓解 |
|---|---|---|
| URL 变化（如果选 B 方案）前端没改导致 404 | 中 | 默认 A 方案保持 URL 不变；如选 B 需同步前端 |
| 24 个 service 的 `UI_SCHEMA` 字段草案与实际 service 行为不匹配 | 中 | 草案按"现有 key + 现有类型"推导；落地时按真实 DEFAULT_PARAMS 校对 |
| `manage_router` 嵌套 include_router 增加一跳 | 低 | 性能无影响（仅启动期注册时一次性解析） |
| 删除 `interface/router.py` 后有未发现的 import | 低 | grep 验证（7.1.4） |
| `CatalogService.__init__` 启动时 import 28 个 service 慢 | 低 | import 在 application 层一次性触发；与改造前 `_build_catalog()` 触发 import 同时机 |

### 9.2 回退策略

分阶段 commit，便于单步回退：

1. **步骤 1**：28 个 service 补 `UI_SCHEMA`（不动其他文件）→ 验证 `param_schema` 字段更精确
2. **步骤 2**：新增 `manage/` 3 个文件 + `application/service/manage/catalog_service.py` → 验证 import 不报错
3. **步骤 3**：改 `router_compat.py` 改 import + 改 include_router → 验证 28 endpoint 仍 200
4. **步骤 4**：删除 `interface/router.py` → 验证 28 endpoint + catalog + query 仍 200

任一步失败可单独回退到上一步。

---

## 十、与项目既有规范的对应

| 规范来源 | 对应本方案 |
|---|---|
| DDD 分层（`application/` vs `interface/`） | catalog 业务归 `application/service/manage/`；HTTP 协议归 `interface/manage/` |
| `market` 上下文的 `interface/` 简洁性 | collect 删 `interface/router.py`，与 market 同一模式 |
| `application/service/{facet}/__init__.py` re-export 28 个 service | `CatalogService._default_services()` 复用同样的 import 路径 |
| `_HIDDEN_SERVICES` / `_REAL_TIME_ONLY` 集中常量 | 提升为 `manage/catalog_service.py` 模块级常量（与原 router.py 同语义） |

---

## 十一、下一步（可选优化）

| 优化项 | 说明 | 优先级 |
|---|---|---|
| **`run_log` 集成** | `manage/run_log_handler.py` 暴露 `GET /collect/manage/runs`（采集运行历史） | 中 |
| **`schedule` 集成** | `manage/schedule_handler.py` 暴露 `GET /collect/manage/schedules`（调度任务） | 中 |
| **`health` 集成** | `manage/health_handler.py` 暴露 `GET /collect/manage/health`（采集健康度） | 低 |
| **`UI_SCHEMA` 校验工具** | 启动时 assert `UI_SCHEMA` 字段符合规范（`key` 唯一、`ui` 在白名单内） | 低 |
| **catalog 缓存** | 28 个 service 元数据启动期反射一次 → 内存缓存（避免每次请求都遍历） | 低（当前规模无需） |

---

**总结**：

- **动作 A**：每个 service 声明 `UI_SCHEMA` class attribute（业务字段归属 service），24 个 service 待补。
- **动作 B**：抽 `interface/manage/` 子模块，catalog 业务归 `application/service/manage/catalog_service.py`，HTTP handler 归 `interface/manage/catalog_handler.py`；`interface/router.py` 整文件删除。
- **统一原则**：catalog 业务归属 application 层，HTTP 协议归属 interface 层，service 自己声明 UI 元数据；`router_compat.py` 与 `market` 上下文结构对齐。
- **URL 兼容**：默认保持 `/api/collect/services` 和 `/api/collect/query/{name}` 不变（评审时如选 B 改为 `/collect/manage/*`，需同步前端）。
