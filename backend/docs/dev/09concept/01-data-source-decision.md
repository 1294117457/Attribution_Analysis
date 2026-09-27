# 概念板块三期 — 数据源治理：去掉 adata、引入 THS 行情

> 编写日期：2026-09-27
> 所属阶段：`09concept`（`06gainian` 概念一期 → `08concept` 二期 → `09concept` 三期）
> 前置依赖：`06gainian`（基础 CRUD）、`08concept`（列表主概念 + 实时刷新）

> 配套文档（本目录）：
> - [README.md](./README.md) — 总览
> - [01-data-source-decision.md](./01-data-source-decision.md) — **数据源选型（本文）** THS vs adata 决策
> - [02-class-design.md](./02-class-design.md) — 类图（领域 / 仓储 / 应用 / 路由 / 前端）
> - [03-data-flow.md](./03-data-flow.md) — 数据流时序图
> - [04-frontend-stockinfo.md](./04-frontend-stockinfo.md) — StockInfoList + 详情抽屉改造
> - [05-collect-manage.md](./05-collect-manage.md) — CollectManage.vue 概念相关采集功能

> 前置阅读（建议）：
> - [`../08concept/README.md`](../08concept/README.md) — 二期总览（含主概念列、实时刷新）
> - [`../06gainian/README.md`](../06gainian/README.md) — 一期（基础链路）
> - [`../04protocol/03_akshare_extension.md`](../04protocol/03_akshare_extension.md) — akshare 协议扩展（实际接口能力清单）

---

## 一、本期目标

**两个用户痛点 + 一个架构诉求**：

1. **列表主概念一直空** — `stock_concept_members` 表无数据。
   - 根因：06gainian 的 `fetch_concept_stocks` 走 `ak.stock_board_concept_cons_em`，在 EM 被 RST 的网络环境下直接返回空。
2. **同花顺显示概念涨跌，我们没有** — akshare `*_em` 端点（RST）本来能拿到 `stock_board_concept_spot_em`（板块涨幅），但现在挂了。
3. **架构诉求** — 评估能否去掉 adata，只用 akshare。

---

## 二、网络现状实测结论（2026-09-27）

### 2.1 akshare 1.16.91 实际能力

| 接口 | 域名 | 状态 | 字段 |
|:---|:---|:---:|:---|
| `ak.stock_board_concept_name_em` | push2.eastmoney.com | ❌ RST | — |
| `ak.stock_board_concept_name_ths` | q.10jqka.com.cn | ✅ | `name, code`（**375 个概念**） |
| `ak.stock_board_concept_spot_em` | push2.eastmoney.com | ❌ RST | — |
| `ak.stock_board_concept_hist_em` | push2.eastmoney.com | ❌ RST | — |
| `ak.stock_board_concept_index_ths` | q.10jqka.com.cn | ✅ | 概念指数日 K（日期/开/高/低/收/成交量/成交额），**244 个交易日** |
| `ak.stock_board_concept_info_ths` | q.10jqka.com.cn | ✅ | **实时行情**：今开/昨收/最低/最高/**板块涨幅**/**涨幅排名**/**涨跌家数**/资金净流入 |
| `ak.stock_board_concept_cons_em` | push2.eastmoney.com | ❌ RST | — |
| `ak.stock_board_concept_cons_ths` | — | ❌ **接口不存在** | akshare 1.16.91 命名空间中无此函数 |
| `ak.stock_board_concept_summary_ths` | q.10jqka.com.cn | ✅ | 日期/概念名称/驱动事件/龙头股/成分股数量（最近 50 条） |

### 2.2 adata 2.9.x 实际能力

| 接口 | 域名 | 状态 |
|:---|:---|:---:|
| `adata.stock.info.all_concept_code_east` | push2.eastmoney | ❌ RST |
| `adata.stock.info.concept_constituent_east` | push2.eastmoney | ❌ RST |
| `adata.stock.info.get_concept_east(stock_code)` | datacenter.eastmoney | ✅ **独家可用** |

### 2.3 结论矩阵

| 能力 | 唯一可用路径 |
|:---|:---|
| 概念清单 | ✅ THS（`concept_name_ths`） |
| 概念→成分股 | ❌ **akshare 无此端点**（EM RST，THS 命名空间无该接口） |
| 股票→所属概念（反查） | ✅ adata（`get_concept_east`） |
| 概念日 K | ✅ THS（`concept_index_ths`） |
| 概念实时行情（板块涨幅/排名/资金净流入） | ✅ THS（`concept_info_ths`） |

---

## 三、用户两个问题的回答

### Q1：是不是 adata 可以不需要，只保留 akshare 和 ths 的数据？

**答：❌ 不能完全去掉 adata。但理由已经升级——adata 也有 THS 同源端点。**

**akshare 没有 THS cons 端点（实测）**：

```
>>> [m for m in dir(ak) if m.endswith('_ths') and 'concept' in m]
['stock_board_concept_index_ths',   ← 指数行情
 'stock_board_concept_info_ths',    ← 单概念实时
 'stock_board_concept_name_ths',    ← 清单
 'stock_board_concept_summary_ths'] ← 摘要
```

akshare 提供的 THS 链路**全是"按概念"维度**——没有"按股票查所属概念"维度。

而 `stock_concept_members` 表的填充**必须从"股票"维度出发**（一只只股票枚举，写它属于哪些概念）。

### Q1.1：adata 有 THS 同源反查端点！（关键发现）

**adata 官方文档里的 THS 端点**：

| 端点 | 说明 |
|:---|:---|
| `stock.info.all_concept_code_ths()` | 所有 A 股概念代码信息（同花顺） |
| `stock.info.concept_constituent_ths()` | 获取同花顺概念指数的成分股 |
| **`stock.info.get_concept_ths(stock_code)`** | **获取单只股票所属的概念板块（F10 同花顺源）** |

**实测**（2026-09-27）：

```python
>>> df = adata.stock.info.get_concept_ths(stock_code='600519')
>>> df.columns.tolist()
['stock_code', 'concept_code', 'name', 'source', 'reason']
>>> df['source'].unique()
['同花顺']                       ← 不是 EM！是 THS 源！
>>> df[['concept_code', 'name']]
   885761      超级品牌
   885525      白酒概念
   885916      同花顺漂亮100
   886021      国企改革
   886086      西部大开发
   885705      乡村振兴
```

**关键洞察**：

1. **adata 的 `get_concept_ths` 走的是 THS 源**（`source='同花顺'`），不是 EM
2. **`concept_code` 是 `885xxx` 系列**，跟 akshare THS 清单的 `code` **是同一个编码体系**（都是 THS 内部 ID）
3. **返回的概念名 100% 匹配 akshare THS 清单**——"白酒概念"、"超级品牌"、"国企改革"等都精确命中
4. **附带入选理由 `reason` 字段**——这是 THS 公开的"为什么入选这个概念"说明

**架构变更**：

```
变更前（第一次假设）：
   概念清单: akshare THS  (q.10jqka.com.cn)
   反查:     adata EM     (datacenter.eastmoney.com)
                     ↑
              不同源，会对不上（白酒 vs 白酒概念）

变更后（发现 get_concept_ths 后）：
   概念清单: akshare THS  (q.10jqka.com.cn)
   反查:     adata THS    (q.10jqka.com.cn 后端)
                     ↑
              同源，天然对得上（"白酒概念" vs "白酒概念"）
```

**adata 在本期保留什么**：

| 端点 | 保留？ | 用途 |
|:---|:---:|:---|
| `stock.info.get_concept_ths` | ✅ | **核心**：M:N 反查（akshare 无此能力） |
| `stock.info.all_concept_code_ths` | ❌ | akshare `concept_name_ths` 已覆盖 |
| `stock.info.concept_constituent_ths` | ❌ | akshare 无 THS cons 反向端点（确认） |
| `stock.info.get_concept_east` | ⚪ | 仅作 fallback（EM 网络恢复后备用） |
| `stock.info.all_concept_code_east` | ❌ | RST，本就不通 |
| `stock.info.concept_constituent_east` | ❌ | RST，本就不通 |

### Q1.5：为什么不用 akshare 东方财富（EM）端点？

**简短答**：EM 全部 RST，**当前用不了**。

**实测结果**（2026-09-27）：

| 域名 | TCP 443 | HTTP 业务 |
|:---|:---:|:---:|
| `push2.eastmoney.com` | ✅ | ❌ RST |
| `datacenter.eastmoney.com` | ✅ | ✅（adata 在用） |
| `q.10jqka.com.cn` | ✅ | ✅（akshare THS 在用） |

```
ak.stock_board_concept_name_em    → RST
ak.stock_board_concept_cons_em    → RST
ak.stock_board_concept_spot_em    → RST
ak.stock_board_concept_hist_em    → RST
```

**EM 端点本质是 akshare 调 push2.eastmoney.com**——服务端主动断连（风控），不是网络问题。**重试不会变好**。

**EM 数据丰富度（基于官方文档）**：

| 维度 | EM 字段 | THS 字段 |
|:---|:---|:---|
| 清单 | 12 列（含最新价/涨跌额/涨跌幅/换手率/上涨家数/**领涨股票**） | 2 列（name, code） |
| 成分股 | 16 列（含最新价/涨跌幅/振幅/换手率/市盈率-动态/市净率） | **无此端点** |
| 实时 | 10 字段（含换手率/振幅） | 10 字段（含资金净流入/涨跌家数） |
| 历史 K 线 | 11 列（含涨跌幅/换手率/振幅，5 年级历史） | 7 列（无涨跌，得自己算） |

**结论**：**EM 恢复后建议引入作为 THS 的增强源**（清单的领涨股票、成分股的实时价都对前端展示很有价值）。**但本期不能依赖**，所有前端可见数据均来自 THS + adata。

### Q2：概念涨跌怎么显示？

**答：用 `ak.stock_board_concept_info_ths`，字段直出**。

**实测字段（人形机器人概念）**：

| 字段 | 值 |
|:---|:---|
| 今开 | 2399.97 |
| 昨收 | 2407.22 |
| 最低 | 2374.96 |
| 最高 | 2417.26 |
| 成交量(万手) | 6400.99 |
| **板块涨幅** | **-1.32%** ← 同花顺显示的就是这个 |
| 涨幅排名 | 191/390 |
| 涨跌家数 | 90/372 |
| 资金净流入(亿) | -199.38 |
| 成交额(亿) | 1960.19 |

**这是 THS 端点直接给的字段，无需任何计算**。

---

## 四、数据源分工（本期方案）

```
┌─────────────────────────────────────────────────────────────────┐
│ 采集阶段（写入 DB）                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 概念清单                                                     │
│     ┌──────────────────────┐                                    │
│     │ ak.concept_name_ths  │ → upsert concepts(name, source='ths')│
│     │  375 个概念           │                                    │
│     └──────────────────────┘                                    │
│                                                                 │
│  2. 概念-成分股 M:N                                              │
│     ┌──────────────────────┐                                    │
│     │ adata.get_concept_ths │                                    │
│     │  (stock_code=symbol) │  ← 反向：从股票出发                 │
│     │  for each stock      │  ← THS 同源（与清单天然匹配）       │
│     └──────────────────────┘                                    │
│         → upsert concepts（若 name 尚未入库，source='ths'）     │
│         → upsert stock_concept_members(symbol, concept_id)       │
│                                                                 │
│  3. 概念行情快照                                                  │
│     ┌──────────────────────┐                                    │
│     │ ak.concept_info_ths  │ → upsert concept_snapshots          │
│     │  (concept=name)      │   (name, latest, pct_change, ...)  │
│     │  for each concept    │   实时同步（每次采集都覆盖）        │
│     └──────────────────────┘                                    │
│                                                                 │
│  4. 概念日 K 线                                                  │
│     ┌──────────────────────┐                                    │
│     │ ak.concept_index_ths │ → upsert concept_index_ths         │
│     │  (concept=name)      │   (name, date, open, high, low,    │
│     │  for each concept    │    close, volume, amount)          │
│     └──────────────────────┘                                    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ 读取阶段（前端展示）                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  • StockInfoList 列表主概念列                                     │
│      row.concepts ← stock_concept_members ← DB                  │
│                                                                 │
│  • 详情抽屉「概念」Tab                                            │
│      /concepts/tab-by-symbol/{symbol}                            │
│      ← stock_concept_members（按 concept_type 分组）             │
│                                                                 │
│  • 🆕 概念行情（板块涨幅）                                        │
│      /concepts/{name}/snapshot                                    │
│      ← concept_snapshots                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 五、为什么不用 EM？

**EM 全部 RST**，包括：

- `ak.stock_board_concept_name_em`
- `ak.stock_board_concept_cons_em`
- `ak.stock_board_concept_spot_em`
- `ak.stock_board_concept_hist_em`
- `ak.stock_board_industry_cons_em`（行业成分股也挂）

**EM 端点能做的事 THS 都能做**（清单、行情、摘要），**且 THS 还多一项 EM 没有的 `concept_info_ths`（单概念实时行情）**。

**结论**：本期 EM 不参与，**所有前端可见的概念数据均来自 THS**。

---

## 六、本期架构决策汇总

| 决策点 | 决策 | 理由 |
|:---|:---|:---|
| 数据源：清单 | **仅 THS** | EM RST；THS 375 个概念全覆盖 |
| 数据源：成分股 M:N | **仅 adata 反查** | akshare 无 cons 端点；EM RST |
| 数据源：概念实时行情 | **仅 THS** | `concept_info_ths` 直出板块涨幅 |
| 数据源：概念日 K | **仅 THS** | `concept_index_ths` 244 个交易日 |
| 是否保留 adata | **保留，但只保留 `get_concept_east` 一项能力** | 反查是 M:N 关系的唯一可行路径 |
| 概念 type 字段 | **默认 `other`** | THS summary 不含 type；先用 `other`，未来加分类规则染色 |
| 是否新增 DDL | **新增 2 张表**：`concept_snapshots` / `concept_index_ths` | 行情数据无既有表可复用 |
| 是否改既有概念 | **零破坏** | `concepts` / `stock_concept_members` 表结构不变 |

---

## 七、变更统计

| 层 | 文件 | 操作 | 改动量（估算） |
|:---|:---|:---:|:---|
| Domain | `domain/concept/value_objects.py` | ✏️ +`ConceptSnapshotVO` | ~25 行 |
| Domain | `domain/concept/entity.py` | ✏️ +`ConceptSnapshot` 实体 | ~30 行 |
| ORM | `infrastructure/database/models/concept.py` | ✏️ +2 个 ORM（snapshot / index_ths） | ~80 行 |
| Repository | `infrastructure/repositories/concept_repository.py` | ✏️ +3 方法（upsert_single_member / list_snapshots / list_index_ths） | ~70 行 |
| Collector | `infrastructure/collectors/akshare/fetcher.py` | ✏️ +`fetch_concept_info_ths` / `fetch_concept_index_ths` | ~80 行 |
| Collector | `infrastructure/collectors/adata/fetcher.py` | 🔧 仅保留 `fetch_concepts_by_stock`（其余标 deprecated） | ~30 行 |
| Service | `application/concept_service.py` | ✏️ 新增 `sync_membership` / `sync_snapshots` / `sync_index_ths` | ~120 行 |
| Sync Task | `infrastructure/tasks/concept_*` | 🆕 `concept_membership_sync_task.py` / `concept_snapshot_sync_task.py` | ~200 行 |
| Route | `route/api/v1/concept.py` | ✏️ +3 端点 | ~30 行 |
| Frontend | `views/stock-info/api.ts` | ✏️ 类型 + API 封装 | ~30 行 |
| Frontend | `views/stock-info/components/ConceptTag.vue` | ✏️ 加 `pct_change` 染色 | ~15 行 |
| Frontend | `views/collect-manage/api.ts` | ✏️ 新增概念子任务 API | ~30 行 |
| Frontend | `views/collect-manage/CollectManage.vue` | ✏️ 概念 Tab 拆为子任务 | ~80 行 |
| **合计** | — | — | **~820 行** |

---

## 八、相关文档索引

| 文档 | 路径 | 说明 |
|:---|:---|:---|
| 二期总览 | `docs/dev/08concept/README.md` | 主概念列 + 实时刷新 |
| 一期总览 | `docs/dev/06gainian/README.md` | 基础 CRUD |
| akshare 协议扩展 | `docs/dev/04protocol/03_akshare_extension.md` | akshare 接口能力清单 |
| akshare collector | `src/infrastructure/collectors/akshare/fetcher.py` | 当前实现 |
| adata collector | `src/infrastructure/collectors/adata/fetcher.py` | 当前实现 |

---

## 九、测试要点

| 测试 | 类型 | 覆盖 |
|:---|:---|:---|
| `test_akshare_ths_concept.py` | 实测脚本 | `concept_name_ths` / `concept_info_ths` / `concept_index_ths` 字段 |
| `test_concept_membership_sync.py` | 单元 | 一次反查的 (symbol, concept_name) → 入库 |
| `test_concept_snapshot_sync.py` | 单元 | `concept_info_ths` 字段解析（板块涨幅字符串 → float） |
| `test_concept_index_ths_sync.py` | 单元 | 日 K DataFrame → ORM 行 |
| `test_route_concept_snapshot.py` | 集成 | `GET /concepts/{name}/snapshot` 端到端 |
| `test_panel_main_concepts.py` | 回归 | 列表主概念列填充（已有 08concept 用例继续跑） |
| `CollectManage.spec.ts` | 集成 | 概念 Tab 三种子任务（清单 / 成分股 / 行情）UI 表现 |
