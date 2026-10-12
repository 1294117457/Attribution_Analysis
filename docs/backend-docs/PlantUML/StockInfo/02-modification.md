# StockInfo 列表 N+1 优化 — 修改文档

> 目标：消除 `StockInfoList.vue` 加载股票列表时的 N+1 反向查询，将 **21 次 HTTP 请求** 压缩为 **1 次**。
> 文档版本：v1  ·  日期：2026-09-18

---

## 一、问题描述

### 1.1 现象（来自 `terminals/1.txt:531-565`）

打开 `StockInfoList.vue` 页面（默认 `page_size=20`）后端访问日志：

```text
GET /api/v1/pools?limit=100                                           200
GET /api/v1/stocks/meta                                              200
GET /api/v1/stocks/?page=1&page_size=20&list_status=L                200
GET /api/v1/pools/by-symbol/000008                                   200
GET /api/v1/pools/by-symbol/000006                                   200
GET /api/v1/pools/by-symbol/000007                                   200
GET /api/v1/pools/by-symbol/000002                                   200
GET /api/v1/pools/by-symbol/000009                                   200
GET /api/v1/pools/by-symbol/000001                                   200
GET /api/v1/pools/by-symbol/000012                                   200
GET /api/v1/pools/by-symbol/000011                                   200
GET /api/v1/pools/by-symbol/000016                                   200
...（共 20 次 by-symbol 请求，未截完）
```

**总计 1 次列表 + 20 次反向查询 = 21 次请求 / 页**。用户翻页时按需重新触发。

### 1.2 根因（前端）

```1:30:frontend/src/views/stock-info/StockInfoList.vue
async function loadAllStockPools() {
  const symbols = stocks.value.map((s) => s.symbol)
  await Promise.all(
    symbols.map(async (symbol) => {
      try {
        const result = await poolStore.findPoolsBySymbol(symbol)
        symbolPoolsMap.value[symbol] = result.pools
      } catch {
        symbolPoolsMap.value[symbol] = []
      }
    })
  )
}
```

`stocks.value` 是当前页 20 只股票，对每只都发起一次 `/pools/by-symbol/{symbol}`。换页、筛选变化、切回页面都会重复执行。

### 1.3 后端对应调用链

```text
前端  GET /stocks/?page=1&page_size=20
   └─► StockAppService.query_stocks()
         └─► StockRepo.list_with_kline_stats_paginated()   ──► 1×SQL（股票 + K线统计 + 最新估值 + 利润率）
         └─► 返回 StockQueryItemResponse[]

前端  Promise.all(symbols.map(s => poolStore.findPoolsBySymbol(s)))
   └─► for each symbol:
         └─► PoolAppService.find_pools_by_symbol()
               └─► PoolRepo.find_pools_by_symbol()          ──► 1×SQL JOIN
         （共 N 次）
```

**两段请求本可以合并**：`stock_infos` ↔ `stock_pool_members` 是天然的多对一关系，关系方向并不影响"批量带出 pool 信息"的实现。

### 1.4 量化影响

| 指标 | 现状 | 优化后 |
|------|------|--------|
| 单页 HTTP 请求数 | 21 | 1 |
| 单页 DB 查询数 | 21（1 列表 + 20 反向） | 2（1 列表 + 1 批量反向） |
| 前端 Promise.all 调度 | 20 个并发 | 0 |
| 翻页 / 切筛选 / 重进页面 | 重发 20 次 by-symbol | 不再额外请求 |
| 总后端 QPS（100 用户、5 页/分钟） | 100×21×5 = **10,500** | 100×1×5 = **500** |

---

## 二、修改方案

### 2.1 设计思路

将"股票列表"和"每只股票所属池"在**同一份 API 响应**中返回，由后端用 **2 次 SQL**（1 次列表 + 1 次批量反向）实现，避免前端逐个请求。

### 2.2 候选方案对比

| 方案 | 描述 | 优点 | 缺点 | 推荐度 |
|------|------|------|------|--------|
| **A. 单条 SQL + PostgreSQL JSON 聚合** | `LEFT JOIN stock_pool_members` 后用 `json_agg(json_build_object(...))` 聚合成 `pools_json` 字段 | 真·1 次 SQL | SQL 复杂、可读性差、需要 `GROUP BY` 调整、不易加 `with_pools` 开关 | ⭐⭐ |
| **B. 2 次 SQL + 应用层合并** ⭐ | 列表查询拿到 symbols → 一次 `WHERE symbol IN (...)` 批量拿池 → Python 端 zip | SQL 简单、可维护性好、与现有列表查询解耦 | 需要在应用层组装 | ⭐⭐⭐⭐⭐ |
| C. 前端缓存合并 | 仍发 20 次，但用 `localStorage` / IndexedDB 缓存 | 后端无改动 | 首屏仍 21 请求、跨用户失效不一致、维护成本高 | ⭐ |

**采用方案 B**。理由：复用现有 `list_with_kline_stats_paginated` 不动，新增一个轻量的"批量反向查询"仓储方法，应用层做组装，边界清晰。

### 2.3 是否需要改表

**不需要任何 schema 变更**。`stock_infos`、`stock_pools`、`stock_pool_members` 三张表都不动。

变更全部在：
- 仓储实现（新增方法）
- 应用服务（编排合并）
- DTO（新增字段 / 轻量 VO）
- 前端（消费新字段）
- 路由（新增 query 参数）

---

## 三、详细修改清单

> 图例：🆕 新增 · ✏️ 修改 · ⚪ 不变

### 3.1 持久层（数据库 / ORM）⚪

三张表（`stock_infos`、`stock_pools`、`stock_pool_members`）和 ORM 模型（`StockInfoDB`、`StockPoolDB`、`StockPoolMemberDB`）**完全不变**。

### 3.2 领域层

#### `domain/stock_info/entity.py` ⚪
`StockInfo` 聚合根本身**不变**。聚合根的字段集合是面向"股票本身"的元数据，不应混入"所属池"这种关系数据。

#### `domain/stock_info/value_objects.py` 🆕 新增值对象
在文件末尾新增（不动现有 `Industry` / `Market`）：

```python
@dataclass(frozen=True)
class StockPoolBrief(ValueObject):
    """股票所属池的轻量快照（值对象，不可变）

    仅包含列表展示所需字段，避免反向查询时拉取完整 StockPool 聚合根。
    用于合并查询场景，不替代 StockPool。
    """
    pool_id: int
    name: str
    pool_type: str  # watchlist/industry/strategy/custom

    def _get_values(self) -> tuple:
        return (self.pool_id, self.name, self.pool_type)
```

#### `domain/stock_info/schemas.py` ⚪
`StockInfoVO`（领域 VO，单股详情用）**不变**。列表项的 `pools` 字段属于"复合查询结果"，应放在应用层 DTO 而非领域 VO。

#### `domain/stock_pool/repository.py` 🆕 新增接口方法

在 `StockPoolRepository` Protocol 中新增：

```python
async def list_membership_by_symbols(
    self, symbols: list[str]
) -> dict[str, list[StockPoolBrief]]:
    """按 symbols 批量查询所属池（不含 archived 池）

    返回 symbol -> StockPoolBrief 列表 的映射。
    未出现在返回 dict 中的 symbol 表示未加入任何池。
    """
    ...
```

保留旧方法 `find_pools_by_symbol(symbol)`（单股详情 / 其他场景）。

#### `domain/stock_pool/value_objects.py` ⚪
现有 `PoolMember` / `PoolType` 等值对象不变。新增的 `StockPoolBrief` 放在 `domain/stock_info/value_objects.py`（属于 stock_info 上下文的展示需求）。

### 3.3 仓储实现层

#### `infrastructure/repositories/pool_repository.py` 🆕 新增方法

在 `PoolRepoImpl` 中新增：

```python
async def list_membership_by_symbols(
    self, symbols: list[str]
) -> dict[str, list[StockPoolBrief]]:
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
        .order_by(
            StockPoolDB.is_default.desc(),
            StockPoolDB.updated_at.desc(),
        )
    )
    result = await self._session.execute(stmt)
    rows = result.all()

    out: dict[str, list[StockPoolBrief]] = {s: [] for s in symbols}
    for row in rows:
        out[row.symbol].append(
            StockPoolBrief(
                pool_id=row.id,
                name=row.name,
                pool_type=row.pool_type,
            )
        )
    return out
```

**性能**：单次 SQL，symbols 数量 ≤ 500（与 `page_size=500` 上限对齐），可命中 `ix_stock_pool_members_symbol`（`symbol` 列已加索引）。

#### `infrastructure/repositories/stock_repository.py` ⚪
**不变**。

### 3.4 应用服务层

#### `application/dto/stock.py` ✏️ 修改 + 🆕 新增

```python
# 🆕 新增轻量 VO
class PoolMembershipVO(BaseModel):
    """列表场景下的池信息（轻量，不含 color/icon/member_count）"""
    pool_id: int
    name: str
    pool_type: str

# ✏️ 修改 StockQueryRequest：新增可选参数
class StockQueryRequest(BaseModel):
    q: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    exchange: Optional[str] = None
    is_hs: Optional[str] = None
    list_status: Optional[str] = "L"
    exclude_st: Optional[bool] = None
    min_total_mv: Optional[float] = None
    with_pools: bool = False                # 🆕
    page: int = 1
    page_size: int = 20

# ✏️ 修改 StockQueryItemResponse：新增 pools 字段
class StockQueryItemResponse(BaseModel):
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
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end: Optional[date] = None
    latest_close: Optional[float] = None
    total_mv: Optional[float] = None
    pe_ttm: Optional[float] = None
    profit_margin: Optional[float] = None
    pools: list[PoolMembershipVO] = Field(    # 🆕
        default_factory=list,
        description="所属操作池（with_pools=True 时填充）",
    )
```

#### `application/dto/pool.py` ⚪
**不变**（`PoolVO` 是完整池信息，给详情用；列表场景用新的轻量 `PoolMembershipVO`）。

#### `application/stock_service.py` ✏️ 修改

`StockAppService` 构造函数和 `query_stocks()` 方法变更：

```python
class StockAppService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo: StockInfoRepository = StockRepoImpl(session)
        self._pool_repo = StockPoolRepoImpl(session)        # 🆕 注入

    async def query_stocks(self, request: StockQueryRequest) -> StockQueryResponse:
        # 1) 已有：拿股票列表（含 K线统计 + 最新估值 + 利润率）
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
            briefs_map = await self._pool_repo.list_membership_by_symbols(symbols)
            pool_map = {
                sym: [
                    PoolMembershipVO(
                        pool_id=b.pool_id,
                        name=b.name,
                        pool_type=b.pool_type,
                    )
                    for b in briefs
                ]
                for sym, briefs in briefs_map.items()
            }

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

#### `application/pool_service.py` ⚪
**不变**。`find_pools_by_symbol()` 仍然保留给详情页用。

### 3.5 路由层

#### `route/api/v1/stock.py` ✏️ 修改

`GET /stocks/` 接口新增 query 参数：

```python
@router.get("/", summary="股票列表（分页+多维筛选）")
async def query_stocks(
    q: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    market: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    is_hs: Optional[str] = Query(None),
    list_status: Optional[str] = Query("L"),
    exclude_st: Optional[bool] = Query(None),
    min_total_mv: Optional[float] = Query(None, ge=0),
    with_pools: bool = Query(False, description="是否在响应中附带所属操作池"),  # 🆕
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    service: StockAppService = Depends(get_stock_service),
):
    request = StockQueryRequest(
        q=q, industry=industry, market=market,
        exchange=exchange, is_hs=is_hs,
        list_status=list_status, exclude_st=exclude_st,
        min_total_mv=min_total_mv,
        with_pools=with_pools,           # 🆕
        page=page, page_size=page_size,
    )
    response = await service.query_stocks(request)
    return R.ok(response.model_dump())
```

`GET /pools/by-symbol/{symbol}` 路由**不变**（仍保留给其他场景）。

### 3.6 前端

#### `frontend/src/views/stock-info/api.ts` ✏️ 修改

```typescript
export interface PoolMembership {
  pool_id:    number
  name:       string
  pool_type:  string
}

export interface StockInfo {
  // ... 现有字段
  pools: PoolMembership[]        // 🆕
}

export interface StockQueryParams {
  // ... 现有字段
  with_pools?: boolean           // 🆕
}

export const queryStocks = (params: StockQueryParams = {}) =>
  http.get<PaginatedResponse<StockInfo>>('/stocks/', { params }).then(unwrap)
```

#### `frontend/src/views/stock-info/StockInfoList.vue` ✏️ 修改

删除：`symbolPoolsMap` / `loadAllStockPools()` / `poolStore.fetchPools()` 调用。

```vue
<script setup lang="ts">
// 删 const symbolPoolsMap = ref<Record<string, Pool[]>>({})
// 删 async function loadAllStockPools() { ... }

// loadStocks 改为带 with_pools=true
const data = await queryStocks({ ...params, with_pools: true })

// getStockPools 直接读 row.pools
function getStockPools(symbol: string): PoolMembership[] {
  const stock = stocks.value.find((s) => s.symbol === symbol)
  return stock?.pools ?? []
}

// onMounted 不再调 loadAllStockPools 和 poolStore.fetchPools（如果只为列表展示）
onMounted(async () => {
  await Promise.all([loadMeta(), loadStocks()])
})
</script>
```

模板 `v-for="p in getStockPools(row.symbol).slice(0, 3)"` 处把 `Pool` 类型替换为 `PoolMembership`（少字段不影响模板使用）。

`AddToPoolDialog` / `onPoolDone()` 完成后，调用 `loadStocks()` 重刷（连带 `pools` 字段自动更新）即可，不需要单独 `loadAllStockPools()`。

---

## 四、兼容性 & 回滚

### 4.1 向后兼容

- `with_pools` 默认为 `false` → 旧请求行为不变，响应中 `pools` 字段是空列表 `[]`
- 旧的 `GET /pools/by-symbol/{symbol}` 接口保留，详情页 / 其他场景继续可用
- 前端可分阶段切换：
  1. 后端先上线（新接口就绪）
  2. 前端切到 `with_pools=true`，删除 `loadAllStockPools`
  3. 观察一段时间无问题后，可在后续 PR 中删除旧 `find_pools_by_symbol` 路由

### 4.2 回滚方案

- 后端：`with_pools` 默认 false，部署即可禁用
- 前端：保留 `findPoolsBySymbol` 调用代码（在分支中），一行 revert 即可恢复旧行为
- 不涉及表结构变更，无 DDL 回滚成本

### 4.3 风险评估

| 风险 | 影响 | 缓解 |
|------|------|------|
| `pools` 字段被前端误用为完整 Pool | 低 | 前端 TypeScript 类型只暴露 `PoolMembership`，无 color/icon |
| `IN (:symbols)` 列表过长 | 中 | `page_size ≤ 500`，且 SQLAlchemy 自动分批参数绑定；如真出现可加 LIMIT |
| 批量反向查询与列表查询不在同一事务 | 低 | 只读快照场景下可接受；如需强一致可包在 `BEGIN READ ONLY` 事务中（建议 v2 视情况引入） |

---

## 五、实施步骤（建议顺序）

1. **后端 domain 层**
   - `domain/stock_info/value_objects.py`：新增 `StockPoolBrief`
   - `domain/stock_pool/repository.py`：Protocol 新增 `list_membership_by_symbols`

2. **后端 infrastructure 层**
   - `infrastructure/repositories/pool_repository.py`：实现 `list_membership_by_symbols`

3. **后端 application 层**
   - `application/dto/stock.py`：新增 `PoolMembershipVO`、修改 `StockQueryRequest`、`StockQueryItemResponse`
   - `application/stock_service.py`：注入 `StockPoolRepoImpl`，修改 `query_stocks`

4. **后端 route 层**
   - `route/api/v1/stock.py`：新增 `with_pools` query 参数

5. **后端测试**
   - 单元：mock pool_repo 验证合并逻辑
   - 集成：启服务，`curl /stocks/?with_pools=true&page_size=5` 看 `pools` 字段

6. **前端**
   - `frontend/src/views/stock-info/api.ts`：新增 `PoolMembership` 类型 / `StockInfo.pools` / `with_pools` 参数
   - `frontend/src/views/stock-info/StockInfoList.vue`：删除 `loadAllStockPools`，改 `queryStocks` 带 `with_pools=true`，`getStockPools` 改读 `row.pools`

7. **联调**
   - 打开 `StockInfoList.vue`，DevTools Network 应只有 1 个 `/stocks/?...` 请求
   - 加入 / 移除池后，确认列表 `pools` 标签同步刷新

---

## 六、变更统计

| 层 | 文件 | 新增行 | 修改行 |
|----|------|--------|--------|
| Domain | `domain/stock_info/value_objects.py` | ~15 | 0 |
| Domain | `domain/stock_pool/repository.py` | ~10 | 0 |
| Infrastructure | `infrastructure/repositories/pool_repository.py` | ~35 | 0 |
| Application | `application/dto/stock.py` | ~10 | ~5 |
| Application | `application/stock_service.py` | ~25 | ~10 |
| Route | `route/api/v1/stock.py` | ~3 | ~5 |
| Frontend | `frontend/src/views/stock-info/api.ts` | ~10 | ~5 |
| Frontend | `frontend/src/views/stock-info/StockInfoList.vue` | ~5 | ~25 |
| **合计** | — | **~113** | **~50** |

---

## 七、后续可优化项（不在本次范围）

- `StockQueryItemResponse` 当前 fields 多（22 个 + pools），可考虑扁平化或按 `with_*` 拆分多个端点
- 列表查询可加入 `include_kline_stats: bool` 控制是否做 K 线聚合（部分场景不需要）
- `IN (:symbols)` 长列表场景可改为 keyset 分页 + 流式响应（SSE）
