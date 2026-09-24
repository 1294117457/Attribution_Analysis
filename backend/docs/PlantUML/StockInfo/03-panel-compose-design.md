# StockPanel 列表组合查询 — 类设计文档

> 围绕 `StockInfoList.vue` 一行数据的真实来源：横跨 **4 张表** (`stock_infos` + `tech_kline_dailys` + `fin_daily_basics` + `fin_reports`) 的组合查询 + 分页。
>
> 文档版本：v1 · 日期：2026-09-18 · 配套 UML：`03-panel-compose.puml`

---

## 一、背景

### 1.1 一行数据的来源拆分

`StockInfoList.vue` 表格中每一条记录由 **4 张表** 共同构成：

| 表 | 行内字段个数 | 提供字段 |
|----|-----------|----------|
| **`stock_infos`** | 13 个 | `symbol, ts_code, name, area, industry, market, exchange, list_date, list_status, is_hs, act_name, act_ent_type, total_shares` |
| **`tech_kline_dailys`** | 3 个聚合 | `record_count`, `kline_start`, `kline_end` （K 线统计） |
| **`fin_daily_basics`** | 3 个最新快照 | `latest_close`, `total_mv`, `pe_ttm` |
| **`fin_reports`** | 1 个计算 | `profit_margin = n_income / revenue * 100` |

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
1. **越界**：4 张表分属 4 个聚合根（stock_info / kline / fin_daily_basic / fin_report），把它们的连接硬塞进 stock_info 仓储，破坏聚合根边界。
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
| 用 `Page[T]` 通用分页 | 参照 `idbackend/src/app/schemas/page.py`，新增 `application/dto/page.py` 提供通用容器 + 语义别名 |
| 不为这个场景新增 DTO | 只把 `StockPanelRow` 映射成同构的 `StockPanelItemVO`，**不重复定义字段** |

---

## 三、修改清单

> 图例：🆕 新增 · ✏️ 修改 · ⚪ 不变

### 3.1 持久层 ⚪

`stock_infos / tech_kline_dailys / fin_daily_basics / fin_reports` 四张表 + 4 个 ORM 模型 **完全不变**。

### 3.2 领域层 🆕

#### `domain/panel/value_objects.py` 🆕

新建一个**中立领域**目录 `domain/panel/`，里面只有一个 `StockPanelRow` 值对象，**不属于任何已有聚合根**：

```python
"""StockPanel 组合行 — 4 表快照的不可变值对象"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class StockPanelRow:
    """股票列表面板行快照（4 表 JOIN 结果）

    来源：
    - stock_infos       基础字段 13 个
    - tech_kline_dailys K 线统计 3 个（COUNT/MIN/MAX 聚合）
    - fin_daily_basics  最新一行估值 3 个
    - fin_reports       最新一期净利润率 1 个（n_income/revenue*100）

    用途：只用于"列表面板"场景的投影，不能写回任何源表。
    """

    # ── 来自 stock_infos ─────────────────────────
    symbol: str
    ts_code: Optional[str]
    name: Optional[str]
    area: Optional[str]
    industry: Optional[str]
    market: Optional[str]
    exchange: Optional[str]
    list_date: Optional[str]            # YYYYMMDD
    list_status: Optional[str]
    is_hs: Optional[str]
    act_name: Optional[str]
    act_ent_type: Optional[str]
    total_shares: Optional[int]

    # ── 来自 tech_kline_dailys（聚合） ──────────────
    record_count: int                    # COUNT(*) by symbol
    kline_start: Optional[date]          # MIN(date)
    kline_end:   Optional[date]          # MAX(date)

    # ── 来自 fin_daily_basics（最新一行） ─────────
    latest_close: Optional[float]
    total_mv:     Optional[float]
    pe_ttm:       Optional[float]

    # ── 来自 fin_reports（最新一期，n_income/revenue*100）
    profit_margin: Optional[float]
```

**为什么不放在 `domain/stock_info/value_objects.py`？**
这个值对象不属于 `StockInfo` 聚合根的语义——它本质是"列表面板视图"，跨了 4 个聚合根，硬塞进 `stock_info` 包会反向暗示这个对象属于该聚合根。新建 `domain/panel/` 目录让跨域组合有一席之地。

#### 4 个原有的 domain/Repository ⚪

`StockInfoRepository / KlineRepository / FinDailyBasicRepository / FinReportRepository` **不变**。

### 3.3 仓储层 🆕

#### `domain/panel/repository.py` 🆕

```python
"""StockPanel 组合查询 — Protocol 在领域层"""

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
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StockPanelRow], int]:
        """分页 + 多维筛选 + 4 表快照，返回 (rows, total)"""
        ...
```

#### `infrastructure/repositories/panel_compose_repository.py` 🆕

```python
"""StockPanel 组合查询 — SQLAlchemy 实现"""

from typing import Optional
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.panel.value_objects import StockPanelRow
from infrastructure.database.models.stock_info import StockInfoDB
from infrastructure.database.models.tech_kline import TechKlineDailyDB
from infrastructure.database.models.fin_daily_basic import FinDailyBasicDB
from infrastructure.database.models.fin_report import FinReportDB


class StockPanelComposeRepoImpl:
    """列表面板组合仓储实现

    关键点（与 `02-modification.md` 当前实现保持一致）：
    - 主表 stock_infos
    - LEFT JOIN tech_kline_dailys 拿 K 线聚合
    - 通过子查询拿 fin_daily_basics 每只股票最新一行
    - 通过子查询拿 fin_reports 每只股票最新一期财报
    - min_total_mv 走 HAVING + count JOIN
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_paginated(self, ...) -> tuple[list[StockPanelRow], int]:
        # 子查询：fin_daily_basics 每只股票最新一行
        latest_date_sq = (
            select(
                FinDailyBasicDB.symbol,
                func.max(FinDailyBasicDB.trade_date).label("max_date"),
            )
            .group_by(FinDailyBasicDB.symbol)
            .subquery()
        )
        latest_basic_sq = (
            select(
                FinDailyBasicDB.symbol,
                FinDailyBasicDB.close.label("latest_close"),
                FinDailyBasicDB.total_mv,
                FinDailyBasicDB.pe_ttm,
            )
            .join(latest_date_sq, ...)
            .subquery()
        )

        # 子查询：fin_reports 每只股票最新一期报表
        latest_report_date_sq = (
            select(
                FinReportDB.symbol,
                func.max(FinReportDB.end_date).label("max_end_date"),
            )
            .where(FinReportDB.report_type == "1")
            .group_by(FinReportDB.symbol)
            .subquery()
        )
        latest_report_sq = (
            select(
                FinReportDB.symbol,
                (FinReportDB.n_income / func.nullif(FinReportDB.revenue, 0) * 100).label("profit_margin"),
            )
            .join(latest_report_date_sq, ...)
            .subquery()
        )

        stmt = (
            select(
                StockInfoDB.symbol,
                StockInfoDB.ts_code,
                StockInfoDB.name,
                ...,
                func.count(TechKlineDailyDB.id).label("record_count"),
                func.min(TechKlineDailyDB.date).label("kline_start"),
                func.max(TechKlineDailyDB.date).label("kline_end"),
                latest_basic_sq.c.latest_close,
                latest_basic_sq.c.total_mv,
                latest_basic_sq.c.pe_ttm,
                latest_report_sq.c.profit_margin,
            )
            .outerjoin(TechKlineDailyDB, StockInfoDB.symbol == TechKlineDailyDB.symbol)
            .outerjoin(latest_basic_sq, ...)
            .outerjoin(latest_report_sq, ...)
            .group_by(StockInfoDB.id, ...)
        )
        # ... 条件构造、HAVING 过滤、order/limit/offset 同当前实现
        ...

        # ORM 行 → StockPanelRow
        return [
            StockPanelRow(
                symbol=r.symbol,
                ts_code=r.ts_code,
                name=r.name,
                ...
                latest_close=r.latest_close,
                total_mv=r.total_mv,
                pe_ttm=r.pe_ttm,
                profit_margin=round(r.profit_margin, 2) if r.profit_margin is not None else None,
            )
            for r in rows
        ], int(total)


StockPanelComposeRepoImpl.__implements_protocol__ = StockPanelComposeRepository
```

**这一步相当于把 SQL 从 `StockRepoImpl.list_with_kline_stats_paginated` 平移到独立的 `StockPanelComposeRepoImpl`**，
属于纯重构，**不影响外部行为**。

### 3.4 应用层

#### `application/dto/page.py` 🆕

参照 `idbackend/src/app/schemas/page.py`，提供通用 `Page[T]` 容器：

```python
"""通用分页响应容器（跨模块复用）

约定：
- Page[T] 提供 .from_list_to_page() 工厂方法
- 列表 VO 通过继承 Page[T] 形成语义别名
- 与 idbackend 项目保持字段一致：list/total/pageNum/pageSize/pages
"""

from typing import Generic, List, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    list: List[T]
    total: int
    pageNum: int
    pageSize: int
    pages: int

    @classmethod
    def from_list_to_page(
        cls,
        items: List[T],
        total: int,
        page_num: int,
        page_size: int,
    ) -> "Page[T]":
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            list=items,
            total=total,
            pageNum=page_num,
            pageSize=page_size,
            pages=pages,
        )


__all__ = ["Page"]
```

#### `application/dto/panel.py` 🆕

只放**与领域 `StockPanelRow` 同构**的 `StockPanelItemVO` + 分页别名：

```python
"""StockPanel 列表 DTO"""

from __future__ import annotations
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from application.dto.page import Page


# ── 单行 VO（与 domain.panel.value_objects.StockPanelRow 字段一一对应）─

class StockPanelItemVO(BaseModel):
    """列表面板单行 VO（4 表组合快照的对外契约）"""

    # 来自 stock_infos
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

    # 来自 tech_kline_dailys
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end:   Optional[date] = None

    # 来自 fin_daily_basics
    latest_close: Optional[float] = None
    total_mv:     Optional[float] = None
    pe_ttm:       Optional[float] = None

    # 来自 fin_reports
    profit_margin: Optional[float] = None


# ── 列表语义别名（沿用 Page[T] 的工厂方法）────────────────────

class StockPanelListVO(Page[StockPanelItemVO]):
    """StockPanel 列表响应（分页 + 4 表快照）"""
    pass


# ── 请求体 ──────────────────────────────────────────

class StockPanelQueryRequest(BaseModel):
    q: Optional[str] = Field(None, description="代码 / 名称 / 拼音 模糊搜索")
    industry:    Optional[str] = None
    market:      Optional[str] = None
    exchange:    Optional[str] = None
    is_hs:       Optional[str] = None
    list_status: Optional[str] = "L"
    exclude_st:  Optional[bool] = None
    min_total_mv: Optional[float] = Field(None, ge=0, description="最低总市值(万元)")
    pageNum:  int = Field(1,  ge=1)
    pageSize: int = Field(20, ge=1, le=500)
```

**关键：**
- `StockPanelItemVO` **只跟 `StockPanelRow` 字段对等**，不多定义不少定义。
- `StockPanelListVO = Page[StockPanelItemVO]` 是**纯继承**，靠 `from_list_to_page` 工厂方法获得完整分页。

#### `application/panel_service.py` 🆕

```python
"""StockPanel 应用服务"""

from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.panel import (
    StockPanelItemVO,
    StockPanelListVO,
    StockPanelQueryRequest,
)
from application.dto.page import Page
from domain.panel.repository import StockPanelComposeRepository
from domain.panel.value_objects import StockPanelRow
from infrastructure.repositories.panel_compose_repository import StockPanelComposeRepoImpl


class StockPanelAppService:
    """列表面板应用服务

    职责单一：把"分页 + 多表快照"组合查询的结果组装为分页 VO。
    不做单表 CRUD，不做领域事件，不依赖其他应用服务。
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo: StockPanelComposeRepository = StockPanelComposeRepoImpl(session)

    async def query_panels(self, req: StockPanelQueryRequest) -> StockPanelListVO:
        rows, total = await self._repo.list_paginated(
            q=req.q,
            industry=req.industry,
            market=req.market,
            exchange=req.exchange,
            is_hs=req.is_hs,
            list_status=req.list_status,
            exclude_st=req.exclude_st,
            min_total_mv=req.min_total_mv,
            page=req.pageNum,
            page_size=req.pageSize,
        )

        items = [_to_vo(r) for r in rows]

        return StockPanelListVO.from_list_to_page(
            items=items,
            total=total,
            page_num=req.pageNum,
            page_size=req.pageSize,
        )


def _to_vo(r: StockPanelRow) -> StockPanelItemVO:
    return StockPanelItemVO(
        symbol=r.symbol,
        ts_code=r.ts_code,
        name=r.name,
        ...                       # 字段一一对应，无额外逻辑
    )
```

---

## 四、调用时序

```
前端 GET /api/v1/stock-panel/?pageNum=1&pageSize=20&industry=银行
  └─► route/api/v1/panel.py::query_panels
        └─► StockPanelAppService.query_panels(request)
              └─► StockPanelComposeRepoImpl.list_paginated(...)    ← 1×SQL
                    ├─ JOIN: stock_infos (主)
                    ├─ JOIN: tech_kline_dailys（聚合）
                    ├─ JOIN: fin_daily_basics（MAX 子查询）
                    └─ JOIN: fin_reports（MAX 子查询）
              └─► StockPanelListVO.from_list_to_page(items, total, ...)
```

**SQL 数量：1 条**（带 3 个子查询 / 1 个 GROUP BY），无 N+1。

---

## 五、与现有实现的兼容

| 现有 | 处置 |
|------|------|
| `StockRepoImpl.list_with_kline_stats_paginated` | ⚠️ 删除（迁移到 `StockPanelComposeRepoImpl.list_paginated`），不重复保留 |
| `StockAppService.query_stocks` | ⚠️ 删除（统一由 `StockPanelAppService.query_panels` 承担） |
| `StockQueryItemResponse` / `StockQueryResponse` | ⚠️ 删除（被 `StockPanelItemVO` / `StockPanelListVO` 替代） |
| `application/dto/stock.py` 中的 list_*/query_* 相关 DTO | ⚠️ 删除（仅保留 `StockUpdateRequest` 等写入 DTO） |
| `application/dto/page.py` `Page[T]` | 🆕 通用容器，未来 `PoolListVO(Page[PoolVO])` 等也可复用 |
| 4 个原 `*_Repository` | ⚪ 不变（单表 CRUD 不受影响）|
| 前端 `StockInfoList.vue` | ✏️ 改 `StockQueryParams.page → pageNum`、`items → list`、`page_size → pageSize`、`page → pageNum` |

> 注意前端字段名变更：旧的 `page` / `page_size` / `items` 与前端 `api.ts` `PaginatedResponse<T>` 是配套的，整体迁到 `Page[T]` 命名（`pageNum` / `pageSize` / `list`）需要在前后端一起改。**这步可以分阶段实施，先做后端、前端保留兼容。**

---

## 六、变更统计

| 层 | 文件 | 类型 | 改动量 |
|----|------|------|--------|
| Domain | `domain/panel/value_objects.py` | 🆕 | ~40 行 |
| Domain | `domain/panel/repository.py` | 🆕 | ~30 行 |
| Infrastructure | `infrastructure/repositories/panel_compose_repository.py` | 🆕 | ~130 行 |
| Application | `application/dto/page.py` | 🆕 | ~45 行 |
| Application | `application/dto/panel.py` | 🆕 | ~80 行 |
| Application | `application/panel_service.py` | 🆕 | ~60 行 |
| Application | `application/dto/stock.py` | ✏️ | -删 list_*/query_*（约 -130 行） |
| Application | `application/stock_service.py` | ✏️ | -删 query_stocks（约 -40 行） |
| Infrastructure | `infrastructure/repositories/stock_repository.py` | ✏️ | -删 list_with_kline_stats_paginated（约 -100 行） |
| Route | `route/api/v1/panel.py` | 🆕 | ~30 行（替代 stock.py 的列表路由） |
| **总计** | — | — | **净 +150 / -270 行** |

---

## 七、为什么不复用 `StockPanelBrief` / `PoolMembershipVO` 等历史设计

| 之前的设计（02-modification） | 现在 | 理由 |
|------------------------------|------|------|
| 新建 `StockPoolBrief` 值对象 | **不建**（也不在本文档范围）| 上次的目的是解决 N+1；当前文档聚焦"4 表组合"这一侧，池是另一个维度 |
| 新建 `PoolMembershipVO` | **不建** | 直接复用 `PoolVO`，列表场景前端 TS 类型按需取字段 |
| 列表 DTO 新建 `StockQueryItemResponse` | 直接 = 领域 `StockPanelRow` 字段投影 | 一一对应，没有重复 |
| 自定义分页 wrapper | 用 `Page[T]` 通用容器 | 跨模块复用，避免每个列表页自定义 |

**原则：能不新建的就不新建，能用通用容器的就用通用容器。**
