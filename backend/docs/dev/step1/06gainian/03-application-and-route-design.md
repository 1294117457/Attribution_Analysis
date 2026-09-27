# 03 — 应用层与路由设计

> 配套 UML：`docs/PlantUML/Concept/01-class.puml` 中「应用层」和「路由层」package
> 所属：`docs/dev/06gainian/README.md` 第五节「API 设计概览」

---

## 一、DTO 设计

### 1.1 ConceptBriefVO（已在领域层定义）

```python
# domain/concept/value_objects.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ConceptBriefVO:
    """概念简略 VO（嵌入到 StockPanelItemVO.concepts，给详情抽屉复用）"""
    concept_id: int
    name: str
    source: str  # "em" / "ths"
```

### 1.1.1 ConceptGroupedVO（详情抽屉用，按类型分组）

```python
# application/dto/concept.py（新增）
@dataclass(frozen=True)
class ConceptGroupedVO:
    """按概念类型分组的概念列表（详情抽屉用）

    与 ConceptBriefVO 的区别：
    - ConceptBriefVO：仅 3 个字段，嵌入列表场景（StockPanelItemVO.concepts）
    - ConceptGroupedVO：携带 concept_type，用于详情抽屉分组展示
    """
    concept_id: int
    name: str
    source: str
    concept_type: str   # industry / theme / style / region / event / other
    description: Optional[str] = None


@dataclass(frozen=True)
class ConceptListBySymbolVO:
    """单股票所属概念列表（详情抽屉用，按类型分组）

    返回结构：
    {
      "symbol": "002229",
      "concepts_by_type": {
        "industry": [...],
        "theme": [...],
        "style": [...],
        ...
      },
      "all_concepts": [...]  # 扁平列表，方便排序/筛选
    }
    """
    symbol: str
    concepts_by_type: dict[str, list[ConceptGroupedVO]]
    all_concepts: list[ConceptGroupedVO]
```

### 1.1.2 ConceptTabSectionVO / ConceptTabContentVO（前端 Tab 渲染模型）

```python
# application/dto/concept.py（新增）
@dataclass(frozen=True)
class ConceptTabSectionVO:
    """概念 Tab 单个分组区块

    渲染策略：每个 concept_type 一行标题 + 一组 Tag。
    标题顺序：industry → theme → style → region → event → other（业务约定）。
    """
    type: str               # industry / theme / style / region / event / other
    type_label: str         # 行业概念 / 主题概念 / ...
    concepts: list[ConceptGroupedVO]


@dataclass(frozen=True)
class ConceptTabContentVO:
    """概念 Tab 完整渲染模型

    前端 ConceptTab.vue 直接消费，无需再做分组。
    """
    symbol: str
    stock_name: str                  # 抽屉顶部用
    sections: list[ConceptTabSectionVO]   # 已按预定顺序排好
    total_count: int                  # 用于「共 N 个概念」统计
```

### 1.2 ConceptQueryRequest

```python
# application/dto/concept.py
"""概念相关 DTO"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ConceptQueryRequest(BaseModel):
    """概念列表查询请求"""
    q: Optional[str] = Field(None, description="模糊搜索概念名称")
    source: Optional[str] = Field(None, description="数据源：em / ths")
    is_active: Optional[bool] = Field(None, description="是否有效")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class ConceptSyncRequest(BaseModel):
    """概念同步请求"""
    source: str = Field("em", description="数据源：em / ths")
    concept_names: Optional[list[str]] = Field(
        None, description="指定概念名称列表，为空则全量同步"
    )
    force_resync: bool = Field(False, description="是否强制重同步已有概念")


class ConceptItemVO(BaseModel):
    """概念详情 VO"""
    concept_id: int
    name: str
    source: str
    concept_type: str
    stock_count: int
    description: Optional[str] = None
    is_active: bool
    last_synced_at: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConceptMemberVO(BaseModel):
    """概念成员 VO（成分股）"""
    symbol: str
    name: str
    rank: Optional[int] = None
    latest_price: Optional[float] = None

    model_config = {"from_attributes": True}


class ConceptDetailVO(ConceptItemVO):
    """概念详情（含成分股）"""
    members: list[ConceptMemberVO] = Field(default_factory=list)


class ConceptSyncResultVO(BaseModel):
    """同步结果 VO"""
    total_concepts: int
    total_members: int
    failed_concepts: list[str]
    elapsed_ms: int
    synced_at: datetime
```

### 1.3 StockPanelItemVO 修改（新增 concepts 字段）

```python
# application/dto/panel.py（修改）
from domain.concept.value_objects import ConceptBriefVO

class StockPanelItemVO(BaseModel):
    """面板行 VO"""
    # ... 既有字段不变 ...

    # ── stock_pool_members ⨝ stock_pools ─────
    pools: list[PoolMembershipVO] = Field(default_factory=list)

    # ── stock_concept_members ⨝ concepts ── 🆕
    concepts: list[ConceptBriefVO] = Field(default_factory=list)

    model_config = {"from_attributes": True}
```

### 1.4 Page[T]（复用既有）

```python
# application/dto/page.py（既有）
class Page(BaseModel, Generic[T]):
    """通用分页响应"""
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def from_list(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "Page[T]":
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)


class ConceptListVO(Page[ConceptItemVO]):
    """概念列表响应"""
    pass
```

---

## 二、应用服务设计

### 2.1 ConceptAppService

```python
# application/concept_service.py
"""概念应用服务"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from domain.concept.entity import Concept
from domain.concept.exceptions import ConceptNotFoundError
from domain.concept.repository import ConceptRepository
from domain.concept.value_objects import ConceptBriefVO
from application.dto.concept import (
    ConceptDetailVO,
    ConceptItemVO,
    ConceptListVO,
    ConceptMemberVO,
    ConceptQueryRequest,
    ConceptSyncRequest,
    ConceptSyncResultVO,
)
from infrastructure.collectors.protocols import ConceptFetcher

logger = logging.getLogger(__name__)


class ConceptAppService:
    """概念应用服务

    职责：
    - 同步：触发 AKShare 采集器同步概念数据
    - 查询：列表 / 详情 / 反查（供 panel 调用）
    """

    def __init__(
        self,
        repo: ConceptRepository,
        fetcher: ConceptFetcher,
    ):
        self._repo = repo
        self._fetcher = fetcher

    # ── 同步 ─────────────────────────────────────────

    async def sync_concepts(self, req: ConceptSyncRequest) -> ConceptSyncResultVO:
        """全量/增量同步概念数据

        伪代码：
        ① 获取全量概念清单（fetcher.fetch_concept_list）
        ② 逐个 upsert_concept + upsert_members
        ③ 返回同步结果
        """
        from infrastructure.tasks.concept_sync_operation import ConceptSyncOperation

        operation = ConceptSyncOperation(repo=self._repo, fetcher=self._fetcher)
        result = await operation.sync_all()

        return ConceptSyncResultVO(
            total_concepts=result.total_concepts,
            total_members=result.total_members,
            failed_concepts=result.failed_concepts,
            elapsed_ms=result.elapsed_ms,
            synced_at=result.synced_at,
        )

    # ── 查询 ─────────────────────────────────────────

    async def query_concepts(
        self, req: ConceptQueryRequest
    ) -> ConceptListVO:
        """分页查询概念列表"""
        concepts, total = await self._repo.list_concepts(
            q=req.q,
            source=req.source,
            is_active=req.is_active,
            page=req.page,
            page_size=req.page_size,
        )

        items = [
            ConceptItemVO(
                concept_id=c.id,
                name=c.name,
                source=c.source.value,
                concept_type=c.concept_type.value if hasattr(c.concept_type, 'value') else c.concept_type,
                stock_count=c.stock_count,
                description=c.description,
                is_active=c.is_active,
                last_synced_at=c.last_synced_at,
                first_seen_at=c.first_seen_at,
            )
            for c in concepts
        ]

        return ConceptListVO.from_list(
            items=items,
            total=total,
            page=req.page,
            page_size=req.page_size,
        )

    async def get_concept_detail(self, name: str, source: str = "em") -> ConceptDetailVO:
        """概念详情（含成分股）"""
        concept = await self._repo.get_concept_by_name(name=name, source=source)
        if not concept:
            raise ConceptNotFoundError(name=name)

        # 获取成分股（从 fetcher 实时拉取，或从缓存）
        stock_bos = self._fetcher.fetch_concept_stocks(name)
        members = [
            ConceptMemberVO(
                symbol=s.symbol,
                name=s.name,
                rank=s.rank,
                latest_price=s.latest_price,
            )
            for s in stock_bos
        ]

        return ConceptDetailVO(
            concept_id=concept.id,
            name=concept.name,
            source=concept.source.value,
            concept_type=concept.concept_type.value if hasattr(concept.concept_type, 'value') else concept.concept_type,
            stock_count=concept.stock_count,
            description=concept.description,
            is_active=concept.is_active,
            last_synced_at=concept.last_synced_at,
            first_seen_at=concept.first_seen_at,
            members=members,
        )

    # ── 反向查询（供 panel 复用）──────────────────────

    async def list_for_symbol(self, symbol: str) -> list[ConceptBriefVO]:
        """单只股票所属的所有活跃概念"""
        return await self._repo.list_concepts_by_symbol(symbol)

    async def list_for_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[ConceptBriefVO]]:
        """批量反向查询（避免 N+1）"""
        return await self._repo.list_concepts_by_symbols(symbols)

    # ── 🆕 详情抽屉「概念」Tab 专用 ──────────────────

    async def get_tab_content_for_symbol(
        self, symbol: str, stock_name: Optional[str] = None
    ) -> ConceptTabContentVO:
        """详情抽屉「概念」Tab 的完整渲染模型

        步骤：
        ① 拉取该股票所属的所有活跃概念（含 concept_type / description）
        ② 按 concept_type 分组，按预定顺序排序（industry → theme → style → region → event → other）
        ③ 组装为 ConceptTabContentVO，前端 ConceptTab.vue 直接消费
        """
        grouped_vos = await self._repo.list_concepts_by_symbol_grouped(symbol)

        type_order = ["industry", "theme", "style", "region", "event", "other"]
        type_labels = {
            "industry": "行业概念",
            "theme":    "主题概念",
            "style":    "风格概念",
            "region":   "地域概念",
            "event":    "事件概念",
            "other":    "其他概念",
        }

        bucket: dict[str, list[ConceptGroupedVO]] = {t: [] for t in type_order}
        for vo in grouped_vos:
            bucket.setdefault(vo.concept_type, []).append(vo)

        sections = [
            ConceptTabSectionVO(
                type=t,
                type_label=type_labels.get(t, t),
                concepts=sorted(bucket[t], key=lambda c: c.name),
            )
            for t in type_order
            if bucket[t]
        ]

        return ConceptTabContentVO(
            symbol=symbol,
            stock_name=stock_name or "",
            sections=sections,
            total_count=sum(len(s.concepts) for s in sections),
        )
```

> **Repository 层扩展**：上述 `list_concepts_by_symbol_grouped` 需要在
> `ConceptRepository` Protocol 中新增（详见 [01-domain-design.md §5.1.1](../01-domain-design.md)）。
> 与 `list_concepts_by_symbols` 的区别：返回 `ConceptGroupedVO[]` 而非 `ConceptBriefVO[]`，
> 多查询 `concept_type` / `description` 两列，前端抽屉 Tab 需要展示分组标题。

### 2.2 StockPanelAppService 修改（新增 with_concepts 参数）

```python
# application/panel_service.py（修改）
from domain.concept.value_objects import ConceptBriefVO

class StockPanelAppService:
    def __init__(
        self,
        panel_repo: StockPanelComposeRepository,
        concept_app_service: Optional[ConceptAppService] = None,  # 🆕
    ):
        self._panel_repo = panel_repo
        self._concept_app = concept_app_service

    async def query_panels(self, req: StockPanelQueryRequest) -> StockPanelListVO:
        """面板列表查询

        步骤：
        ① rows, total = repo.list_paginated(req)      ← 1× SQL
        ② pool_map    = repo.list_membership_by_symbols([r.symbol for r in rows])  [if with_pools]
        ③ concept_map = repo.list_concepts_by_symbols([r.symbol for r in rows])       [if with_concepts] 🆕
        ④ items = [_to_vo(r, pool_map.get(r.symbol), concept_map.get(r.symbol)) for r in rows]
        ⑤ return StockPanelListVO.from_list(...)
        """
        rows, total = await self._panel_repo.list_paginated(
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

        symbols = [r.symbol for r in rows]

        # ② 池反查
        pool_map: dict[str, list[PoolMembershipVO]] = {}
        if req.with_pools:
            pool_map = await self._panel_repo.list_membership_by_symbols(symbols)

        # ③ 概念反查 🆕
        concept_map: dict[str, list[ConceptBriefVO]] = {}
        if req.with_concepts and self._concept_app:
            concept_map = await self._panel_repo.list_concepts_by_symbols(symbols)

        # ④ 组装 VO
        items = [
            StockPanelItemVO(
                **self._to_row_dict(r),
                pools=pool_map.get(r.symbol, []),
                concepts=concept_map.get(r.symbol, []),  # 🆕
            )
            for r in rows
        ]

        return StockPanelListVO.from_list(
            items=items,
            total=total,
            page=req.page,
            page_size=req.page_size,
        )
```

---

## 三、路由设计

### 3.1 ConceptRouter

```python
# route/api/v1/concept.py
"""概念路由"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from application.concept_service import ConceptAppService
from application.dto.concept import (
    ConceptDetailVO,
    ConceptListVO,
    ConceptQueryRequest,
    ConceptSyncRequest,
    ConceptSyncResultVO,
    ConceptTabContentVO,
)
from domain.concept.exceptions import ConceptNotFoundError
from domain.concept.repository import ConceptRepository
from infrastructure.collectors.protocols import ConceptFetcher
from infrastructure.repositories.concept_repository import ConceptRepoImpl
from infrastructure.database.session import get_db_session

router = APIRouter(prefix="/concepts", tags=["概念"])


# ── 依赖注入 ────────────────────────────────────────

async def get_concept_app_service(
    session: AsyncSession = Depends(get_db_session),
) -> ConceptAppService:
    """获取 ConceptAppService 实例"""
    repo = ConceptRepoImpl(session)
    # 从 FetcherRegistry 获取已注册的 fetcher
    from infrastructure.collectors.registry import get_registry
    registry = get_registry()
    fetcher = registry.get_fetcher(ConceptFetcher)
    if not fetcher:
        raise HTTPException(503, "概念采集器未注册")
    return ConceptAppService(repo=repo, fetcher=fetcher)


# ── 路由定义 ────────────────────────────────────────

@router.get("/", response_model=ConceptListVO)
async def list_concepts(
    req: Annotated[ConceptQueryRequest, Query()],
    app: ConceptAppService = Depends(get_concept_app_service),
) -> ConceptListVO:
    """分页列出所有概念（支持 q / source / is_active 筛选）"""
    return await app.query_concepts(req)


@router.get("/{name}", response_model=ConceptDetailVO)
async def get_concept_detail(
    name: str,
    source: str = Query("em", description="数据源：em / ths"),
    app: ConceptAppService = Depends(get_concept_app_service),
) -> ConceptDetailVO:
    """单概念详情（含成分股）"""
    try:
        return await app.get_concept_detail(name=name, source=source)
    except ConceptNotFoundError:
        raise HTTPException(404, f"概念 {name!r} 不存在")


@router.get("/by-symbol/{symbol}", response_model=list[ConceptBriefVO])
async def get_concepts_by_symbol(
    symbol: str,
    app: ConceptAppService = Depends(get_concept_app_service),
) -> list[ConceptBriefVO]:
    """单股票所属概念列表（轻量版，仅 concept_id / name / source）

    用于详情抽屉「概念」Tab 的快速打开（避免首屏就拉全量）。
    前端拿到后可直接渲染概念 Tag；如果用户切到「概念」Tab，
    再调下方的 /tab-by-symbol/{symbol} 拿全量分组数据。
    """
    return await app.list_for_symbol(symbol)


# 🆕 详情抽屉「概念」Tab 专用端点（按类型分组，返回 ConceptTabContentVO）
@router.get("/tab-by-symbol/{symbol}", response_model=ConceptTabContentVO)
async def get_concept_tab_for_symbol(
    symbol: str,
    stock_name: Optional[str] = Query(None, description="股票名称（仅用于头部展示）"),
    app: ConceptAppService = Depends(get_concept_app_service),
) -> ConceptTabContentVO:
    """单股票所属概念 Tab 内容（按 concept_type 分组，含 description）

    抽屉「概念」Tab 切换时调用，返回 ConceptTabContentVO，
    前端 ConceptTab.vue 直接消费，无需再做分组 / 排序。
    """
    return await app.get_tab_content_for_symbol(symbol, stock_name=stock_name)


@router.post("/sync", response_model=ConceptSyncResultVO)
async def sync_concepts(
    req: ConceptSyncRequest = ConceptSyncRequest(),
    app: ConceptAppService = Depends(get_concept_app_service),
) -> ConceptSyncResultVO:
    """触发概念全量/增量同步（后台任务）"""
    return await app.sync_concepts(req)


@router.get("/sync/status")
async def get_sync_status() -> dict:
    """查询最近同步状态"""
    # TODO: 从 Redis/DB 读取最近同步记录
    return {"status": "not_implemented"}
```

### 3.2 StockPanelRouter 修改

```python
# route/api/v1/panel.py（修改）
from application.dto.panel import StockPanelQueryRequest

class StockPanelQueryRequest(BaseModel):
    # ... 既有字段 ...
    with_pools: bool = False
    with_concepts: bool = False  # 🆕
    page: int = 1
    page_size: int = 20
```

---

## 四、前端对接（2026-09-24 修订）

> 设计变更：**概念数据从表格列改为详情抽屉 Tab**。
> 原方案在表格中新增概念列（最多 3 个 tag + `+N` 溢出），经交互走查后调整：
> - 表格聚焦"快速浏览 + 多维筛选"，不再嵌入概念列表（避免视觉拥挤）。
> - 右侧抽屉 `StockDetailDrawer.vue` 新增「概念」Tab，按 `concept_type` 分组展示。
> - 移除原 `el-table-column type="expand"`（点击行展开 KLine 看板），改为行内显眼「详情」按钮触发抽屉。
>
> 完整前端设计（组件结构、状态机、按钮强化细节）见
> **[04-frontend-detail-design.md](./04-frontend-detail-design.md)**。
> 本节仅给出 DTO / API / 关键交互的对接要点。

### 4.1 TypeScript 类型（`api.ts`）

```typescript
// frontend/src/views/stock-info/api.ts

// ── 概念相关 VO（与后端 1.1 节 1:1 对齐）────────────────

/** 简略 VO（嵌入到 StockInfo.concepts，给详情抽屉预热用） */
export interface ConceptBrief {
  concept_id: number
  name: string
  source: "em" | "ths"
}

/** 分组 VO（详情抽屉「概念」Tab 用） */
export interface ConceptGroupedVO {
  concept_id: number
  name: string
  source: "em" | "ths"
  concept_type: ConceptType        // 见下方枚举
  description: string | null
}

/** 概念类型（与后端 ConceptType 1:1） */
export type ConceptType =
  | "industry"   // 行业概念
  | "theme"      // 主题概念
  | "style"      // 风格概念
  | "region"     // 地域概念
  | "event"      // 事件概念
  | "other"      // 其他概念

/** 概念类型展示标签 */
export const CONCEPT_TYPE_LABELS: Record<ConceptType, string> = {
  industry: "行业概念",
  theme:    "主题概念",
  style:    "风格概念",
  region:   "地域概念",
  event:    "事件概念",
  other:    "其他概念",
}

/** Tab 单个分组区块 */
export interface ConceptTabSectionVO {
  type: ConceptType
  type_label: string
  concepts: ConceptGroupedVO[]
}

/** 概念 Tab 完整渲染模型（与后端 ConceptTabContentVO 1:1） */
export interface ConceptTabContentVO {
  symbol: string
  stock_name: string
  sections: ConceptTabSectionVO[]   // 已按 industry → theme → style → region → event → other 排序
  total_count: number
}

// ── 嵌入到 StockInfo ──────────────────────────────

export interface StockInfo {
  symbol: string
  name: string
  // ... 既有字段 ...
  pools: PoolMembership[]
  /** 简略概念列表（with_concepts=true 时附带，详情抽屉预热用） */
  concepts: ConceptBrief[]
}

// ── API 封装 ──────────────────────────────────────

/** GET /api/v1/concepts/by-symbol/{symbol}  单股票所属概念（仅简略 VO） */
export const getConceptsBySymbol = (symbol: string): Promise<ConceptBrief[]> =>
  http.get<ConceptBrief[]>(`/concepts/by-symbol/${symbol}`).then(unwrap)

/** GET /api/v1/concepts/tab-by-symbol/{symbol}  抽屉「概念」Tab 内容（按类型分组） */
export const getConceptTabForSymbol = (
  symbol: string,
  params: { stock_name?: string } = {},
): Promise<ConceptTabContentVO> =>
  http.get<ConceptTabContentVO>(`/concepts/tab-by-symbol/${symbol}`, { params }).then(unwrap)
```

### 4.2 StockInfoList.vue 改造要点

#### 4.2.1 移除概念列

```diff
   <el-table :data="stocks">
-    <!-- 🆕 概念列 -->
-    <el-table-column label="概念" min-width="180">
-      <template #default="{ row }"> ... </template>
-    </el-table-column>
   </el-table>
```

#### 4.2.2 移除展开列（type="expand"）

```diff
-  <!-- 展开列（点击行展开 KLine 看板，type="expand"） -->
-  <el-table-column type="expand">
-    <template #default="{ row }">
-      <StockExpandRow :symbol="row.symbol" />
-    </template>
-  </el-table-column>
```

#### 4.2.3 在固定列（`fixed="right"`）新增显眼的「详情」按钮列

> 用户原话：*"原有点击单个数据显示第二行kline看板的功能，改为 @StockInfoList.vue (127-151) 点击这里的按钮，
> 然后强化下这里按钮的显示效果让其更显眼"*

```vue
<!-- 行末操作列（fixed="right"）：高亮的「详情」按钮 -->
<el-table-column
  label="操作"
  width="100"
  fixed="right"
  align="center"
>
  <template #default="{ row }">
    <el-button
      type="primary"
      size="default"
      round
      plain
      class="row-detail-btn"
      @click.stop="openDetailDrawer(row)"
    >
      <el-icon class="mr-1"><View /></el-icon>
      详情
    </el-button>
  </template>
</el-table-column>
```

**按钮强化策略**（详见 `04-frontend-detail-design.md` §3）：

| 维度 | 原 `expand` 列 | 新「详情」按钮 |
|------|---------------|--------------|
| 视觉位置 | 行首小箭头（弱） | 行末大按钮（强）|
| 颜色 | 灰色） | `primary` 蓝色（醒目）|
| 尺寸 | 默认 | `default`（比 small 大）|
| 形状 | 箭头 | `round` 圆角（亲和）|
| 反馈 | 仅图标 + hover | 图标 + 文字 + hover 动画 + 点击波纹 |
| 触发方式 | `/rows` 整行 | 按钮 `click.stop`（不触发行选中）|

#### 4.2.4 行点击行为调整

```diff
- @row-click="toggleExpand"
+ @row-click="(row) => openDetailDrawer(row)"
```

> **保留** 行点击打开详情作为辅助入口；按钮是主要入口，两者等价。

#### 4.2.5 抽屉状态管理

```typescript
// 新增状态
const detailDrawerVisible = ref(false)
const detailDrawerStock = ref<StockInfo | null>(null)

function openDetailDrawer(row: StockInfo) {
  detailDrawerStock.value = row
  detailDrawerVisible.value = true
}

function closeDetailDrawer() {
  detailDrawerVisible.value = false
  // 延迟清空，避免抽屉关闭动画中内容闪烁
  setTimeout(() => { detailDrawerStock.value = null }, 300)
}
```

#### 4.2.6 模板新增抽屉

```vue
<StockDetailDrawer
  v-model="detailDrawerVisible"
  :stock="detailDrawerStock"
  @close="closeDetailDrawer"
  @add-to-pool="onAddToPool"
  @go-analysis="(symbol) => router.push(`/home/stock/${symbol}/analysis`)"
/>
```

#### 4.2.7 `with_concepts` 仍由后端下发（用于预热）

```typescript
// loadStocks() 仍带 with_concepts=true
// 抽屉打开后先读 row.concepts 渲染轻量 Tag，
// 同时后台调 getConceptTabForSymbol 拿全量分组内容，切 Tab 时无缝替换。
const data = await queryStocks({ ..., with_concepts: true })
```

### 4.3 StockDetailDrawer.vue 改造要点

#### 4.3.1 新增 props：预热概念数据

```typescript
interface Props {
  modelValue: boolean
  stock: StockInfo | null
  /** 抽屉首次打开时是否立即加载「概念」Tab 数据（默认 true） */
  prefetchConcepts?: boolean
}
```

#### 4.3.2 新增「概念」Tab

```diff
   <el-tabs v-model="activeTab" class="drawer-tabs">
     <el-tab-pane label="基本信息" name="info">...</el-tab-pane>
     <el-tab-pane label="K 线图" name="kline">
       <KLineDrawerTab :symbol="stock.symbol" />
     </el-tab-pane>
+    <el-tab-pane label="概念" name="concepts">
+      <ConceptTab :symbol="stock.symbol" :stock-name="stock.name" />
+    </el-tab-pane>
     <el-tab-pane label="归因分析" name="analysis">...</el-tab-pane>
   </el-tabs>
```

### 4.4 新增 ConceptTab.vue 组件

> 详见 [`04-frontend-detail-design.md §2.4.3`](./04-frontend-detail-design.md)。

```vue
<!-- components/ConceptTab.vue -->
<template>
  <div v-loading="loading" class="concept-tab">
    <div v-if="data && data.sections.length > 0">
      <div v-for="section in data.sections" :key="section.type" class="concept-section">
        <div class="section-title">
          <span class="title-text">{{ section.type_label }}</span>
          <el-tag size="small" type="info" effect="plain">{{ section.concepts.length }}</el-tag>
        </div>
        <div class="concept-list">
          <ConceptTag
            v-for="c in section.concepts"
            :key="c.concept_id"
            :concept="c"
            @click="goConceptDetail(c)"
          />
        </div>
      </div>
      <div class="concept-summary mt-3">
        共 <b>{{ data.total_count }}</b> 个概念
        <el-link type="primary" :underline="false" @click="reload">
          <el-icon class="mr-1"><Refresh /></el-icon>刷新
        </el-link>
      </div>
    </div>
    <el-empty v-else-if="!loading" description="暂无概念数据" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  getConceptTabForSymbol,
  type ConceptTabContentVO,
  type ConceptGroupedVO,
} from '@/views/stock-info/api'
import ConceptTag from './ConceptTag.vue'

const props = defineProps<{ symbol: string; stock_name?: string }>()
const emit = defineEmits<{ conceptClick: [c: ConceptGroupedVO] }>()

const loading = ref(false)
const data = ref<ConceptTabContentVO | null>(null)

async function load() {
  if (!props.symbol) return
  loading.value = true
  try {
    data.value = await getConceptTabForSymbol(props.symbol, {
      stock_name: props.stock_name,
    })
  } catch (e) {
    ElMessage.error('加载概念失败: ' + (e as Error).message)
  } finally {
    loading.value = false
  }
}

async function reload() {
  await load()
}

function goConceptDetail(c: ConceptGroupedVO) {
  emit('conceptClick', c)
  // 预留：未来可跳到概念详情页 / 当前先 console / toast
  ElMessage.info(`点击了概念: ${c.name}（${c.source}）`)
}

watch(() => props.symbol, load, { immediate: true })
</script>
```

### 4.5 新增 ConceptTag.vue 组件

```vue
<!-- components/ConceptTag.vue -->
<template>
  <el-tooltip
    :content="concept.description || '点击查看概念详情'"
    placement="top"
    :show-after="200"
  >
    <el-tag
      :type="tagType"
      :effect="hovered ? 'dark' : 'plain'"
      class="concept-tag"
      :class="{ 'is-clickable': true }"
      @mouseenter="hovered = true"
      @mouseleave="hovered = false"
      @click.stop="$emit('click', concept)"
    >
      {{ concept.name }}
    </el-tag>
  </el-tooltip>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ConceptGroupedVO, ConceptType } from '@/views/stock-info/api'

const props = defineProps<{ concept: ConceptGroupedVO }>()
defineEmits<{ click: [c: ConceptGroupedVO] }>()

const hovered = ref(false)

const tagType = computed(() => {
  const map: Record<ConceptType, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    industry: 'primary',
    theme:    'success',
    style:    'warning',
    region:   'info',
    event:    'danger',
    other:    'info',
  }
  return map[props.concept.concept_type] || 'info'
})
</script>

<style scoped>
.concept-tag {
  margin: 0 4px 6px 0;
  cursor: pointer;
  transition: transform 0.15s ease;
}
.concept-tag.is-clickable:hover {
  transform: translateY(-1px);
}
</style>
```

### 4.6 列表请求策略变化

| 维度 | 原方案 | 新方案 |
|------|------|------|
| 列表字段 | `with_concepts=true` 必传，每行 3 个 tag + `+N` | `with_concepts=true` 仍传，但仅作为抽屉"零概念预热"用 |
| 列表渲染 | 行内概念 tag 列 | 仅渲染基本字段 + 末尾「详情」按钮 |
| 详情数据源 | 列表行已带全量概念 | 列表行带简略版 → 抽屉打开时调 `/concepts/tab-by-symbol/{symbol}` 拿分组版 |
| 列表请求负载 | 略增（概念数组内嵌） | 略增（但远小于展开行的 KLine 数据） |
| 用户认知 | 概念密度高、表格拥挤 | 表格清爽、详情深入 |

### 4.7 数据流（完整链路）

```
用户操作流：
┌────────────────────────────────────────────────────────────────────────┐
│ ① 用户进入 StockInfoList 页面                                          │
│   loadStocks(with_concepts=true) ─→ GET /stock-panel/                   │
│   响应 items[].concepts: ConceptBrief[]                                │
│                                                                        │
│ ② 用户点击行末「详情」按钮（或行点击）                                  │
│   openDetailDrawer(row) → 抽屉打开                                     │
│   row.concepts 暂存于 drawer 内部（用于概念 Tab 骨架屏）                │
│                                                                        │
│ ③ 抽屉渲染：activeTab 默认 "info"，用户切到 "concepts"                  │
│   ConceptTab 挂载 → 触发 getConceptTabForSymbol(symbol)                │
│   ─→ GET /concepts/tab-by-symbol/{symbol}                              │
│   ─→ ConceptAppService.get_tab_content_for_symbol                      │
│   ─→ ConceptRepository.list_concepts_by_symbol_grouped (单 SQL JOIN)   │
│   ─→ 按 concept_type 分组 → ConceptTabContentVO                         │
│                                                                        │
│ ④ ConceptTab 渲染分组列表                                              │
│   每个 ConceptTag 可点击 → 预留 goConceptDetail(c)                       │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.8 删除/修改/新增文件清单（前端）

| 操作 | 文件 | 说明 |
|------|------|------|
| ✏️ 改 | `frontend/src/views/stock-info/StockInfoList.vue` | 移除 expand 列、移除概念列、新增详情按钮列、绑定抽屉状态 |
| ✏️ 改 | `frontend/src/views/stock-info/api.ts` | 新增 ConceptBrief / ConceptGroupedVO / ConceptTabContentVO / getConceptsBySymbol / getConceptTabForSymbol |
| ✏️ 改 | `frontend/src/views/stock-info/components/StockDetailDrawer.vue` | 新增「概念」Tab 挂载点、新增 prefetchConcepts prop |
| 🆕 增 | `frontend/src/views/stock-info/components/ConceptTab.vue` | 概念 Tab 内容组件（按类型分组渲染） |
| 🆕 增 | `frontend/src/views/stock-info/components/ConceptTag.vue` | 单个概念 Tag 组件（hover/click 反馈） |
| ❌ 删 | `frontend/src/views/stock-info/components/StockExpandRow.vue` | 展开行组件（被详情按钮取代） |
| 🆕 增 | `frontend/src/views/stock-info/components/IndicatorSwitcher.vue` | 预留：若 ConceptTab 需要可视化指标切换 |
| 🆕 增 | `frontend/src/views/stock-info/composables/useStockDetailDrawer.ts` | 可选：抽屉状态管理 composable（如果 StockInfoList 内联太复杂） |

---

## 五、API 汇总

| 方法 | 路径 | 用途 | 响应类型 |
|------|------|------|---------|
| GET  | `/api/v1/concepts/` | 分页列出概念 | `ConceptListVO` |
| GET  | `/api/v1/concepts/{name}` | 单概念详情（含成分股） | `ConceptDetailVO` |
| GET  | `/api/v1/concepts/by-symbol/{symbol}` | 单股票所属概念（**简略版**，抽屉预热用） | `list[ConceptBriefVO]` |
| GET  | `/api/v1/concepts/tab-by-symbol/{symbol}` | 🆕 单股票所属概念 Tab 内容（**按类型分组**，抽屉 Tab 专用） | `ConceptTabContentVO` |
| POST | `/api/v1/concepts/sync` | 触发全量同步 | `ConceptSyncResultVO` |
| GET  | `/api/v1/concepts/sync/status` | 同步状态 | `dict` |
| GET  | `/api/v1/stock-panel/?with_concepts=true` | 列表 + 嵌入简略概念（抽屉预热） | `StockPanelListVO` |

> **接口层次说明**（2026-09-24 修订）：
> - `/by-symbol/{symbol}` 仍保留，返回**简略版**（3 字段），用于详情抽屉快速打开时的"骨架屏"。
> - 新增 `/tab-by-symbol/{symbol}` 返回**分组版**（含 `concept_type` / `description`），用于抽屉「概念」Tab 渲染。
> - 两者共享同一个底层仓储方法 `list_concepts_by_symbol`，只是后者按 `concept_type` 在 Service 层分组。
> - 列表 `with_concepts=true` 仍然下发简略版概念，作为抽屉首屏（默认 Tab = "info"）的预热数据。

---

## 六、依赖注入配置

```python
# main.py（修改）
from infrastructure.repositories.concept_repository import ConceptRepoImpl
from infrastructure.collectors.akshare.concept_fetcher import AkShareConceptFetcher
from application.concept_service import ConceptAppService

# 注册 ConceptAppService
concept_repo = ConceptRepoImpl(session)
concept_fetcher = AkShareConceptFetcher()
concept_app_service = ConceptAppService(repo=concept_repo, fetcher=concept_fetcher)

# 注入到 StockPanelAppService
stock_panel_app_service = StockPanelAppService(
    panel_repo=panel_repo,
    concept_app_service=concept_app_service,  # 🆕
)
```

---

## 七、错误处理

| 错误 | HTTP 状态码 | 处理 |
|------|------------|------|
| `ConceptNotFoundError` | 404 | 返回 `{"detail": "概念 xxx 不存在"}` |
| `AKShareFetcher` 未注册 | 503 | 返回 `{"detail": "概念采集器未注册"}` |
| 同步超时 | 504 | 记录失败概念，返回部分结果 |
| 参数校验失败 | 422 | FastAPI 自动返回 Pydantic 错误 |

---

## 八、相关文档

- [README.md](../README.md) — 统一设计文档
- [01-domain-design.md](../01-domain-design.md) — 领域层
- [02-infrastructure-design.md](../02-infrastructure-design.md) — 基础设施层
- **[04-frontend-detail-design.md](../04-frontend-detail-design.md)** — 🆕 前端详情抽屉 + 强化按钮设计
- `docs/PlantUML/Concept/01-class.puml` — 类图
- `docs/PlantUML/Concept/02-data-flow.puml` — 数据流
