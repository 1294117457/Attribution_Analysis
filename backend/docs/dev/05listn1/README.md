# 股票列表 N+1 优化 — 统一设计文档

> 本目录整合 `backend/docs/PlantUML/StockInfo/02-modification.md`（N+1 修复）
> 与 `backend/docs/PlantUML/StockInfo/03-panel-compose-design.md`（类重构），
> 消除两份设计在命名、字段、分页上的不一致，形成统一的实施方案。
>
> 文档版本：v1  ·  日期：2026-09-24  ·  配套 UML：`01-class.puml` / `02-panel-compose.puml`

---

## 一、问题描述

### 1.1 现象

`StockInfoList.vue` 打开后端日志显示典型的 N+1 请求：

```
GET /api/v1/stocks/?page=1&page_size=20&list_status=L           200  ← 1 次：股票列表
GET /api/v1/stocks/meta                                          200  ← 1 次：筛选项
GET /api/v1/pools?limit=100                                      200  ← 1 次：池列表（但未用）
GET /api/v1/pools/by-symbol/000001                               200  ┐
GET /api/v1/pools/by-symbol/000002                               200  │
...                                                              ..  │ 20 次：每个 symbol 反查
GET /api/v1/pools/by-symbol/000029                               200  ┘
```

单页 **23 个 HTTP 请求**，其中 **20 次反向查询** 完全可以合并。

### 1.2 根因

```
frontend/src/views/stock-info/StockInfoList.vue
  loadAllStockPools()
    → stocks.value.map(symbol => poolStore.findPoolsBySymbol(symbol))
      → GET /pools/by-symbol/{symbol}（每 symbol 一次）
```

`pools` 属于"关系数据"，在列表场景下应随股票列表**一起下发**，而不是前端逐条反向查询。

### 1.3 量化影响

| 指标 | 现状 | 优化后 |
|------|------|--------|
| 单页 HTTP 请求数 | 23 | 3（列表 + meta + 批量池） |
| 单页 DB 查询数 | 23（1 列表 + 20 反向 + 2 辅助） | 3（1 列表 + 1 批量池 + 1 辅助） |
| 翻页 / 筛选 / 重进页面 | 重发 20 次 by-symbol | 不再额外请求 |
| 总后端 QPS（100 用户，5 页/分钟） | **11,500** | **1,500** |

---

## 二、统一设计决策

两份原始设计（`02-modification` / `03-panel-compose-design`）存在四处不一致，以下是统一结论：

| 议题 | 原设计 A（02-modification） | 原设计 B（03-panel-compose） | 统一决策 |
|------|--------------------------|---------------------------|---------|
| `PoolMembershipVO` 放置 | `application/dto/stock.py`（新建） | 复用 `PoolVO`，不新建 | 统一放在 `application/dto/pool.py`，字段 `pool_id / name / pool_type / joined_at` |
| `PoolMembershipVO` 字段 | `pool_id / name / pool_type` | 不建 | 统一为 `pool_id / name / pool_type / joined_at` |
| `Page[T]` 分页字段 | `list / total / pageNum / pageSize / pages` | 无泛型 | 统一用 `items / total / page / page_size / pages`（与前端 `PaginatedResponse<T>` 对齐） |
| `StockPanelRow` 归属 | `domain/stock_info/value_objects.py` | `domain/panel/`（新建目录） | 统一用 `domain/panel/`，避免跨域值对象归属 stock_info 造成歧义 |

### 2.1 统一 DTO / 值对象一览

```
application/dto/page.py              Page[T]                          ← 通用分页容器，字段 items/total/page/page_size/pages
application/dto/pool.py              PoolMembershipVO (pool_id/name/pool_type/joined_at) ← 池成员关系 DTO
application/dto/panel.py             StockPanelItemVO / StockPanelListVO ← 面板列表 DTO
domain/panel/value_objects.py        StockPanelRow (frozen)            ← 4 表组合行，领域层
domain/panel/repository.py           StockPanelComposeRepository        ← 领域层 Protocol
domain/stock_pool/value_objects.py  StockPoolBrief                    ← 保留，设计文档已定义但未实施
```

---

## 三、实施路径（分两阶段）

> **阶段一**：最小侵入修复 N+1，在现有 `StockAppService.query_stocks()` 上增加 `with_pools` 参数。
> **阶段二**：类重构，新建 `domain/panel/` + `StockPanelComposeRepository`，将 4 表 JOIN SQL 迁移至独立仓储。

两阶段可独立实施，阶段一是阶段二的前置条件（先修 N+1，再重构）。

---

## 四、阶段一：N+1 修复

### 4.1 不改动的部分

- 数据库 / ORM 模型（`stock_infos` / `stock_pools` / `stock_pool_members`）不变
- 路由 `GET /pools/by-symbol/{symbol}` 保留（详情页 / 其他场景继续用）

### 4.2 新增 DTO

#### `application/dto/pool.py` 新增

```python
class PoolMembershipVO(BaseModel):
    """池成员关系 DTO（列表 / 详情通用）

    统一放置于 pool DTO 模块，字段对齐前后端命名规范。
    """
    pool_id: int
    name: str
    pool_type: str
    joined_at: Optional[str] = None
```

#### `application/dto/stock.py` 修改

```python
# ── 新增字段（StockQueryItemResponse） ──────────────────────────
class StockQueryItemResponse(BaseModel):
    # ... 现有字段不变 ...

    # 🆕 新增：所属操作池（with_pools=True 时填充）
    pools: list[PoolMembershipVO] = Field(
        default_factory=list,
        description="所属操作池列表",
    )

# ── 新增请求参数（StockQueryRequest） ──────────────────────────
class StockQueryRequest(BaseModel):
    # ... 现有字段不变 ...
    with_pools: bool = False  # 🆕 是否附带池信息
```

### 4.3 新增仓储方法

#### `domain/stock_pool/repository.py` Protocol 新增

```python
async def list_membership_by_symbols(
    self, symbols: list[str]
) -> dict[str, list[PoolMembershipVO]]:
    """按 symbols 批量查询所属池（不含 archived 池）

    返回 symbol -> PoolMembershipVO[] 的映射。
    未出现在 dict key 中的 symbol 表示未加入任何池。
    """
    ...
```

#### `infrastructure/repositories/pool_repository.py` 实现

```python
async def list_membership_by_symbols(
    self, symbols: list[str]
) -> dict[str, list[PoolMembershipVO]]:
    if not symbols:
        return {}

    stmt = (
        select(
            StockPoolMemberDB.symbol,
            StockPoolDB.id,
            StockPoolDB.name,
            StockPoolDB.pool_type,
        )
        .join(StockPoolDB, StockPoolDB.id == StockPoolMemberDB.pool_id)
        .where(
            and_(
                StockPoolMemberDB.symbol.in_(symbols),
                StockPoolDB.is_archived == False,
            )
        )
        .order_by(StockPoolDB.is_default.desc(), StockPoolDB.updated_at.desc())
    )
    result = await self._session.execute(stmt)
    rows = result.all()

    out: dict[str, list[PoolMembershipVO]] = {s: [] for s in symbols}
    for row in rows:
        out[row.symbol].append(
            PoolMembershipVO(
                pool_id=row.id,
                name=row.name,
                pool_type=row.pool_type,
            )
        )
    return out
```

**性能**：单次 SQL，`symbol IN (:symbols)` 可命中 `ix_stock_pool_members_symbol` 索引，symbols 数量上限 ≤ `page_size`（500）。

### 4.4 修改应用服务

#### `application/stock_service.py` 修改

```python
from application.dto.pool import PoolMembershipVO  # 🆕 导入

class StockAppService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo: StockInfoRepository = StockRepoImpl(session)
        self._pool_repo = StockPoolRepoImpl(session)  # 🆕 注入

    async def query_stocks(
        self, request: StockQueryRequest
    ) -> StockQueryResponse:
        # 1) 拿股票列表（不变）
        rows, total = await self._repo.list_with_kline_stats_paginated(
            q=request.q,
            industry=request.industry,
            market=request.market,
            exchange=request.exchange,
            is_hs=request.is_hs,
            list_status=request.list_status,
            exclude_st=request.exclude_st,
            min_total_mv=request.min_total_mv,
            page=request.page,
            page_size=request.page_size,
        )

        # 2) 🆕 按需批量反向查询池
        pool_map: dict[str, list[PoolMembershipVO]] = {}
        if request.with_pools and rows:
            symbols = [r["symbol"] for r in rows]
            pool_map = await self._pool_repo.list_membership_by_symbols(symbols)

        # 3) 组装响应
        items = [
            StockQueryItemResponse(
                **row,
                pools=pool_map.get(row["symbol"], []),
            )
            for row in rows
        ]
        return StockQueryResponse(
            total=total,
            page=request.page,
            page_size=request.page_size,
            items=items,
        )
```

### 4.5 修改路由

#### `route/api/v1/stock.py` 修改

```python
@router.get("/", summary="股票列表（分页 + 多维筛选）")
async def query_stocks(
    q: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    market: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    is_hs: Optional[str] = Query(None),
    list_status: Optional[str] = Query("L"),
    exclude_st: Optional[bool] = Query(None),
    min_total_mv: Optional[float] = Query(None, ge=0),
    with_pools: bool = Query(False, description="是否附带所属操作池"),  # 🆕
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    service: StockAppService = Depends(get_stock_service),
):
    request = StockQueryRequest(
        q=q, industry=industry, market=market,
        exchange=exchange, is_hs=is_hs,
        list_status=list_status, exclude_st=exclude_st,
        min_total_mv=min_total_mv,
        with_pools=with_pools,  # 🆕
        page=page, page_size=page_size,
    )
    response = await service.query_stocks(request)
    return R.ok(response.model_dump())
```

### 4.6 前端配合

#### `frontend/src/views/stock-info/api.ts` 修改

```typescript
export interface PoolMembership {
  pool_id: number
  name: string
  pool_type: string
  joined_at?: string
}

export interface StockInfo {
  // ... 现有字段 ...
  pools: PoolMembership[]  // 🆕
}

export const queryStocks = (params: StockQueryParams = {}) =>
  http.get<PaginatedResponse<StockInfo>>('/stocks/', { params }).then(unwrap)
```

#### `frontend/src/views/stock-info/StockInfoList.vue` 修改

```typescript
// 删除：symbolPoolsMap / loadAllStockPools() / poolStore.fetchPools()
// 修改：loadStocks 调用时带 with_pools=true
const data = await queryStocks({ ...params, with_pools: true })

// 修改：getStockPools 改为读 row.pools
function getStockPools(symbol: string): PoolMembership[] {
  const stock = stocks.value.find(s => s.symbol === symbol)
  return stock?.pools ?? []
}

// onMounted 不再调 poolStore.fetchPools 和 loadAllStockPools
onMounted(async () => {
  await Promise.all([loadMeta(), loadStocks()])
})
```

### 4.7 阶段一变更统计

| 层 | 文件 | 操作 | 改动量 |
|----|------|------|--------|
| DTO | `application/dto/pool.py` | 新增 `PoolMembershipVO` | ~10 行 |
| DTO | `application/dto/stock.py` | 新增 `with_pools` 参数 + `pools` 字段 | ~5 行 |
| Domain Repository | `domain/stock_pool/repository.py` | 新增 Protocol 方法 | ~10 行 |
| Infra Repository | `infrastructure/repositories/pool_repository.py` | 实现 `list_membership_by_symbols` | ~30 行 |
| App Service | `application/stock_service.py` | 注入 `pool_repo`，编排合并 | ~25 行 |
| Route | `route/api/v1/stock.py` | 新增 `with_pools` query 参数 | ~5 行 |
| Frontend API | `frontend/src/views/stock-info/api.ts` | 新增类型 + `with_pools` 参数 | ~10 行 |
| Frontend Vue | `frontend/src/views/stock-info/StockInfoList.vue` | 删除 N+1 调用，改为读 `row.pools` | ~30 行 |
| **合计** | — | — | **~125 行** |

---

## 五、阶段二：类重构（面板组合仓储）

> 将 4 表 JOIN SQL 从 `StockRepoImpl.list_with_kline_stats_paginated` 迁移至独立的
> `StockPanelComposeRepository`，解决"跨聚合根组合查询"写在 stock_info 仓储里的架构异味。

### 5.1 新增目录结构

```
domain/panel/
  __init__.py
  value_objects.py      ← StockPanelRow (frozen)
  repository.py         ← StockPanelComposeRepository (Protocol)

infrastructure/repositories/
  panel_compose_repository.py  ← StockPanelComposeRepoImpl

application/dto/
  page.py               ← Page[T]（通用分页，字段 items/total/page/page_size/pages）
  panel.py              ← StockPanelItemVO / StockPanelListVO

application/
  panel_service.py       ← StockPanelAppService
```

### 5.2 通用分页容器

#### `application/dto/page.py` 新增

```python
"""通用分页响应容器（跨模块复用）

字段命名与前端 PaginatedResponse<T> 对齐：
items / total / page / page_size / pages
"""

from typing import Generic, List, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """泛型分页容器"""
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def from_list(
        cls,
        items: List[T],
        total: int,
        page_num: int,
        page_size: int,
    ) -> "Page[T]":
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page_num,
            page_size=page_size,
            pages=pages,
        )
```

### 5.3 领域层

#### `domain/panel/value_objects.py` 新增

```python
"""StockPanel 组合行 — 4 表快照的不可变值对象"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class StockPanelRow:
    """股票列表面板行快照（4 表 JOIN 结果）

    来源：
    - stock_infos           基本字段 13 个
    - tech_kline_dailys     K 线统计 3 个（COUNT / MIN / MAX）
    - fin_daily_basics      最新一行估值 3 个（close / total_mv / pe_ttm）
    - fin_reports           最新一期净利润率 1 个（n_income / revenue * 100）

    用途：仅用于"列表面板"视图投影，不可写回任何源表。
    属于 domain/panel 上下文，不归属任何单一聚合根。
    """

    # ── 来自 stock_infos ─────────────────────────
    symbol: str
    ts_code: Optional[str]
    name: Optional[str]
    area: Optional[str]
    industry: Optional[str]
    market: Optional[str]
    exchange: Optional[str]
    list_date: Optional[str]
    list_status: Optional[str]
    is_hs: Optional[str]
    act_name: Optional[str]
    act_ent_type: Optional[str]
    total_shares: Optional[int]

    # ── 来自 tech_kline_dailys（聚合） ──────────────
    record_count: int
    kline_start: Optional[date]
    kline_end: Optional[date]

    # ── 来自 fin_daily_basics（最新一行） ─────────
    latest_close: Optional[float]
    total_mv: Optional[float]
    pe_ttm: Optional[float]

    # ── 来自 fin_reports（最新一期） ─────────────
    profit_margin: Optional[float]
```

#### `domain/panel/repository.py` 新增

```python
"""StockPanel 组合查询 — 领域层 Protocol"""

from typing import Optional, Protocol, runtime_checkable

from domain.panel.value_objects import StockPanelRow


@runtime_checkable
class StockPanelComposeRepository(Protocol):
    """列表面板专用组合仓储

    严格只服务于"列表 + 多表快照"场景，跨表 JOIN 是它的本职，
    不算越界（对比：单表 CRUD 属于各聚合根仓储）。
    """

    async def list_paginated(
        self,
        q: Optional[str] = None,
        industry: Optional[str] = None,
        market: Optional[str] = None,
        exchange: Optional[str] = None,
        is_hs: Optional[str] = None,
        list_status: Optional[str] = None,
        exclude_st: Optional[bool] = None,
        min_total_mv: Optional[float] = None,
        with_pools: bool = False,          # 🆕 阶段一成果
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StockPanelRow], int]:
        """分页 + 多维筛选 + 4 表快照，返回 (rows, total)"""
        ...

    async def list_membership_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list["PoolMembershipVO"]]:  # 前向引用
        """批量反向查询池（阶段一成果）"""
        ...
```

### 5.4 基础设施层

#### `infrastructure/repositories/panel_compose_repository.py` 新增

将 `StockRepoImpl.list_with_kline_stats_paginated` 中的 SQL 整体迁移至此，
同时内嵌 `list_membership_by_symbols`（或委托给 `PoolRepoImpl`，见实现选择）。

### 5.5 DTO 层

#### `application/dto/panel.py` 新增

```python
"""StockPanel 列表 DTO"""

from __future__ import annotations
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from application.dto.page import Page
from application.dto.pool import PoolMembershipVO


class StockPanelItemVO(BaseModel):
    """列表面板单行 VO（与 StockPanelRow 字段 1:1 对齐）"""

    # stock_infos
    symbol: str
    ts_code: Optional[str] = None
    name: Optional[str] = None
    area: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    exchange: Optional[str] = None
    list_date: Optional[str] = None
    list_status: Optional[str] = None
    is_hs: Optional[str] = None
    act_name: Optional[str] = None
    act_ent_type: Optional[str] = None
    total_shares: Optional[int] = None

    # tech_kline_dailys
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end: Optional[date] = None

    # fin_daily_basics
    latest_close: Optional[float] = None
    total_mv: Optional[float] = None
    pe_ttm: Optional[float] = None

    # fin_reports
    profit_margin: Optional[float] = None

    # 🆕 所属池（with_pools=True 时填充）
    pools: list[PoolMembershipVO] = Field(default_factory=list)


class StockPanelListVO(Page[StockPanelItemVO]):
    """StockPanel 列表响应（分页 + 4 表快照 + 池信息）

    继承 Page[T] 的 items/total/page/page_size/pages，
    字段命名与前端 PaginatedResponse 对齐。
    """
    pass
```

### 5.6 应用服务层

#### `application/panel_service.py` 新增

```python
"""StockPanel 应用服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.panel import (
    StockPanelItemVO,
    StockPanelListVO,
    StockPanelQueryRequest,
)
from application.dto.page import Page
from domain.panel.repository import StockPanelComposeRepository
from domain.panel.value_objects import StockPanelRow


class StockPanelAppService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo: StockPanelComposeRepository = StockPanelComposeRepoImpl(session)

    async def query_panels(
        self, req: StockPanelQueryRequest
    ) -> StockPanelListVO:
        rows, total = await self._repo.list_paginated(
            q=req.q,
            industry=req.industry,
            market=req.market,
            exchange=req.exchange,
            is_hs=req.is_hs,
            list_status=req.list_status,
            exclude_st=req.exclude_st,
            min_total_mv=req.min_total_mv,
            with_pools=req.with_pools,
            page=req.page,
            page_size=req.page_size,
        )

        items = [_to_vo(r) for r in rows]
        return StockPanelListVO.from_list(items, total, req.page, req.page_size)


def _to_vo(r: StockPanelRow) -> StockPanelItemVO:
    return StockPanelItemVO(
        symbol=r.symbol,
        ts_code=r.ts_code,
        name=r.name,
        area=r.area,
        industry=r.industry,
        market=r.market,
        exchange=r.exchange,
        list_date=r.list_date,
        list_status=r.list_status,
        is_hs=r.is_hs,
        act_name=r.act_name,
        act_ent_type=r.act_ent_type,
        total_shares=r.total_shares,
        record_count=r.record_count,
        kline_start=r.kline_start,
        kline_end=r.kline_end,
        latest_close=r.latest_close,
        total_mv=r.total_mv,
        pe_ttm=r.pe_ttm,
        profit_margin=round(r.profit_margin, 2) if r.profit_margin is not None else None,
    )
```

### 5.7 路由层

#### `route/api/v1/panel.py` 新增

```python
"""StockPanel 面板列表路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.panel_service import StockPanelAppService
from application.dto.panel import StockPanelListVO
from domain.panel.value_objects import StockPanelRow
from infrastructure.database.connection import get_db
from route.schemas.response import ok

router = APIRouter(prefix="/api/v1", tags=["面板"])


def get_panel_service(db: AsyncSession = Depends(get_db)) -> StockPanelAppService:
    return StockPanelAppService(session=db)


@router.get(
    "/stock-panel/",
    summary="股票面板列表（分页 + 多维筛选 + 4 表快照）",
    response_model=StockPanelListVO,
)
async def query_panels(
    q: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    market: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    is_hs: Optional[str] = Query(None),
    list_status: Optional[str] = Query("L"),
    exclude_st: Optional[bool] = Query(None),
    min_total_mv: Optional[float] = Query(None, ge=0),
    with_pools: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    service: StockPanelAppService = Depends(get_panel_service),
):
    result = await service.query_panels(...)
    return result  # FastAPI 直接返回 Pydantic 模型
```

### 5.8 阶段二变更统计

| 层 | 文件 | 操作 | 改动量 |
|----|------|------|--------|
| Domain | `domain/panel/__init__.py` | 🆕 | ~5 行 |
| Domain | `domain/panel/value_objects.py` | 🆕 `StockPanelRow` | ~45 行 |
| Domain | `domain/panel/repository.py` | 🆕 `StockPanelComposeRepository` Protocol | ~35 行 |
| Infra | `infrastructure/repositories/panel_compose_repository.py` | 🆕 SQL 实现 | ~130 行 |
| DTO | `application/dto/page.py` | 🆕 `Page[T]` | ~35 行 |
| DTO | `application/dto/panel.py` | 🆕 `StockPanelItemVO` / `StockPanelListVO` | ~55 行 |
| DTO | `application/dto/stock.py` | ⚰️ 删除 list_*/query_* DTO（迁移至 panel.py） | ~-80 行 |
| App | `application/panel_service.py` | 🆕 `StockPanelAppService` | ~60 行 |
| App | `application/stock_service.py` | ⚰️ 删除 `query_stocks`（迁移至 panel_service） | ~-40 行 |
| Infra | `infrastructure/repositories/stock_repository.py` | ⚰️ 删除 `list_with_kline_stats_paginated` | ~-100 行 |
| Route | `route/api/v1/panel.py` | 🆕 | ~30 行 |
| **合计** | — | — | **净增 ~325 行 / 删 ~220 行** |

---

## 六、兼容性 & 回滚

### 6.1 向后兼容（阶段一）

- `with_pools` 默认为 `false`，旧请求行为不变，`pools` 字段为空列表 `[]`
- `GET /pools/by-symbol/{symbol}` 保留，详情页 / 其他场景继续可用

### 6.2 向后兼容（阶段二）

- 阶段二完成后，`GET /stocks/` 路由可降级为"兼容旧调用方，底层委托 `StockPanelComposeRepoImpl`"
- 前端 `StockInfoList.vue` 迁移至 `GET /stock-panel/` 后，保留旧路由做 fallback

### 6.3 风险评估

| 风险 | 影响 | 缓解 |
|------|------|------|
| `IN (:symbols)` 列表过长 | 中 | `page_size ≤ 500`，SQLAlchemy 自动分批；超长场景可加截断 |
| 批量反向查询与列表查询不在同一事务 | 低 | 只读快照场景可接受；强一致性需求可包 `BEGIN READ ONLY` 事务 |
| `PoolMembershipVO` 被前端误用为完整 `Pool` | 低 | TS 类型只暴露 `pool_id/name/pool_type/joined_at`，无 color/icon 等完整字段 |

---

## 七、相关文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| **类图：N+1 修复** | `docs/PlantUML/StockInfo/01-class.puml` | 阶段一类图（with_pools 参数 + 批量反向查询），权威版本 |
| **类图：面板组合数据流** | `docs/PlantUML/StockInfo/03-panel-compose.puml` | 阶段二数据流图（4 层 + 4 表），权威版本 |
| 设计说明：面板组合 | `docs/dev/05listn1/03-panel-compose-design.md` | 阶段二详细设计（含代码骨架） |
| UML 绘制规范 | `docs/config/uml类图设计规范.md` | PlantUML 绘制规范（模板 / 颜色 / 便签 / 箭头约定） |
| 统一设计文档 | `docs/dev/05listn1/README.md` | 本文档：整合两份原始设计，消除 4 处不一致 |
| 原始设计 A（历史） | `docs/PlantUML/StockInfo/02-modification.md` | 原始 N+1 修复方案（参考） |
| 原始设计 B（历史） | `docs/PlantUML/StockInfo/03-panel-compose-design.md` | 原始面板组合方案（参考） |

> **约定**：PlantUML 文件统一放置于 `docs/PlantUML/StockInfo/`，设计文档放置于 `docs/dev/05listn1/`。两者按以上索引对应，不重复存放。
