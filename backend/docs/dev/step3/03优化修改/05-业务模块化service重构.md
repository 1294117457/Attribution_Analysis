# 05 · Service 按业务模块重组

## 1. 需求

**用户原话**：
> "我看都是根据对象来定义 service 的，我想根据业务来定义 service，比如当前主要实现了 stockinfo 和 collectmanage 和正在做的 conceptboard 的功能，这里就是可以说改为定义 stock_info_service, collect_manage_service 这样吗，按照业务模块来区分，比如当前有"权限、股票信息、概念看板、等模块来区别"

**意图**：把当前"按 entity 切"的 service 改为"按业务模块切"。

---

## 2. 现状盘点

### 2.1 现有 service (`application/service/`)

| 文件 | 行数 | 主要 class | 主要职责 |
|------|------|-----------|---------|
| `auth_app_service.py` | 452 | `AuthAppService` | 用户/角色/权限/登录/注册/密码 |
| `collect_app_service.py` | 419 | `CollectAppService` | 采集任务/方案/任务组 |
| `concept_app_service.py` | 461 | `ConceptAppService` | 概念查询/实时/反向/大盘 |
| `kline_app_service.py` | 422 | `KlineAppService` | K线 + 指标 |
| `panel_app_service.py` | 150 | `StockPanelAppService` | 股票面板（归因分析入口） |
| `pool_app_service.py` | 272 | `StockPoolAppService` | 操作池 CRUD + 成员管理 |
| `pool_operation_app_service.py` | 188 | `PoolOperationAppService` | 池操作（后台派发 + 进度） |
| `stock_analysis_app_service.py` | 159 | `StockAnalysisAppService` | 股票归因分析聚合视图 |
| `stock_app_service.py` | 194 | `StockAppService` | 股票 CRUD + 元数据 |

> 命名规则：`<领域对象或子概念>_app_service.py` + `<对象名>AppService` 类

### 2.2 现有前端业务模块 (`frontend/src/views/`)

| 目录 | 主要页面 | 后端主要服务（依赖） |
|------|---------|------------------|
| `auth/` | LoginPage, ChangePassword, AccountPage | `AuthAppService` |
| `stock-info/` | StockInfoList, StockDetailDrawer, MiniKline | `StockAppService`, `KlineAppService`, `ConceptAppService` |
| `collect-manage/` | CollectManage, PlanCard, RealtimePanel | `CollectAppService` |
| `stock-pool/` | PoolList, PoolDetail, SignalSummaryPanel | `StockPoolAppService`, `PoolOperationAppService` |
| `concept-board/` | ConceptBoard, ConceptCardGrid, ConceptRankBoard, ConceptMembersList | `ConceptAppService` |
| `market/` | SectorBoard, MarketDashboard | （走 `MarketDashboard`，可能直接调 stock/concept） |
| `Dashboard.vue` | 总览 | 多个聚合 |

### 2.3 关键关系：service 与前端模块不一一对应

| 前端模块 | 后端 service（聚合） |
|---------|--------------------|
| `auth/` | `AuthAppService`（**1:1**） |
| `stock-info/` | `StockAppService` + `KlineAppService` + `ConceptAppService`（**聚合 3 个**） |
| `collect-manage/` | `CollectAppService`（**1:1**） |
| `stock-pool/` | `StockPoolAppService` + `PoolOperationAppService`（**聚合 2 个**） |
| `concept-board/` | `ConceptAppService`（**1:1，但同时 stock-info 也用它**） |
| `market/` | `ConceptAppService` + `StockAppService` 等（**聚合多个**） |

---

## 3. 重构方案

### 3.1 目标组织（按业务模块）

```
application/service/
├── auth_service.py            (原 auth_app_service)
├── stock_info_service.py      ← 合并: stock + kline + stock_analysis
├── collect_manage_service.py  (原 collect_app_service)
├── stock_pool_service.py      ← 合并: pool + pool_operation
├── concept_board_service.py   ← 从 concept_app_service 拆出大盘 + kline
└── shared/
    └── concept_service.py     (原 concept_app_service 中"查询/反查/详情"被 stock_info/market 共用的部分)
```

**对应关系**：

| 前端模块 | 后端 service（重组后）|
|---------|--------------------|
| auth | `AuthService` |
| stock-info | `StockInfoService` (含 K 线 + 分析) |
| collect-manage | `CollectManageService` |
| stock-pool | `StockPoolService` (含操作派发) |
| concept-board | `ConceptBoardService` (含 K 线 + 实时) |
| market | `ConceptService` (共享) |

### 3.2 推荐方案 vs 备选方案

`★ 不确定点 Q4 ─────────────────────────────────────`
- **方案 A**：全量重组（上述目录结构）— 改动大，但边界清晰
- **方案 B**：渐进迁移 — 保留 `application/service/*_app_service.py`，**新建** `application/service/modules/<business_name>.py`，只搬概念大盘相关逻辑进去（最小可用）
- **方案 C**：仅"目录嵌套，不改类名" — 创建 `application/service/{auth,stock_info,collect_manage,...}/` 子目录，每个子目录放原 service 文件（仅物理位置变，import 全部修改）
- `─────────────────────────────────────────────────`

### 3.3 推荐方案 B（渐进迁移）

**优势**：
- 不破坏现有 DI（`di.py` 已有 9 个工厂对应 9 个 service）
- 一次性只改一个业务模块（先做概念大盘，因用户正在做的）
- 验证模板后批量推广

**步骤**（以"概念大盘"为例）：

#### 3.3.1 新建模块目录

```
application/service/modules/
├── __init__.py
└── concept_board_service.py     # 仅装概念大盘相关方法
```

#### 3.3.2 抽离方法

原 `ConceptAppService` 拆为：
- `ConceptAppService.query_board()` / `query_board_members()` / `get_concept_kline()`（新增）→ 移到 `ConceptBoardService`
- 保留：`query_concepts` / `get_concept_detail` / `get_tab_content_for_symbol` / `get_tab_content_with_live` / `get_quotes` / `list_for_symbol*` / `fetch_concepts_by_stock`（共用）

#### 3.3.3 共用方法怎么办？

- **方案 B-1**：让 `ConceptBoardService` 注入 `ConceptAppService`，调用其底层查询
- **方案 B-2**：抽出更细粒度的"共享服务"（如 `SharedConceptQueryService`），两个 service 都注入

**推荐 B-1**（更简单）：
```python
class ConceptBoardService:
    def __init__(self, concept_app_service: ConceptAppService, realtime: RealtimeQueryPort):
        self._concept_svc = concept_app_service
        self._realtime = realtime

    async def query_board(self, req):
        # 复用概念服务的方法,加上大盘特有的逻辑
        ...
```

#### 3.3.4 DI 注册新增

`infrastructure/config/di.py` 增加：
```python
def get_concept_board_app_service(
    session: AsyncSession = Depends(get_db),
) -> ConceptBoardService:
    registry = get_registry()
    return ConceptBoardService(
        concept_app_service=ConceptAppService(
            repo=ConceptRepoImpl(session),
            fetcher=registry.get(ConceptFetcher),
            realtime=get_realtime_query_framework(),
        ),
        realtime=get_realtime_query_framework(),
    )
```

#### 3.3.5 路由切换

`route/api/v1/concept.py` 中大盘相关路由（`/concept-board`, `/concept-board/members`, `/kline`）从 Depends(`get_concept_app_service`) 改为 Depends(`get_concept_board_app_service`)，调用 `concept_board_service.query_board(...)`。

#### 3.3.6 其他 service 不动

- `AuthAppService` / `StockAppService` / `KlineAppService` / `StockPanelAppService` / `StockPoolAppService` / `PoolOperationAppService` / `CollectAppService` / `StockAnalysisAppService` 保持现状
- 老的 `ConceptAppService` 也保留（其共用方法仍在用）

### 3.4 推广（如方案 B 跑通）

按"业务模块"再迁：
- `StockInfoService` 合并 `StockAppService` + `KlineAppService` + `StockAnalysisAppService`
- `StockPoolService` 合并 `StockPoolAppService` + `PoolOperationAppService`
- ...

每一轮按"先建新 → 路由切换 → 老 service 标记 deprecated → 后续版本删除"。

---

## 4. 测试用例

| 场景 | 期望 |
|------|------|
| 概念大盘所有功能（默认+筛选+成员+新 K 线）| 行为完全不变 |
| 股票信息所有功能（含 K 线/分析）| 行为完全不变 |
| 操作池所有功能 | 行为完全不变 |
| 采集管理所有功能 | 行为完全不变 |
| 登录/注册/权限 | 行为完全不变 |
| 性能 | 重组后不能比重组前慢（同步调用链不变，仅 DI 多一层） |

---

## 5. 影响范围

| 范围 | 改动量 |
|------|--------|
| `application/service/modules/concept_board_service.py` | **新增** 1 文件 |
| `application/service/concept_app_service.py` | **删除 3 个大盘方法**（搬到新 service） |
| `infrastructure/config/di.py` | **+1 工厂函数**（`get_concept_board_app_service`） |
| `route/api/v1/concept.py` | **改 3 个路由** 的 Depends（/concept-board, /concept-board/members, /kline） |
| 其他 service | **不动** |
| 前端 | **不动**（API 不变） |
| DI | 增量 |
| 风险 | **低**（增量，原 service 方法保留时老路由仍可用） |

---

## 6. 实施步骤（预估 4-6 小时）

### 阶段 1：建立概念大盘模块（先跑通）

1. 新建 `application/service/modules/__init__.py`
2. 新建 `application/service/modules/concept_board_service.py`，把 `query_board` / `query_board_members` / `get_concept_kline`（03 文档里规划）搬过来
3. 写 `get_concept_board_app_service` 工厂到 `di.py`
4. 改 `route/api/v1/concept.py` 中大盘路由的 Depends
5. 跑：
   ```bash
   curl http://localhost:8000/api/v1/concepts/concept-board?type_filter=all
   curl http://localhost:8000/api/v1/concepts/concept-board/members?concept_id=1
   ```
6. 跑前端 `npm run dev`，打开 `/home/concepts` 看效果

### 阶段 2（可选）：再迁 stock-info

合并 `StockAppService` + `KlineAppService` + `StockAnalysisAppService`，按同样模板。

### 阶段 3（可选）：再迁 stock-pool

合并 `StockPoolAppService` + `PoolOperationAppService`。

### 阶段 4（可选）：清理 deprecated

所有模块迁完后，删除 `application/service/{concept,...}_app_service.py` 中已搬空的方法，统一为 `application/service/modules/<business>_service.py`。

---

## 7. 命名约定（建议）

| 原 | 新 |
|----|---|
| `auth_app_service.py` | `auth_service.py` 或 `modules/auth_service.py` |
| `AuthAppService` | `AuthService`（去掉 `_app_` 中缀） |
| `_app_service` 后缀 | `_service` 后缀（DDD 中 application 已隐含 service 含义） |

> 也可保留 `_app_service` 兼容老 import；推荐一起改一致。

---

## 8. 不推荐的方案

- **方案 X**：直接拆 service 文件、保留 `_app_service` 后缀 — 纯物理位置变化，无业务意义
- **方案 Y**：把 service 全下沉到 `domain/service/` — 违反 DDD 分层，service 是 application 层职责
- **方案 Z**：每个方法一个文件 — 过度细化，找代码反而困难