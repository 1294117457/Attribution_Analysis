# 概念板块接入方案（AKShare 数据源）

> 编写日期：2026-09-24
> 所属阶段：`06gainian`（独立排期，与 `04protocol` / `05listn1` 解耦）
>
> 配套 UML（权威）：
> - `docs/PlantUML/Concept/01-class.puml` — 跨层类图修改概览
> - `docs/PlantUML/Concept/02-data-flow.puml` — 概念反查数据流（4 层 + 2 表）
> - `docs/PlantUML/Concept/03-sync-data-flow.puml` — 概念同步数据流（4 层 + 3 表）
>
> 详细设计文档：
> - [01-domain-design.md](./01-domain-design.md) — 领域层 BO / VO / Entity / Repository Protocol
> - [02-infrastructure-design.md](./02-infrastructure-design.md) — 数据库 / ORM / Repository 实现 / AKShare Collector
> - [03-application-and-route-design.md](./03-application-and-route-design.md) — DTO / Service / Route / 前端
>
> PlantUML 渲染规范：`docs/config/uml类图设计规范.md`

---

## 一、背景与目标

### 1.1 现状缺口

`StockInfoList.vue` 当前展示的标签维度过少：

| 已有列 | 缺失 |
|------|------|
| 行业（来自 Tushare `stock_basic.industry`，1:1 字段） | **概念板块**（来自东方财富 / 同花顺，N:M 关系） |

概念板块（如"人形机器人"、"中字头"、"高股息"等）是**归因分析**和**板块轮动**的核心维度，
用户在选股时常以"概念标签"作为筛选条件。

### 1.2 为什么用 AKShare 而不是 Tushare

| 数据源 | 概念板块积分 | 数据质量 | 维护成本 |
|------|------------|--------|---------|
| **Tushare Pro** | 需要 **6000 积分** | 高（机构维护） | 同步低频 |
| **AKShare** | **免费开源** | 中（爬取东方财富 / 同花顺） | 第三方接口有变更风险 |

**结论**：本项目用户当前 Tushare 积分不足 6000，**优先用 AKShare 作为唯一概念数据源**，
后续若积分到位可切换到 Tushare（数据流不变，仅替换 Collector 实现）。

### 1.3 目标

1. 在 `StockInfoList.vue` 行内的「详情」按钮点击后，**右侧抽屉展示**该股票所属的概念列表（按 `concept_type` 分组）。
2. 提供概念的全量同步、概念筛选、概念-股票反查等基础 API。
3. 数据流遵循现有 ACL + Registry + Protocol 模式，**新增代码不破坏任何现有模块**。

> **设计变更说明**（2026-09-24 修订）：
> 早期方案曾在表格中新增「概念」列（最多 3 个 tag + `+N` 溢出）。
> 经过交互走查后调整为：
> - **列表更聚焦**：表格只承担"快速浏览 + 多维筛选"职责，不嵌入概念列表。
> - **详情更深入**：右侧抽屉（`StockDetailDrawer`）新增「概念」Tab，展示完整概念列表（按类型分组、可点击跳转）。
> - **行操作更显眼**：移除 `el-table-column type="expand"`（点击展开 KLine 看板），改为在固定列右侧放置一个**显眼的「详情」按钮**，按钮态而非行点击态，避免与表格的多选 / 排序 / 行高亮等交互冲突。
>
> 详细前端设计见 [04-frontend-detail-design.md](./04-frontend-detail-design.md)。

---

## 二、核心决策 ⭐ 数据治理

### 2.1 议题：概念数据放哪里？

> **关键问题**：概念数据应该「合并到 stock_infos 表」还是「独立成新表」？

#### 方案 A：合并到 stock_infos（denormalize）

```sql
-- 尝试方案
ALTER TABLE stock_infos ADD COLUMN concepts JSONB;  -- 存 ["人形机器人", "AI算力", ...]
```

#### 方案 B：独立聚合根（推荐 ⭐）

新建两张表：

```sql
CREATE TABLE concepts (
  id           SERIAL PRIMARY KEY,
  name         VARCHAR(100) NOT NULL,
  source       VARCHAR(10)  NOT NULL DEFAULT 'em',  -- 'em' / 'ths'
  concept_type VARCHAR(50),
  description  TEXT,
  stock_count  INTEGER NOT NULL DEFAULT 0,
  is_active    BOOLEAN  NOT NULL DEFAULT TRUE,
  first_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
  last_synced_at TIMESTAMP,
  UNIQUE(name, source)
);

CREATE TABLE stock_concept_members (
  symbol     VARCHAR(10) NOT NULL,
  concept_id INTEGER     NOT NULL REFERENCES concepts(id),
  joined_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
  source     VARCHAR(10) NOT NULL DEFAULT 'em',
  PRIMARY KEY (symbol, concept_id)
);
```

### 2.2 推荐方案 B 的理由

| 维度 | 方案 A（合并到 stock_infos） | 方案 B（独立聚合）⭐ |
|------|------|------|
| **范式** | ❌ 违反 1NF（多值字段存 JSONB） | ✅ 严格 3NF |
| **关系性质** | ❌ 概念是 N:M，硬塞 1:1 表语义混乱 | ✅ 概念是独立聚合根，N:M 由 `stock_concept_members` 显式表达 |
| **同步频率** | ❌ 概念每周变 → 频繁 UPDATE stock_infos，触发行级锁 | ✅ 概念变更只更新 `concepts` / `stock_concept_members`，互不影响 stock_infos |
| **数据源** | ❌ stock_infos 来源 Tushare（同步低频），概念来源 AKShare（同步高频），混在一起违反 SRP | ✅ 每个聚合根对应单一数据源 |
| **查询模式** | ❌ "查询某概念下的所有股票" 需要扫描 stock_infos 全表 | ✅ `SELECT ... WHERE concept_id = ?` 命中索引 |
| **复用** | ❌ 概念字段与其他 stock_info 字段耦合 | ✅ 概念相关功能（列表筛选 / 详情页 / 选股器）共享同一张表 |
| **迁移一致性** | ❌ Tushare stock_basic 接口没有 concepts 字段，每次 upsert 都要特殊处理 | ✅ stock_info 不感知概念存在，互不污染 |
| **既有模式** | ❌ 与现有"pool + pool_member"模式不一致 | ✅ **与现有 `stock_pools + stock_pool_members` 模式 1:1 对齐** |

### 2.3 与 Pool 模式的复用性

```
现有 Pool 模式（运营层）          新 Concept 模式（数据源层）
─────────────────────────────────   ─────────────────────────────────
stock_pools                         concepts
  ├ id {PK}                           ├ id {PK}
  ├ name                              ├ name {UQ}
  ├ pool_type                         ├ source ('em'/'ths')
  ├ is_archived                       ├ is_active
  ├ ... (icon/color/sort_order)       └ ... (stock_count/last_synced_at)
  └ 由用户/管理员维护                 └ 由 AKShare 采集器维护

stock_pool_members                  stock_concept_members
  ├ pool_id {FK}                      ├ concept_id {FK}
  ├ symbol {FK}                       ├ symbol {FK}
  └ joined_at                         └ joined_at
```

**结论**：复用相同的"聚合 + 关联表"两段式架构，对开发者和 reviewer 都友好。

---

## 三、整体架构

### 3.1 文件清单

```
backend/
├── docs/
│   ├── dev/06gainian/                       ← 本设计文档目录
│   │   ├── README.md                        ← 本文件
│   │   ├── 01-domain-design.md
│   │   ├── 02-infrastructure-design.md
│   │   ├── 03-application-and-route-design.md
│   │   └── 04-frontend-detail-design.md      ← 🆕 前端详情抽屉 + 按钮设计
│   └── PlantUML/Concept/
│       ├── 01-class.puml                    ← 跨层修改概览
│       └── 02-data-flow.puml                ← 概念反查数据流
│
├── src/
│   ├── domain/concept/                      ← 🆕 新增聚合根
│   │   ├── __init__.py
│   │   ├── entity.py                        ← Concept, ConceptMember
│   │   ├── value_objects.py                 ← ConceptBriefVO (frozen)
│   │   ├── schemas.py                       ← ConceptListBO, ConceptStockBO
│   │   ├── repository.py                    ← ConceptRepository (Protocol)
│   │   └── exceptions.py                    ← ConceptNotFoundError
│   │
│   ├── infrastructure/
│   │   ├── collectors/akshare/              ← 🆕 AKShare 适配器
│   │   │   ├── __init__.py
│   │   │   ├── fetcher.py                   ← AkShareFetcher
│   │   │   └── parser.py                    ← AkShareConceptParser
│   │   │
│   │   ├── database/models/concept.py       ← 🆕 ORM
│   │   ├── repositories/concept_repository.py  ← 🆕 Repo 实现
│   │   ├── collectors/registry.py           ← ✏️ 注册 ConceptFetcher
│   │   └── main.py                          ← ✏️ import 新 ORM + Collector
│   │
│   ├── application/
│   │   ├── dto/concept.py                   ← 🆕 DTO
│   │   ├── concept_service.py               ← 🆕 应用服务
│   │   ├── dto/panel.py                     ← ✏️ StockPanelItemVO 新增 concepts 字段
│   │   ├── panel_service.py                 ← ✏️ 编排 list_concepts_by_symbols
│   │   └── repositories/panel_compose_repository.py  ← ✏️ 委托给 ConceptRepository
│   │
│   └── route/api/v1/concept.py              ← 🆕 REST 端点

frontend/
└── src/views/stock-info/
    ├── StockInfoList.vue                    ← ✏️ 移除概念列；强化详情按钮
    ├── api.ts                               ← ✏️ 增加 ConceptBrief / 概念分组 VO 类型
    └── components/
        ├── StockDetailDrawer.vue            ← ✏️ 新增「概念」Tab（按类型分组）
        ├── ConceptTab.vue                   ← 🆕 概念 Tab 内容组件
        ├── ConceptTag.vue                   ← 🆕 单个概念 Tag（可点击跳概念详情）
        ├── StockExpandRow.vue               ← ❌ 删除（展开行被详情按钮取代）
        └── ...（既有 AddToPoolDialog / KLineDrawerTab / MiniKlineChart 不变）
```

### 3.2 跨层依赖图

```
                    ┌──────────────────────────┐
                    │  AkShare（数据源）        │
                    │  东方财富 / 同花顺         │
                    └────────────┬─────────────┘
                                 │ HTTP（ak.stock_board_*）
                                 ▼
            ┌────────────────────────────────────┐
            │  AkShareFetcher（采集层）          │
            │  → ConceptListBO / ConceptStockBO │
            └────────────────┬───────────────────┘
                             │ via FetcherRegistry
                             ▼
            ┌────────────────────────────────────┐
            │  ConceptRepository（基础设施层）   │
            │  → concepts / stock_concept_members│
            └────────────────┬───────────────────┘
                             │ ↑↓ ORM
            ┌────────────────────────────────────┐
            │  ConceptAppService（应用层）       │
            │  → sync_concepts / query_concepts  │
            │  → list_for_symbol(symbols)        │
            └─────┬──────────────────────┬───────┘
                  │                      │
                  ▼                      ▼
       StockPanelComposeRepo       ConceptRouter
       (list_concepts_by_symbols)  /api/v1/concepts/*
                  │
                  ▼
       StockPanelItemVO.concepts
       (前端表格展示)
```

---

## 四、数据同步策略

### 4.1 首次同步（全量）

| 步骤 | 接口 | 频率 |
|------|------|------|
| 1. 拉所有概念清单 | `ak.stock_board_concept_name_em()` | 一次性 |
| 2. 对每个概念拉成分股 | `ak.stock_board_concept_cons_em(symbol=name)` | 一次性，约 500 次 |
| 3. 写入 DB | `ConceptRepository.upsert_members` | 一次性 |

**预计耗时**：500 概念 × 0.5s sleep ≈ 4-5 分钟（单线程），并发可压缩到 1-2 分钟。

**建议**：作为后台 collect_task 任务（参考 `infrastructure/tasks/operation_dispatcher.py`），
避免阻塞 HTTP 入口。

### 4.2 增量同步

| 频率 | 内容 |
|------|------|
| **每周一次**（建议） | 重新跑 `fetch_concept_list`，对比新增/退出的概念，`stock_concept_members` 全量覆盖（`DELETE + INSERT`） |
| **每日一次**（可选） | 仅同步活跃概念的成分股变化（数据源波动较大） |

### 4.3 容错

| 失败场景 | 处理 |
|--------|------|
| AKShare 接口超时（>5s） | 单次重试 2 次，仍失败则跳过该概念，记录到 `failed_concepts` |
| 数据格式变更 | `parser.parse_*` 抛 `ValueError` 时单条跳过，不中断整体 |
| 东方财富限流（429） | 整体退避 60s 后重试 |
| 概念消失（已退市/合并） | 标记 `is_active = FALSE`，不删除（保留历史） |
| 概念对应股票已退市 | `stock_concept_members.symbol` 无 FK 约束（symbol 不引用 stock_infos），但可在同步后用 `LEFT JOIN` 清理孤立记录 |

---

## 五、API 设计概览

| 方法 | 路径 | 用途 | 调用方 |
|------|------|------|--------|
| GET  | `/api/v1/concepts/` | 分页列出所有概念（支持 q/source/is_active 筛选） | 后台概念管理页 |
| GET  | `/api/v1/concepts/{name}` | 单概念详情（含成分股） | 概念详情页 |
| GET  | `/api/v1/concepts/by-symbol/{symbol}` | 单股票所属概念（**简略版**，抽屉预热） | 股票详情页 |
| GET  | `/api/v1/concepts/tab-by-symbol/{symbol}` | 🆕 单股票所属概念（**分组版**，抽屉「概念」Tab 专用） | StockDetailDrawer「概念」Tab |
| POST | `/api/v1/concepts/sync` | 触发全量/增量同步（后台任务） | 后台管理 |
| GET  | `/api/v1/concepts/sync/status` | 查询同步进度 | 同步页 |
| GET  | `/api/v1/stock-panel/?with_concepts=true` | 列表接口，`concepts` 字段（简略版，预热用） | StockInfoList.vue |

### 5.1 响应示例（嵌入到 StockPanel，给详情抽屉复用）

```json
GET /api/v1/stock-panel/?page=1&page_size=20&with_concepts=true

{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "symbol": "002229",
        "name": "鸿博股份",
        "industry": "轻工制造",
        "total_mv": 85.4,
        "pe_ttm": 120.5,
        "pools": [...],
        "concepts": [
          { "concept_id": 1042, "name": "人形机器人", "source": "em" },
          { "concept_id": 1088, "name": "AI算力",     "source": "em" },
          { "concept_id": 1203, "name": "英伟达概念", "source": "em" }
        ]
      }
    ],
    "total": 5569,
    "page": 1,
    "page_size": 20,
    "pages": 279
  }
}
```

> **字段用途变更**（2026-09-24 修订）：
> `concepts` 字段不再用于表格列渲染，改为「详情抽屉」按需消费。
> - 列表请求默认 `with_concepts=false`（减少首屏负载）。
> - 详情抽屉打开时，前端可选择：
>   1. 直接读 `row.concepts`（若该行已带，避免重复请求），或
>   2. 调 `GET /api/v1/concepts/by-symbol/{symbol}` 获取完整版（含 `concept_type`、`description`）。
>
> 推荐方案 1（直接读 `row.concepts`），仅在用户点「查看更多概念」按钮时才调方案 2 拿全量。

---

## 六、变更统计

| 层 | 文件 | 操作 | 改动量 |
|----|------|------|--------|
| **PlantUML** | `docs/PlantUML/Concept/01-class.puml` | 🆕 | ~325 行 |
| **PlantUML** | `docs/PlantUML/Concept/02-data-flow.puml` | 🆕 | ~210 行 |
| **设计文档** | `docs/dev/06gainian/README.md` | 🆕 | ~280 行 |
| **设计文档** | `docs/dev/06gainian/01-domain-design.md` | 🆕 | ~200 行 |
| **设计文档** | `docs/dev/06gainian/02-infrastructure-design.md` | 🆕 | ~280 行 |
| **设计文档** | `docs/dev/06gainian/03-application-and-route-design.md` | 🆕 | ~230 行 |
| Domain | `domain/concept/{entity,value_objects,schemas,repository,exceptions,__init__}.py` | 🆕 | ~200 行 |
| Infra ORM | `infrastructure/database/models/concept.py` | 🆕 | ~80 行 |
| Infra Collector | `infrastructure/collectors/akshare/{fetcher,parser,__init__}.py` | 🆕 | ~150 行 |
| Infra Repo | `infrastructure/repositories/concept_repository.py` | 🆕 | ~200 行 |
| Infra Registry | `infrastructure/collectors/registry.py` | ✏️ +8 行 | 注册 ConceptFetcher |
| Infra Main | `infrastructure/main.py` | ✏️ +3 行 | import 新 ORM + Collector |
| App DTO | `application/dto/concept.py` | 🆕 | ~80 行 |
| App DTO | `application/dto/panel.py` | ✏️ +5 行 | StockPanelItemVO 加 `concepts` 字段 |
| App Service | `application/concept_service.py` | 🆕 | ~150 行 |
| App Service | `application/panel_service.py` | ✏️ +15 行 | 编排概念反查 |
| App Repo | `infrastructure/repositories/panel_compose_repository.py` | ✏️ +15 行 | 委托给 ConceptRepository |
| Route | `route/api/v1/concept.py` | 🆕 | ~120 行 |
| Route | `route/api/v1/panel.py` | ✏️ +1 行 | 新增 `with_concepts` query 参数 |
| Frontend | `frontend/src/views/stock-info/api.ts` | ✏️ +15 行 | ConceptBrief / ConceptGroupedVO / 新增 API 封装 |
| Frontend | `frontend/src/views/stock-info/StockInfoList.vue` | ✏️ +20 行 | 移除展开列 + 强化详情按钮 |
| Frontend | `frontend/src/views/stock-info/components/StockDetailDrawer.vue` | ✏️ +30 行 | 新增「概念」Tab |
| Frontend | `frontend/src/views/stock-info/components/ConceptTab.vue` | 🆕 | 概念 Tab 内容组件（按类型分组） |
| Frontend | `frontend/src/views/stock-info/components/ConceptTag.vue` | 🆕 | 单概念 Tag（可点击） |
| Frontend | `frontend/src/views/stock-info/components/StockExpandRow.vue` | ❌ -110 行 | 删除（被详情按钮取代） |
| Frontend | `frontend/src/views/stock-info/components/IndicatorSwitcher.vue` | 🆕 | 概念 Tab 中复用的子组件 |
| **合计** | — | — | **净增 ~2310 行**（比原方案略减，因为删除了展开行） |

---

## 七、相关文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| **类图：跨层修改概览** | `docs/PlantUML/Concept/01-class.puml` | NEW vs CHANGED vs UNCHANGED |
| **数据流：概念反查** | `docs/PlantUML/Concept/02-data-flow.puml` | 4 层 + 2 表 |
| 领域层详细设计 | `docs/dev/06gainian/01-domain-design.md` | BO / Entity / VO / Protocol |
| 基础设施层详细设计 | `docs/dev/06gainian/02-infrastructure-design.md` | DB / ORM / Repo / AKShare Fetcher |
| 应用层 + 路由详细设计 | `docs/dev/06gainian/03-application-and-route-design.md` | DTO / Service / Route |
| **前端详情抽屉设计** | `docs/dev/06gainian/04-frontend-detail-design.md` | 🆕 抽屉 Tab / 强化按钮 / 组件结构 / API 流程 |
| 类图：面板组合数据流 | `docs/PlantUML/StockInfo/03-panel-compose.puml` | 复用既有 panel 数据流图 |
| 设计演进：Protocol 重构 | `docs/dev/04protocol/03_akshare_extension.md` | 早期 akshare 接入思路（不实现，已被本方案替代） |
| UML 绘制规范 | `docs/config/uml类图设计规范.md` | PlantUML 绘制规范 |

---

## 八、设计取舍说明

### 8.1 为什么不像 03-panel-compose 那样把概念反查内置到 `StockPanelComposeRepository`？

| 选项 | 优 | 劣 |
|------|----|----|
| **A. 内置**（panel 仓储直接 JOIN concept） | 少一次 SQL | ❌ panel 仓储变成 6 表 JOIN，越界更严重 |
| **B. 委托**（panel 仓储调用 ConceptRepository，封装在 panel 内） | ✅ panel 仍是单一职责，调用方无感知 | 多 1 次 SQL（可接受，page_size ≤ 500） |
| **C. 上抛 Service 层**（panel_service 直接调 ConceptRepository） | 仓储层无依赖 | ❌ Service 层编排变复杂，与既有"with_pools 同源反查"模式不一致 |

**选择 B**：与现有 `list_membership_by_symbols`（pool 反查）模式对称，
确保 Service 编排代码风格统一。

### 8.2 为什么不做 Tushare 概念接口适配？

虽然 `concept` 协议可以接多家数据源，但当前 AKShare 已满足需求，
引入 Tushare 适配器会徒增代码复杂度（双数据源需做合并/去重策略）。
**原则：能不新建的就不新建，需要时再补**。

### 8.3 为什么概念清单用 `is_active` 而不硬删除？

概念可能因监管 / 业务原因临时下线（如"雄安新区"），但历史归因分析仍需查这些概念。
软删除 + `last_synced_at` 标记状态即可，避免历史数据丢失。
