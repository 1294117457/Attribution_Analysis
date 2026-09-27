# 09 — 概念板块三期（THS 链路 + adata 反查 + 概念行情）

> 编写日期：2026-09-27
> 所属阶段：`09concept`（继承 `06gainian` 一期 + `08concept` 二期）
> 触发问题：列表主要概念为空 + 同花顺显示概念涨跌、我们没有

> 配套文档（本目录）：
> - [README.md](./README.md) — 总览（本文件）
> - [01-data-source-decision.md](./01-data-source-decision.md) — **数据源选型 ⭐**（重点）
> - [02-class-design.md](./02-class-design.md) — 类图
> - [03-data-flow.md](./03-data-flow.md) — 数据流时序图
> - [04-frontend-stockinfo.md](./04-frontend-stockinfo.md) — 前端 StockInfoList + 详情抽屉改造
> - [05-collect-manage.md](./05-collect-manage.md) — CollectManage.vue 概念子任务改造

> 前置阅读（建议）：
> - [`../08concept/README.md`](../08concept/README.md) — 二期总览（主概念列 + 实时刷新）
> - [`../06gainian/README.md`](../06gainian/README.md) — 一期总览（基础 CRUD）
> - [`../04protocol/03_akshare_extension.md`](../04protocol/03_akshare_extension.md) — akshare 接口能力清单

---

## 一、背景

### 1.1 用户原始诉求

> *"列表主要概念都是空的"*
> *"同花顺会显示概念的涨跌，这里没有"*
> *"是不是 adata 可以不需要，只保留 akshare 和 ths 的数据"*

### 1.2 现状（基于 `08concept` 已完成产出）

| 已实现 | 数据来源 | 痛点 |
|:---|:---|:---|
| 概念清单列表（`GET /concepts/`） | DB（THS 源） | ✅ 有 375 个 |
| 详情抽屉「概念」Tab（`/tab-by-symbol/{symbol}`） | **DB** `stock_concept_members` | ❌ **表里没数据**，Tab 永远空 |
| 行内主概念列（08concept 已加渲染） | `row.concepts` | ❌ 同样依赖空表 |
| 实时反查 + 入选理由（08concept 已加 🔄 按钮） | adata 实时 | ✅ 工作正常 |
| 概念行情 | — | ❌ **完全没做** |

### 1.3 网络现状（2026-09-27 实测）

| 域名 | 状态 | 说明 |
|:---|:---:|:---|
| `push2.eastmoney.com` | ❌ RST | akshare 所有 `*_em` 概念端点全挂 |
| `q.10jqka.com.cn` | ✅ | akshare 所有 `*_ths` 概念端点可用 |
| `datacenter.eastmoney.com` | ✅ | adata 反查端点可用（**独家**） |

---

## 二、本期目标

| # | 目标 | 优先级 | 数据源 |
|:--:|:---|:---:|:---|
| G1 | 列表主概念列填充（`stock_concept_members` 入库） | **P0** | adata 反查 |
| G2 | 详情抽屉「概念」Tab 显示该股票所有相关概念 | **P0** | DB（依赖 G1） |
| G3 | 概念行情快照（板块涨幅/排名/资金净流入）入库 | **P0** | THS `concept_info_ths` |
| G4 | StockInfoList 主概念 Tag 显示涨跌 | **P0** | DB（依赖 G3） |
| G5 | CollectManage.vue 概念 Tab 拆为 3 个子任务 | **P0** | 后端 3 类任务 |
| G6 | 概念指数日 K 增量入库 | P1 | THS `concept_index_ths` |
| G7 | 概念联动归因（结合 reason + K 线异动） | ❌ v2.0 | — |

---

## 三、核心决策 ⭐

### 3.1 数据源分工

| 能力 | 数据源 | 决策 |
|:---|:---|:---|
| 概念清单（375 个） | THS `concept_name_ths` | **仅 THS**（EM RST） |
| 概念-成分股 M:N | adata `get_concept_east(stock_code)` | **仅 adata 反查**（akshare 全链路无此端点） |
| 概念实时行情 | THS `concept_info_ths` | **仅 THS**（EM RST） |
| 概念日 K | THS `concept_index_ths` | **仅 THS**（EM RST） |
| EM `concept_cons_em` / `concept_spot_em` | — | ❌ **不参与**（RST） |

### 3.2 adata 是否可以完全去掉？

**❌ 不能完全去掉**。

**关键证据**：

```
akshare THS 概念端点（共 4 个）：
  stock_board_concept_index_ths     ← 指数行情
  stock_board_concept_info_ths      ← 单概念实时
  stock_board_concept_name_ths      ← 清单
  stock_board_concept_summary_ths   ← 摘要
                                 ↑
                  全是「概念维度」，无「股票维度」

akshare 全命名空间搜「concept ... cons」：空集
→ akshare 没有任何「按概念查成分股」或「按股票反查概念」端点
```

**M:N 关系只能从股票维度构建**，因此 adata 的 `get_concept_east` 是唯一可行路径。

**但 adata 可以做减法**：

- ❌ `all_concept_code_east`：RST
- ❌ `concept_constituent_east`：RST
- ✅ **`get_concept_east(stock_code)`：保留，仅用于采集阶段**

详情抽屉的"实时反查"按钮（08concept）继续用 adata，**业务路径不变**。

### 3.3 M:N 入库策略

| 策略 | 描述 | 采纳？ |
|:---|:---|:---:|
| A. 枚举概念→拉成分股（EM RST 走不通） | akshare cons_em | ❌ |
| **B. 枚举股票→adata 反查（唯一可行）** | adata 反查每只股票 | ✅ P0 |
| C. 用户手动导入 CSV | 用户上传 | P2（兜底） |

### 3.4 行情采集频率

| 任务 | 频率 | 触发 |
|:---|:---|:---|
| 概念清单 | 每日 1 次 | 手动 + cron 9:00 |
| **成分股反查** | 每日 1 次（全量） + 增量（新增股票） | 手动 + cron 9:30 |
| **概念行情快照** | 交易日 09:30-15:00 每 5 分钟 | 调度器（TradingHoursGuard） |

---

## 四、范围与非目标

### 4.1 范围

**后端**：
- 仓储：3 个新方法（upsert_single_member / upsert_snapshot / upsert_index_ths）
- 采集器：akshare `concept_info_ths` / `concept_index_ths` 2 个新方法
- 同步任务：3 个新 BaseCollectTask（清单已有 / 成分股 / 行情快照）
- 路由：3 个新端点（`/snapshot/{name}` / `/index-ths/{name}` / `/membership-sync` 触发）
- ORM：2 张新表（`concept_snapshots` / `concept_index_ths`）

**前端**：
- StockInfoList：主概念 Tag 显示涨跌色块（红涨绿跌同花顺配色）
- StockDetailDrawer：「概念」Tab 加"涨跌"列
- CollectManage.vue：概念 Tab 拆为子任务 UI（清单/成分股/行情三按钮）

### 4.2 非目标（本期不做）

- ❌ 概念详情页 / 选股器
- ❌ 概念热力图
- ❌ EM 网络恢复后的多源合并（待 EM 通了再说）
- ❌ 实时推送（WebSocket）
- ❌ 跨概念成分股交叉分析

---

## 五、文件清单

### 5.1 后端（增量）

| 文件 | 操作 | 说明 |
|:---|:---:|:---|
| `src/domain/concept/entity.py` | ✏️ | + `ConceptSnapshot` / `ConceptIndexTH` 实体 |
| `src/domain/concept/value_objects.py` | ✏️ | + `ConceptSnapshotVO` / `ConceptIndexTHVO` |
| `src/domain/concept/repository.py` | ✏️ | + 4 个仓储协议方法 |
| `src/infrastructure/database/models/concept.py` | ✏️ | + `ConceptSnapshotDB` / `ConceptIndexTHDB` |
| `src/infrastructure/repositories/concept_repository.py` | ✏️ | + 4 个实现方法 |
| `src/infrastructure/collectors/akshare/fetcher.py` | ✏️ | + `fetch_concept_info_ths()` / `fetch_concept_index_ths()` |
| `src/infrastructure/collectors/adata/fetcher.py` | 🔧 | 保留 `get_concept_east`，其余 deprecated |
| `src/infrastructure/collectors/protocols.py` | ✏️ | + `ConceptQuoteFetcher` / `ConceptIndexTHFetcher` 协议 |
| `src/infrastructure/collectors/registry.py` | ✏️ | 注册新协议 |
| `src/application/concept_service.py` | ✏️ | + `sync_membership` / `sync_snapshot` / `sync_index_th` |
| `src/infrastructure/tasks/collect/membership.py` | 🆕 | MembershipSyncTask |
| `src/infrastructure/tasks/collect/snapshot.py` | 🆕 | SnapshotSyncTask |
| `src/infrastructure/tasks/collect/index_th.py` | 🆕 | IndexTHSyncTask |
| `src/route/api/v1/concept.py` | ✏️ | + 3 个端点 |
| `src/infrastructure/database/migrate/concept_*.py` | 🆕 | 2 张新表迁移脚本 |

### 5.2 前端（增量）

| 文件 | 操作 | 说明 |
|:---|:---:|:---|
| `src/views/stock-info/api.ts` | ✏️ | + `getConceptSnapshot()` / 类型 |
| `src/views/stock-info/components/ConceptTag.vue` | ✏️ | 涨跌染色（红涨绿跌） |
| `src/views/stock-info/components/ConceptTab.vue` | ✏️ | 「概念」Tab 加"涨跌"列 |
| `src/views/stock-info/StockInfoList.vue` | ✏️ | 主概念 Tag 后缀显示 pct_change |
| `src/views/collect-manage/api.ts` | ✏️ | + `Membership` / `Snapshot` / `IndexTH` 任务创建 API |
| `src/views/collect-manage/CollectManage.vue` | ✏️ | 概念 Tab 拆为子任务 UI |

---

## 六、实施顺序（建议 5 步走）

```
Step 1: 后端基础设施（无 UI）
   ├─ ORM 2 张新表
   ├─ 仓储 4 个方法
   └─ akshare collector 加 2 个方法
   ⏱ 估时：半天

Step 2: Membership 同步任务
   ├─ AdataFetcher.get_concept_east（已有）
   ├─ MembershipSyncTask（迭代 stock_infos，adata 反查累加）
   └─ 测试：一只股票 → 多个 concept → 写入 stock_concept_members
   ⏱ 估时：1 天

Step 3: Snapshot 同步任务
   ├─ AkShareFetcher.fetch_concept_info_ths
   ├─ SnapshotSyncTask（迭代 concepts，THS info 入库）
   └─ 测试：375 个概念 × 5s = 30 分钟一次
   ⏱ 估时：1 天

Step 4: 前端 UI 改造
   ├─ StockInfoList 主概念 Tag 显示涨跌
   ├─ ConceptTab 加"涨跌"列
   └─ CollectManage.vue 概念 Tab 拆为子任务
   ⏱ 估时：1-2 天

Step 5: Index TH 日 K（可选 P1）
   ⏱ 估时：1 天
```

---

## 七、变更统计

| 层 | 文件 | 操作 | 改动量（估算） |
|:---|:---|:---:|:---|
| Domain | 2 文件 | ✏️ +2 实体 +2 VO | ~80 行 |
| ORM | 1 文件 | ✏️ +2 表 | ~100 行 |
| Repository | 2 文件 | ✏️ +5 方法 | ~80 行 |
| Collector | 2 文件 | ✏️ +2 方法、🔧 减 adata | ~120 行 |
| Sync Task | 3 文件 🆕 | 🆕 | ~250 行 |
| Service | 1 文件 | ✏️ +3 方法 | ~100 行 |
| Route | 1 文件 | ✏️ +3 端点 | ~30 行 |
| Frontend | 4 文件 | ✏️ | ~150 行 |
| 文档 | 5 文件 🆕 | 🆕 | ~1500 行 |
| **合计** | — | — | **~2410 行** |

---

## 八、相关文档索引

| 文档 | 路径 | 说明 |
|:---|:---|:---|
| 数据源选型 | `./01-data-source-decision.md` | ⭐ 本期最重要决策 |
| 类图 | `./02-class-design.md` | 跨层类图 |
| 数据流 | `./03-data-flow.md` | 时序图 |
| 前端 StockInfo | `./04-frontend-stockinfo.md` | 列表 + 抽屉 |
| 前端 CollectManage | `./05-collect-manage.md` | 采集管理 Tab |
| 二期总览 | `../08concept/README.md` | 主概念列 + 实时刷新 |
| 一期总览 | `../06gainian/README.md` | 基础 CRUD |
| akshare 协议扩展 | `../04protocol/03_akshare_extension.md` | 接口能力 |
| 全局命名规范 | `../03dataana/01data.md` §0.1 | 表前缀约定 |

---

## 九、设计取舍

### 9.1 为什么 M:N 入库用 adata 反查，而不是等待 EM 恢复？

| 选项 | 优 | 劣 |
|:---|:---|:---|
| **A. adata 反查** ⭐ | 当前网络可跑通，**最快填补空表** | 慢（5000×0.5s = 42 分钟） |
| B. 等 EM 恢复重跑 cons_em | akshare EM 数据最权威 | 不知道什么时候恢复 |
| C. 用户导入 CSV | 立刻可用 | 体验差 |

**采用 A**，并加入"增量模式"作为兜底。

### 9.2 为什么 adata 还要保留？

**M:N 关系的唯一路径**。任何想从"股票"维度出发构建概念归属的方案都绕不开 adata。

### 9.3 为什么行情采集单独一张 `concept_snapshots` 表，而不是复用 `mkt_sector_dailys`？

| 选项 | 优 | 劣 |
|:---|:---|:---|
| **A. 新表 `concept_snapshots`** ⭐ | schema 干净（10 字段）；高频写入独立 | 多一张表 |
| B. 复用 `mkt_sector_dailys` | 少一张表 | 表 schema 为 SW 行业设计（trade_date 主键）+ concept 字段与现有 industry 共存混乱 |

**采用 A**——保持表与业务语义 1:1。

### 9.4 为什么主概念 Tag 显示涨跌用 red-up green-down（同花顺配色）？

**符合用户既有习惯**（同花顺/东方财富都红涨绿跌，与 A 股普遍配色相反是国际惯例）。

---

## 十、测试要点

| 测试 | 类型 | 覆盖 |
|:---|:---|:---|
| `_test_ths.py`（临时脚本） | 实测 | THS 4 个接口字段确认 |
| `test_membership_sync.py` | 单元 | 单只股票反查 → 多个概念 → 累加入库 |
| `test_snapshot_sync.py` | 单元 | THS info 字段解析（"板块涨幅"字符串 → float） |
| `test_index_th_sync.py` | 单元 | 日 K DataFrame → ORM 行 |
| `test_route_concept_snapshot.py` | 集成 | `GET /concepts/{name}/snapshot` |
| `test_route_concept_membership_sync.py` | 集成 | `POST /concepts/sync/membership` 触发 |
| `ConceptTag.spec.ts` | 单元 | 涨跌染色（红/绿/默认） |
| `ConceptTab.spec.ts` | 单元 | 「概念」Tab 加列渲染 |
| `CollectManage.spec.ts` | 集成 | 三子任务 UI 表现 |
| 端到端 | 手工 | 列表主概念列显示 → 点入详情 → 看到全部概念 + 涨跌 |

---

## 十一、风险与回退

| 风险 | 影响 | 回退方案 |
|:---|:---|:---|
| adata 反查被 RST | M:N 入库停滞 | 切换到 akshare `industry_summary_ths` 兜底（仅行业，不全） |
| THS 接口限频（q.10jqka） | 行情采集 429 | 加 retry + 0.5s 间隔 |
| 全量 42 分钟过长 | 用户等待焦虑 | 加"后台跑 + WebSocket 进度" |
| 涨跌字符串解析失败 | snapshot 入库失败 | try/except 单条，skip + 累计 fail 数 |

---

## 十二、本期不动

- ❌ `concepts` / `stock_concept_members` 表 DDL
- ❌ 既有 `ConceptAppService` 方法签名
- ❌ 既有路由（仅新增，不修改）
- ❌ EM 链路（等网络恢复再讨论）
