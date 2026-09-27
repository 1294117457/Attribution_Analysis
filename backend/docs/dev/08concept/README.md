# 概念板块二期接入 — 列表主概念 + 详情实时理由

> 编写日期：2026-09-26
> 所属阶段：`08concept`（`06gainian` 之后的演进排期）
> 前置依赖：`06gainian`（概念聚合根 / BO / VO / Repository / 路由 / 前端 Tab 全部已落地）
>
> 配套文档（本目录）：
> - [README.md](./README.md) — 总览（本文件）
> - [01-naming-and-tables.md](./01-naming-and-tables.md) — 命名规范 + 表 ER 图（Mermaid）
> - [02-class-design.md](./02-class-design.md) — 涉及修改的类（新增 `ConceptMainVO` / DTO / Service / 仓储方法）
> - [03-data-flow.md](./03-data-flow.md) — 数据流时序图 + 缓存策略
> - [04-frontend-stockinfo.md](./04-frontend-stockinfo.md) — 前端 StockInfoList 行内主概念 + 详情抽屉实时刷新
>
> 前置阅读（建议）：
> - [`../06gainian/README.md`](../06gainian/README.md) — 概念一期总览
> - [`../06gainian/01-domain-design.md`](../06gainian/01-domain-design.md) — `Concept` / `ConceptBriefVO` / `ConceptGroupedVO` / `ConceptLiveVO` 定义
> - [`../06gainian/03-application-and-route-design.md`](../06gainian/03-application-and-route-design.md) — 既有路由 / Service / DTO
> - [`../03dataana/01data.md`](../03dataana/01data.md) — 全局表命名规范（前缀约定）

---

## 一、背景与目标

### 1.1 现状（基于 `06gainian` 的产出）

后端已经实现：

| 能力 | 端点 | 数据来源 | 入库？ |
|:---|:---|:---|:---:|
| 概念清单分页 | `GET /api/v1/concepts/` | DB | ✅ |
| 单概念详情 | `GET /api/v1/concepts/{name}` | DB + 实时拉成分股 | ✅ |
| 单股票所属概念（简略版，预热用） | `GET /api/v1/concepts/by-symbol/{symbol}` | DB | ✅ |
| 单股票所属概念（分组版，抽屉 Tab 用） | `GET /api/v1/concepts/tab-by-symbol/{symbol}` | DB | ✅ |
| 实时反查 + 入选理由（adata 独家） | `GET /api/v1/concepts/live-by-symbol/{symbol}` | adata 实时 | ❌ |
| 列表内嵌简略概念 | `GET /api/v1/stock-panel/?with_concepts=true` | DB | ✅ |

前端已经实现：

| 视图位置 | 显示 | 数据来源 |
|:---|:---|:---|
| `StockInfoList.vue` 行内（`with_concepts=true` 下发） | 携带 `row.concepts: ConceptBrief[]`，**当前未渲染** | DB |
| `StockDetailDrawer.vue`「概念」Tab | 按 `concept_type` 分组渲染 + Tooltip 显示 description | `/tab-by-symbol/{symbol}` |

### 1.2 缺口

1. **列表行"主要概念"未渲染**：
   `StockInfo.concepts` 已经随列表下发，但前端没有 UI 渲染它——用户**看不到**这只股票主要属于哪些概念。
   - 这是用户最近的提问：*"在列表中实现主要概念和详情中相关概念的功能"*
2. **详情抽屉没有"实时反查 + 入选理由"按钮**：
   `/live-by-symbol/{symbol}` 端点已存在，但前端 `ConceptTab.vue` 没有调用入口，用户**看不到** adata 提供的"为什么该股票属于该概念"的解释。
3. **列表预热的 `ConceptBrief` 没有类型字段**：
   列表行只能展示 3 字段（`concept_id / name / source`），无法区分行业 / 主题 / 事件。

### 1.3 目标（本期）

| # | 目标 | 优先级 | 复杂度 |
|:--:|:---|:---:|:---:|
| G1 | 列表行渲染"主概念 Tag 列"（最多 3 个 + `+N` 溢出），按优先级排序（industry > theme > event > other） | P0 | 低 |
| G2 | 详情抽屉「概念」Tab 加 🔄"实时刷新"按钮，调 `/live-by-symbol/{symbol}` 覆盖 DB 数据并展示入选理由 | P0 | 中 |
| G3 | 列表下发的 `ConceptBrief` 增 `concept_type` 字段（不影响现有 3 字段接口，前端可选用） | P1 | 低 |
| G4 | `ConceptTag.vue` 组件支持两种入参：`ConceptBrief`（列表用）+ `ConceptGroupedVO`（抽屉用），避免重复实现 | P1 | 低 |
| G5 | `StockPanelItemVO.concepts` 增 `ConceptMainVO`（取主概念视图，业务排序+去重），保留 `ConceptBrief[]` 字段以向后兼容 | P2 | 中 |

### 1.4 非目标（本期不做）

- 概念详情页 / 选股器（v1.1）
- 概念热力图（v1.3）
- 概念联动归因（结合 K 线异动 + reason 时间窗口；v2.0）
- 工具栏高级筛选区加"概念多选"（v1.1）

---

## 二、与 `06gainian` 的关系

`06gainian` 解决了"**有没有**"——概念数据从采集 → 入库 → 前端渲染的完整链路；
`08concept` 解决"**好不好用**"——在已有数据基础上，让用户**一眼看到**列表股票的主概念、**理解**每条概念的入选理由。

```
06gainian（已完成）                08concept（本期）
─────────────────────             ─────────────────────
✓ 概念聚合根 + 2 张表              ▲ 行内主概念 Tag 列（用已有 row.concepts）
✓ BO/VO/Repository/Protocol       ▲ ConceptMainVO：主概念视图（业务排序）
✓ 路由 7 个                        ▲ 抽屉「🔄 实时刷新」按钮（用已有 /live-by-symbol）
✓ AkShare/THS/Adata fetcher        ▲ ConceptTag 适配两种入参
✓ ConceptTab.vue 按类型分组           ▲ concept_type 透出到 ConceptBrief
✓ ConceptTag.vue 单 Tag 组件
```

**所有后端能力已在 `06gainian` 完成**，`08concept` 主要工作是**前端 UI 整合 + 新增 1 个轻量后端 VO（ConceptMainVO）+ 后端排序逻辑**。

---

## 三、核心决策 ⭐

### 3.1 列表行"主概念"的判定规则

| 策略 | 描述 | 采纳？ |
|:---|:---|:---:|
| **A. 全部展示 + `+N` 溢出** | 简单粗暴，但 14+ 列的表格再加 8+ 个 Tag 视觉拥挤 | ❌ |
| **B. 限定 3 个 + `+N` 溢出，按 `concept_type` 优先级排序** | 一眼能看到核心标签，详情 Tab 看完整列表 | ✅ P0 |
| **C. 工具栏加"概念多选" + 仅展示命中概念** | 功能强大，但工作量大、本期 P1 推后 | ❌ 本期不做 |

**优先级排序**：industry → theme → style → region → event → other；
**同优先级内**：按 `name` 字典序。

### 3.2 详情抽屉"实时反查"展示策略

| 策略 | 描述 | 采纳？ |
|:---|:---|:---:|
| **A. 覆盖原数据** | 用户点 🔄 后，原 DB 数据被实时数据替换 | ❌ 破坏 SSR 体验 |
| **B. 并列展示：DB + 实时（合并去重）** | 两路数据合成一份，重复概念优先展示实时数据 | ✅ P0 |
| **C. 切换标签页（DB / 实时）** | 互不干扰 | ❌ 概念一般不会同时存在两路，复杂度不划算 |

**合并去重规则**：

1. 取两路并集（按 `(name, source)` 联合去重）；
2. **DB 概念** 标记为 `is_realtime=false`；
3. **实时独有** 概念标记为 `is_realtime=true`，并显示 `reason`；
4. **DB 与实时共有** 概念：保留 DB 概念，但把 `reason` 字段（实时独有）合并进来。

### 3.3 概念数据排序 + 染色

继承 `06gainian` 的 `CONCEPT_TYPE_ORDER` 与 `ConceptTag.vue` 的 `tagType` 映射，**不重复实现**。

---

## 四、文件清单（本设计涉及，但本期不实现）

### 4.1 后端（基于 `06gainian` 增量）

| 文件 | 操作 | 说明 |
|:---|:---:|:---|
| `backend/src/domain/concept/value_objects.py` | ✏️ 改 | 新增 `ConceptMainVO`（主概念视图，带 `display_order`） |
| `backend/src/application/dto/concept.py` | ✏️ 改 | `StockPanelItemVO.concepts` 类型由 `ConceptBriefVO` 升级为 `ConceptMainVO` |
| `backend/src/application/panel_service.py` | ✏️ 改 | `query_panels()` 增加"主概念筛选+排序"逻辑 |
| `backend/src/application/concept_service.py` | ✏️ 改 | 新增 `merge_db_and_live(db_vos, live_vos)` 工具方法 |
| `backend/src/route/api/v1/concept.py` | ✏️ 改 | `/tab-by-symbol` 新增 query 参数 `merge_live=true`（默认 false） |

### 4.2 前端（基于 `06gainian` 增量）

| 文件 | 操作 | 说明 |
|:---|:---:|:---|
| `frontend/src/views/stock-info/api.ts` | ✏️ 改 | `ConceptBrief` 增 `concept_type?`；新增 `ConceptMainVO` TS 类型；新增 `getLiveConceptsBySymbol()` |
| `frontend/src/views/stock-info/components/ConceptTag.vue` | ✏️ 改 | 接受 `ConceptBrief` 或 `ConceptGroupedVO`，统一渲染逻辑 |
| `frontend/src/views/stock-info/components/ConceptTab.vue` | ✏️ 改 | 加 🔄"实时刷新"按钮；展示合并后的数据 + 入选理由 |
| `frontend/src/views/stock-info/StockInfoList.vue` | ✏️ 改 | 新增"主概念"列（最多 3 个 Tag + `+N`），接 `ConceptTag` |
| `frontend/src/views/stock-info/components/StockDetailDrawer.vue` | ✏️ 改 | 「概念」Tab 透传 `conceptClick` 到 ConceptTab → 处理"跳概念详情" |

### 4.3 新增文档（本目录）

```
backend/docs/dev/08concept/
├── README.md                       ← 本文件（总览）
├── 01-naming-and-tables.md         ← 表命名 + Mermaid ER 图
├── 02-class-design.md              ← 类图（领域 / 仓储 / 应用 / 路由 / 前端）
├── 03-data-flow.md                 ← 数据流时序图（Mermaid sequenceDiagram）
└── 04-frontend-stockinfo.md        ← 前端 StockInfoList + StockDetailDrawer 改造方案
```

---

## 五、变更统计

| 层 | 文件 | 操作 | 改动量（估算） |
|:---|:---|:---:|:---|
| Domain | `domain/concept/value_objects.py` | ✏️ +1 类（ConceptMainVO） | ~15 行 |
| App DTO | `application/dto/panel.py` | ✏️ `concepts` 字段类型升级 | ~5 行 |
| App DTO | `application/dto/concept.py` | ✏️ 增 `merged` 字段 | ~5 行 |
| App Service | `application/panel_service.py` | ✏️ 主概念筛选逻辑 | ~30 行 |
| App Service | `application/concept_service.py` | ✏️ `merge_db_and_live` + `get_tab_content_with_live` | ~50 行 |
| Route | `route/api/v1/concept.py` | ✏️ `merge_live=true` query 参数 | ~10 行 |
| Frontend | `frontend/.../api.ts` | ✏️ 类型扩展 + 新 API 封装 | ~20 行 |
| Frontend | `frontend/.../ConceptTag.vue` | ✏️ 双类型入参 | ~10 行 |
| Frontend | `frontend/.../ConceptTab.vue` | ✏️ 实时刷新按钮 + 合并渲染 | ~50 行 |
| Frontend | `frontend/.../StockInfoList.vue` | ✏️ 主概念列 | ~40 行 |
| Frontend | `frontend/.../StockDetailDrawer.vue` | ✏️ 透传 conceptClick | ~5 行 |
| 文档 | `backend/docs/dev/08concept/*.md` | 🆕 | ~1500 行 |
| **合计** | — | — | **~1740 行** |

---

## 六、相关文档索引

| 文档 | 路径 | 说明 |
|:---|:---|:---|
| 概念一期总览 | `docs/dev/06gainian/README.md` | 上游基础 |
| 概念领域层 | `docs/dev/06gainian/01-domain-design.md` | BO / VO / Protocol |
| 概念基础设施层 | `docs/dev/06gainian/02-infrastructure-design.md` | ORM / Repo / Collector |
| 概念应用层 + 路由 | `docs/dev/06gainian/03-application-and-route-design.md` | Service / Route |
| 概念前端设计 | `docs/dev/06gainian/04-frontend-detail-design.md` | Tab / 强化按钮 |
| 全局命名规范 | `docs/dev/03dataana/01data.md` §0.1 | 表前缀约定 |
| PlantUML 类图 | `docs/PlantUML/Concept/01-class.puml` | 跨层类图 |
| PlantUML 数据流 | `docs/PlantUML/Concept/02-data-flow.puml` | 反查数据流 |

---

## 七、设计取舍

### 7.1 为什么复用 `row.concepts` 而不是新增端点？

| 选项 | 优 | 劣 |
|:---|:---|:---|
| **A. 复用 `row.concepts`** ⭐ | 零网络、零 N+1、与 `with_pools` 模式一致 | 字段少（无 description） |
| **B. 新增 `GET /api/v1/stock-panel/main-concepts`** | 可定制返回字段 | 多一次请求 + 重复实现"反查"逻辑 |
| **C. 前端懒加载（点行再调 `/by-symbol/{symbol}`）** | 首屏最快 | 与"详情抽屉"功能重复 |

`row.concepts` 已经随列表下发，**复用成本最低**；description 在抽屉 Tab 里再拉。

### 7.2 为什么需要 `ConceptMainVO` 而不是直接用 `ConceptBriefVO`？

| 维度 | `ConceptBriefVO` | `ConceptMainVO` |
|:---|:---|:---|
| 字段 | `concept_id / name / source` | `concept_id / name / source / concept_type / display_order` |
| 业务 | 通用简略视图 | 主概念业务视图（带排序） |
| 出现处 | 列表预热 | 列表行渲染 |
| 数量 | 全部命中 | 仅 3 个 + `+N` |

`display_order` 是关键字段——前端拿到后可以直接 `v-for` 渲染，无需再做客户端排序。

### 7.3 为什么详情 Tab 用"合并"而不是"切换"？

用户期望的是"看完 DB 数据，还能点一下看实时理由"——**叠加态**最自然。
切换会让用户失去 DB 列表的稳定性（毕竟 DB 同步过，更权威）。

---

## 八、测试要点

| 测试 | 类型 | 覆盖 |
|:---|:---|:---|
| `test_concept_main_vo.py` | 单元 | `display_order` 计算逻辑；按 `concept_type` 排序正确性 |
| `test_concept_service_merge.py` | 单元 | `merge_db_and_live` 合并规则：DB-only / live-only / 共有 |
| `test_panel_service_main_concepts.py` | 单元 | 列表行主概念筛选：3 个 + `+N`；排序优先级 |
| `test_route_tab_merge_live.py` | 集成 | `?merge_live=true` 端到端调用 |
| `ConceptTag.spec.ts` | 单元 | 双类型入参：ConceptBrief（无 description）vs ConceptGroupedVO（有 description）|
| `ConceptTab.spec.ts` | 单元 | 实时刷新按钮触发；合并数据展示；reason tooltip |
| `StockInfoList.spec.ts` | 集成 | 行内主概念列渲染；hover tooltip；点击不冒泡 |
