# StockPanel 列表组合查询 — 类设计文档

> 围绕 `StockInfoList.vue` 一行数据的真实来源：横跨 **4 张表**
> (`stock_infos` + `tech_kline_dailys` + `fin_daily_basics` + `fin_reports`)
> 的组合查询 + 分页 + 批量池反向查询。
>
> 文档版本：v1 · 日期：2026-09-24
> 配套 UML（权威版本）：`docs/PlantUML/StockInfo/03-panel-compose.puml`
> 所属统一设计：`docs/dev/05listn1/README.md`

---

## 一、背景

### 1.1 一行数据的来源拆分

`StockInfoList.vue` 表格中每一条记录由 **4 张表** 共同构成：

| 表 | 行内字段个数 | 提供字段 |
|----|-----------|----------|
| **`stock_infos`**           | 13 个 | `symbol, ts_code, name, area, industry, market, exchange, list_date, list_status, is_hs, act_name, act_ent_type, total_shares` |
| **`tech_kline_dailys`**     | 3 个聚合 | `record_count`, `kline_start`, `kline_end` |
| **`fin_daily_basics`**      | 3 个最新一行 | `latest_close`, `total_mv`, `pe_ttm` |
| **`fin_reports`**           | 1 个计算 | `profit_margin = n_income / revenue * 100` |
| **`stock_pool_members` ⨝ `stock_pools`** | 0..N 个池 | `pools[]`（with_pools=True 时填充） |

### 1.2 当前实现的痛点

当前实现位于 `infrastructure/repositories/stock_repository.py::list_with_kline_stats_paginated`，
把"组合查询的 SQL"塞进 `StockInfoRepository`：

```python
# 反模式：组合查询写在单一聚合根仓储里
class StockRepoImpl:
    async def list_with_kline_stats_paginated(...):
        # 这里同时 JOIN tech_kline_dailys / fin_daily_basics / fin_reports
        ...
```

问题：

1. **越界**：4 张表分属 4 个聚合根（stock_info / kline / fin_daily_basic / fin_report），
   把它们的连接硬塞进 stock_info 仓储，破坏聚合根边界。
2. **不可复用**：以后任何"列表 + 多表快照"场景（选股器 / 仪表盘 / 排行）都要复制粘贴同样的 SQL。
3. **DTO 膨胀**：`StockQueryItemResponse` 一旦又要加 K 线 MACD 摘要，又要去改 `StockInfo` 这条线。

---

## 二、设计原则

> **让组合查询有一等公民：组合查询 ≠ 任何单一聚合根的操作，应该属于"它自己的"仓储。**

| 原则 | 落地 |
|------|------|
| 单表操作归各聚合根仓库 | `StockInfoRepository / KlineRepository / FinDailyBasicRepository / FinReportRepository` **不变**，继续按聚合根管理 |
| 多表组合查询独立成类 | 新增 `StockPanelComposeRepository`，**专门**负责"列表组合查询" |
| 组合结果用值对象封装 | 新增 `StockPanelRow`（不可变 dataclass，4 表快照组合），不污染任何聚合根 |
| 通用分页用 `Page[T]` | 字段 `items / total / page / page_size / pages`，与前端 `PaginatedResponse<T>` 对齐 |
| 池信息通过 `PoolMembershipVO` 注入 | 阶段一成果，`with_pools=True` 时填充到 `StockPanelItemVO.pools` |

---

## 三、修改清单

> 图例：🆕 新增 · ✏️ 修改 · ⚪ 不变 · ⚰️ 删除

### 3.1 持久层 ⚪

`stock_infos / tech_kline_dailys / fin_daily_basics / fin_reports / stock_pools / stock_pool_members`
六张表 + 6 个 ORM 模型 **完全不变**。

### 3.2 领域层 🆕

#### `domain/panel/__init__.py` 🆕

```python
"""面板（Panel）上下文

跨聚合根的"列表面板视图"值对象与组合仓储归此处。
不归属 stock_info / kline / fin_daily_basic / fin_report 任一聚合根。
"""
```

#### `domain/panel/value_objects.py` 🆕

```python
"""StockPanel 组合行 — 4 表快照的不可变值对象"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class StockPanelRow:
    """股票列表面板行快照（4 表 JOIN 结果）

    来源：
    - stock_infos           基础字段 13 个
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
    list_date: Optional[str]              # YYYYMMDD
    list_status: Optional[str]
    is_hs: Optional[str]
    act_name: Optional[str]
    act_ent_type: Optional[str]
    total_shares: Optional[int]

    # ── 来自 tech_kline_dailys（聚合） ──────────────
    record_count: int
    kline_start: Optional[date]
    kline_end:   Optional[date]

    # ── 来自 fin_daily_basics（最新一行） ─────────
    latest_close: Optional[float]
    total_mv:     Optional[float]
    pe_ttm:       Optional[float]

    # ── 来自 fin_reports（最新一期） ─────────────
    profit_margin: Optional[float]
```

**为什么不放在 `domain/stock_info/value_objects.py`？**
这个值对象不属于 `StockInfo` 聚合根的语义——它本质是"列表面板视图"，跨了 4 个聚合根，
硬塞进 `stock_info` 包会反向暗示这个对象属于该聚合根。新建 `domain/panel/` 目录
让跨域组合有一席之地。

#### `domain/panel/repository.py` 🆕

```python
"""StockPanel 组合查询 — 领域层 Protocol"""

from typing import Optional, Protocol, runtime_checkable

from domain.panel.value_objects import StockPanelRow


@runtime_checkable
class StockPanelComposeRepository(Protocol):
    """列表面板专用组合仓储

    严格只服务于"列表 + 多表快照"场景，不承担单表的 CRUD。
    跨表 JOIN 是它的本职，不算越界。
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
        with_pools: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StockPanelRow], int]:
        """分页 + 多维筛选 + 4 表快照，返回 (rows, total)"""
        ...
```

### 3.3 仓储实现层 🆕

#### `infrastructure/repositories/panel_compose_repository.py` 🆕

```python
"""StockPanel 组合查询 — SQLAlchemy 实现"""

from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.pool import PoolMembershipVO
from domain.panel.value_objects import StockPanelRow
from domain.panel.repository import StockPanelComposeRepository
from infrastructure.database.models.stock_info import StockInfoDB
from infrastructure.database.models.tech_kline import TechKlineDailyDB
from infrastructure.database.models.fin_daily_basic import FinDailyBasicDB
from infrastructure.database.models.fin_report import FinReportDB
from infrastructure.database.models.stock_pool import StockPoolDB
from infrastructure.database.models.stock_pool_member import StockPoolMemberDB


class StockPanelComposeRepoImpl:
    """列表面板组合仓储实现

    关键点（与当前 StockRepoImpl.list_with_kline_stats_paginated 一致）：
    - 主表 stock_infos
    - LEFT JOIN tech_kline_dailys 拿 K 线聚合
    - 通过子查询拿 fin_daily_basics 每只股票最新一行
    - 通过子查询拿 fin_reports 每只股票最新一期（report_type=1）净利润率
    - min_total_mv 走 HAVING 过滤
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_paginated(
        self, ..., with_pools: bool = False, ...
    ) -> tuple[list[StockPanelRow], int]:
        # 子查询 1：fin_daily_basics 每只股票最新一行
        latest_date_sq = (
            select(
                FinDailyBasicDB.symbol,
                func.max(FinDailyBasicDB.trade_date).label("max_date"),
            )
            .group_by(FinDailyBasicDB.symbol)
            .subquery("latest_date")
        )
        latest_basic_sq = (
            select(
                FinDailyBasicDB.symbol,
                FinDailyBasicDB.close.label("latest_close"),
                FinDailyBasicDB.total_mv,
                FinDailyBasicDB.pe_ttm,
            )
            .join(
                latest_date_sq,
                (FinDailyBasicDB.symbol == latest_date_sq.c.symbol)
                & (FinDailyBasicDB.trade_date == latest_date_sq.c.max_date),
            )
            .subquery("latest_basic")
        )

        # 子查询 2：fin_reports 每只股票最新一期（report_type=1）
        latest_report_date_sq = (
            select(
                FinReportDB.symbol,
                func.max(FinReportDB.end_date).label("max_end_date"),
            )
            .where(FinReportDB.report_type == "1")
            .group_by(FinReportDB.symbol)
            .subquery("latest_report_date")
        )
        latest_report_sq = (
            select(
                FinReportDB.symbol,
                (
                    FinReportDB.n_income
                    / func.nullif(FinReportDB.revenue, 0)
                    * 100
                ).label("profit_margin"),
            )
            .join(
                latest_report_date_sq,
                (FinReportDB.symbol == latest_report_date_sq.c.symbol)
                & (FinReportDB.end_date == latest_report_date_sq.c.max_end_date),
            )
            .subquery("latest_report")
        )

        # 主查询：4 表 JOIN
        stmt = (
            select(
                StockInfoDB.symbol,
                StockInfoDB.ts_code,
                StockInfoDB.name,
                StockInfoDB.area,
                StockInfoDB.industry,
                StockInfoDB.market,
                StockInfoDB.exchange,
                StockInfoDB.list_date,
                StockInfoDB.list_status,
                StockInfoDB.is_hs,
                StockInfoDB.act_name,
                StockInfoDB.act_ent_type,
                StockInfoDB.total_shares,
                func.count(TechKlineDailyDB.id).label("record_count"),
                func.min(TechKlineDailyDB.date).label("kline_start"),
                func.max(TechKlineDailyDB.date).label("kline_end"),
                latest_basic_sq.c.latest_close,
                latest_basic_sq.c.total_mv,
                latest_basic_sq.c.pe_ttm,
                latest_report_sq.c.profit_margin,
            )
            .outerjoin(TechKlineDailyDB, StockInfoDB.symbol == TechKlineDailyDB.symbol)
            .outerjoin(latest_basic_sq, StockInfoDB.symbol == latest_basic_sq.c.symbol)
            .outerjoin(latest_report_sq, StockInfoDB.symbol == latest_report_sq.c.symbol)
            .group_by(StockInfoDB.id, latest_basic_sq.c.latest_close, ...)
        )
        # ... 条件构造、HAVING 过滤、order/limit/offset 同当前实现

        # ORM 行 → StockPanelRow
        return [
            StockPanelRow(
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
                record_count=r.record_count or 0,
                kline_start=r.kline_start,
                kline_end=r.kline_end,
                latest_close=r.latest_close,
                total_mv=r.total_mv,
                pe_ttm=r.pe_ttm,
                profit_margin=round(r.profit_margin, 2) if r.profit_margin is not None else None,
            )
            for r in rows
        ], int(total)

    async def list_membership_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[PoolMembershipVO]]:
        """批量反向查询池（阶段一成果，从 PoolRepoImpl 平移至此）"""
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


StockPanelComposeRepoImpl.__implements_protocol__ = StockPanelComposeRepository
```

**注意**：`list_membership_by_symbols` 从 `PoolRepoImpl` 平移到 `StockPanelComposeRepoImpl`，
让"列表所需的所有数据"由一个组合仓储一次性提供，避免服务层跨仓储编排。

### 3.4 DTO 层

#### `application/dto/page.py` 🆕

通用分页响应容器，字段与前端 `PaginatedResponse<T>` 对齐：

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

#### `application/dto/pool.py` ✏️ 新增 `PoolMembershipVO`

```python
class PoolMembershipVO(BaseModel):
    """池成员关系 DTO（列表 / 详情通用）

    统一放置于 pool DTO 模块（避免在 stock / panel 模块下重复定义）。
    字段对齐前后端命名规范。
    """
    pool_id: int
    name: str
    pool_type: str
    joined_at: Optional[str] = None
```

#### `application/dto/panel.py` 🆕

```python
"""StockPanel 列表 DTO"""

from __future__ import annotations
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from application.dto.page import Page
from application.dto.pool import PoolMembershipVO


class StockPanelItemVO(BaseModel):
    """列表面板单行 VO（与 StockPanelRow 字段 1:1 + pools 字段）"""

    # ── 来自 stock_infos ─────────────────────────
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

    # ── 来自 tech_kline_dailys ────────────────────
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end:   Optional[date] = None

    # ── 来自 fin_daily_basics ────────────────────
    latest_close: Optional[float] = None
    total_mv:     Optional[float] = None
    pe_ttm:       Optional[float] = None

    # ── 来自 fin_reports ─────────────────────────
    profit_margin: Optional[float] = None

    # ── 来自 stock_pool_members ⨝ stock_pools（with_pools=True 时填充）
    pools: list[PoolMembershipVO] = Field(default_factory=list)


class StockPanelListVO(Page[StockPanelItemVO]):
    """StockPanel 列表响应（分页 + 4 表快照 + 池信息）

    继承 Page[T] 的 items/total/page/page_size/pages。
    """
    pass


class StockPanelQueryRequest(BaseModel):
    q: Optional[str] = Field(None, description="代码 / 名称 / 拼音 模糊搜索")
    industry:    Optional[str] = None
    market:      Optional[str] = None
    exchange:    Optional[str] = None
    is_hs:       Optional[str] = None
    list_status: Optional[str] = "L"
    exclude_st:  Optional[bool] = None
    min_total_mv: Optional[float] = Field(None, ge=0, description="最低总市值(万元)")
    with_pools:  bool = False
    page:        int = Field(1,  ge=1)
    page_size:   int = Field(20, ge=1, le=500)
```

#### `application/dto/stock.py` ⚰️ 删除 list_*/query_* 相关 DTO

迁移至 `panel.py`，避免重复定义。

### 3.5 应用服务层

#### `application/panel_service.py` 🆕

```python
"""StockPanel 应用服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.panel import (
    StockPanelItemVO,
    StockPanelListVO,
    StockPanelQueryRequest,
)
from application.dto.pool import PoolMembershipVO
from domain.panel.repository import StockPanelComposeRepository
from domain.panel.value_objects import StockPanelRow
from infrastructure.repositories.panel_compose_repository import (
    StockPanelComposeRepoImpl,
)


class StockPanelAppService:
    """列表面板应用服务

    职责单一：把"分页 + 多表快照 + 批量池"组合查询的结果组装为分页 VO。
    不做单表 CRUD，不做领域事件，不依赖其他应用服务。
    """

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

        # with_pools 时一次性批量反查池
        pool_map: dict[str, list[PoolMembershipVO]] = {}
        if req.with_pools and rows:
            symbols = [r.symbol for r in rows]
            pool_map = await self._repo.list_membership_by_symbols(symbols)

        items = [_to_vo(r, pool_map.get(r.symbol, [])) for r in rows]
        return StockPanelListVO.from_list(items, total, req.page, req.page_size)


def _to_vo(
    r: StockPanelRow, pools: list[PoolMembershipVO]
) -> StockPanelItemVO:
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
        profit_margin=(
            round(r.profit_margin, 2)
            if r.profit_margin is not None else None
        ),
        pools=pools,
    )
```

#### `application/stock_service.py` ⚰️ 删除 `query_stocks`

迁移至 `panel_service.py`。

### 3.6 路由层

#### `route/api/v1/panel.py` 🆕

```python
"""StockPanel 面板列表路由"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.panel_service import StockPanelAppService
from application.dto.panel import (
    StockPanelListVO,
    StockPanelQueryRequest,
)
from infrastructure.database.connection import get_db
from route.schemas.response import ok

router = APIRouter(prefix="/api/v1", tags=["面板"])


def get_panel_service(db: AsyncSession = Depends(get_db)) -> StockPanelAppService:
    return StockPanelAppService(session=db)


@router.get(
    "/stock-panel/",
    summary="股票面板列表（分页 + 多维筛选 + 4 表快照 + 池信息）",
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
    with_pools: bool = Query(False, description="是否附带所属操作池"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    service: StockPanelAppService = Depends(get_panel_service),
):
    request = StockPanelQueryRequest(
        q=q, industry=industry, market=market,
        exchange=exchange, is_hs=is_hs,
        list_status=list_status, exclude_st=exclude_st,
        min_total_mv=min_total_mv,
        with_pools=with_pools,
        page=page, page_size=page_size,
    )
    result = await service.query_panels(request)
    return ok(result.model_dump())
```

#### `route/api/v1/stock.py` ⚰️ 删除 `GET /` 路由

迁移至 `panel.py`。

> **兼容性方案**：`stock.py` 的 `GET /` 可改为薄包装，内部委托给 `StockPanelAppService.query_panels`，
> 保留旧路由直到前端迁移完成。

---

## 四、调用时序

```
前端 GET /api/v1/stock-panel/?page=1&page_size=20&with_pools=true
  └─► route/api/v1/panel.py::query_panels
        └─► StockPanelAppService.query_panels(request)
              ├─► StockPanelComposeRepoImpl.list_paginated(...)   ← 1×SQL（4 表 JOIN）
              └─► StockPanelComposeRepoImpl.list_membership_by_symbols(symbols)
                                                          ← 1×SQL（批量反向）
              └─► items = [_to_vo(r, pools) for r in rows]
              └─► StockPanelListVO.from_list(items, total, page, page_size)
```

**SQL 数量：最多 2 条**（4 表 JOIN + 批量反向），无 N+1。

---

## 五、与现有实现的兼容

### 5.1 完全迁移

| 现有 | 处置 |
|------|------|
| `StockRepoImpl.list_with_kline_stats_paginated` | ⚰️ 删除（迁移到 `StockPanelComposeRepoImpl.list_paginated`） |
| `PoolRepoImpl.list_membership_by_symbols` | ⚰️ 删除（迁移到 `StockPanelComposeRepoImpl.list_membership_by_symbols`） |
| `StockAppService.query_stocks` | ⚰️ 删除（迁移到 `StockPanelAppService.query_panels`） |
| `StockQueryRequest` / `StockQueryItemResponse` / `StockQueryResponse` | ⚰️ 删除（被 `StockPanelQueryRequest` / `StockPanelItemVO` / `StockPanelListVO` 替代） |
| `application/dto/stock.py` list_*/query_* DTO | ⚰️ 删除 |

### 5.2 不变

- 4 个原 `*_Repository`（`StockInfoRepository / KlineRepository / FinDailyBasicRepository / FinReportRepository`）
- `StockPoolRepository.find_pools_by_symbol`（单股详情继续用）
- `GET /pools/by-symbol/{symbol}` 路由
- 数据库 schema / ORM 模型

### 5.3 前端迁移

前端 `StockInfoList.vue` 调用从 `/stocks/` 改为 `/stock-panel/`，参数保持不变：

```typescript
// 旧
queryStocks({ page: 1, page_size: 20, list_status: 'L' })

// 新
queryStocks({ page: 1, page_size: 20, list_status: 'L', with_pools: true })
//  → 实际请求 GET /stock-panel/
```

响应字段保持兼容：`items / total / page / page_size` 与前端 `PaginatedResponse<T>` 1:1 对齐。

---

## 六、变更统计

| 层 | 文件 | 操作 | 改动量 |
|----|------|------|--------|
| Domain | `domain/panel/__init__.py` | 🆕 | ~5 行 |
| Domain | `domain/panel/value_objects.py` | 🆕 `StockPanelRow` | ~45 行 |
| Domain | `domain/panel/repository.py` | 🆕 Protocol | ~30 行 |
| Infra | `infrastructure/repositories/panel_compose_repository.py` | 🆕 SQL 实现 | ~140 行 |
| DTO | `application/dto/page.py` | 🆕 `Page[T]` | ~35 行 |
| DTO | `application/dto/panel.py` | 🆕 | ~70 行 |
| DTO | `application/dto/pool.py` | ✏️ 新增 `PoolMembershipVO` | ~10 行 |
| DTO | `application/dto/stock.py` | ⚰️ 删除 list_*/query_* | ~-90 行 |
| App | `application/panel_service.py` | 🆕 `StockPanelAppService` | ~75 行 |
| App | `application/stock_service.py` | ⚰️ 删除 `query_stocks` | ~-40 行 |
| Infra | `infrastructure/repositories/stock_repository.py` | ⚰️ 删除 `list_with_kline_stats_paginated` | ~-100 行 |
| Infra | `infrastructure/repositories/pool_repository.py` | ⚰️ 删除 `list_membership_by_symbols`（迁移后） | ~-30 行 |
| Route | `route/api/v1/panel.py` | 🆕 | ~45 行 |
| Route | `route/api/v1/stock.py` | ⚰️ 删除 `GET /` | ~-30 行 |
| Frontend | `frontend/src/views/stock-info/api.ts` | ✏️ 改 baseURL `/stock-panel/` | ~5 行 |
| Frontend | `frontend/src/views/stock-info/StockInfoList.vue` | ✏️ 删 N+1 调用，读 `row.pools` | ~-30 行 |
| **合计** | — | — | **净增 ~330 行 / 删 ~320 行** |

---

## 七、为什么不复用 `StockPoolBrief`

| 设计点 | 决策 | 理由 |
|--------|------|------|
| 阶段一设计的 `StockPoolBrief` | **不新建** | 阶段一`PoolMembershipVO` 字段（pool_id/name/pool_type/joined_at）已经足够，再建一个值对象是过度抽象 |
| 阶段二的池信息载体 | 直接用 `PoolMembershipVO` | 跨阶段复用，统一放置于 `application/dto/pool.py` |

**原则**：能不新建的就不新建；阶段一引入的 DTO 阶段二直接复用，不再造新概念。

---

## 八、相关文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| **类图：面板组合数据流** | `docs/PlantUML/StockInfo/03-panel-compose.puml` | 权威 PlantUML（4 层 + 4 表数据流图） |
| 类图：N+1 修复 | `docs/PlantUML/StockInfo/01-class.puml` | 阶段一跨层类图（with_pools 参数） |
| 统一设计文档 | `docs/dev/05listn1/README.md` | 整合两份原始设计，消除 4 处不一致 |
| UML 绘制规范 | `docs/config/uml类图设计规范.md` | PlantUML 绘制规范 |

> **约定**：PlantUML 文件统一放置于 `docs/PlantUML/StockInfo/`，设计文档放置于 `docs/dev/05listn1/`。
